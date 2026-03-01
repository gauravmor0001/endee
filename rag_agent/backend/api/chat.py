from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

from database import UserDatabase
from api.auth import verify_token

import re #using it to find xml.
import json
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage  #systemMessage is instruction to the model.
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode, tools_condition #run tools for llm.
from mem0 import Memory
from tools import tools_list
import uuid


load_dotenv()

router = APIRouter()
db = UserDatabase()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

# MODEL_NAME = "llama-3.1-8b-instant"
MODEL_NAME = "llama-3.3-70b-versatile" 
llm = ChatGroq(
    model=MODEL_NAME, 
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3,
)
llm_with_tools = llm.bind_tools(tools_list)

config = {
    "version": "v1.1",
    "embedder": {
        "provider": "huggingface",
        "config": {
            "api_key": os.getenv("HUGGINGFACEHUB_API_TOKEN"),
            "model": "sentence-transformers/all-MiniLM-L6-v2"
        }
    },
    "llm": { #decide what mem0 will remember about user and its prefrences.
        "provider": "groq",
        "config": {
            "api_key": os.getenv("GROQ_API_KEY"),
            "model": MODEL_NAME,
        }
    },
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "chatbot_memory",
            "path": "./local_mem0_db",
        }
    }
}

print("DEBUG: Connecting to Memory...")
mem_client = Memory.from_config(config)

def normalize_tool_calls(state: MessagesState):
    last = state["messages"][-1]
    if not isinstance(last, AIMessage):
        return state

    content = last.content or ""
    
    # Already has proper tool_calls, no need to normalize
    if last.tool_calls:
        return state

    match = re.search(r'<function=([a-zA-Z0-9_\-]+)>\s*(\{[\s\S]*?\})', content)
    if not match:
        return state

    tool_name = match.group(1)
    args_raw = match.group(2)
    try:
        args = json.loads(args_raw) if args_raw else {}
    except:
        args = {}

    print(f"DEBUG: Normalized tool call → {tool_name} with args {args}")  # so you can see it in terminal

    new_message = AIMessage(
    content="",  # clear the XML text, tool_calls carries the info now
    tool_calls=[{
        "name": tool_name,
        "args": args,
        "id": f"call_{uuid.uuid4().hex[:8]}"
    }],
    id=last.id
)
    return {"messages": [new_message]}
def reasoner(state: MessagesState):
    """The main thinking node for the AI."""
    # Take the entire history of the conversation from the flowchart's state
    # Hand it to the LLM (which has tools attached to it)
    response = llm_with_tools.invoke(state["messages"])
    # Take the AI's new reply, add it to the list of messages, 
    # and send it back to the flowchart
    return {"messages":  [response]}


workflow = StateGraph(MessagesState)
workflow.add_node("agent", reasoner)
workflow.add_node("tools", ToolNode(tools_list))
workflow.add_node("normalize", normalize_tool_calls)

workflow.set_entry_point("agent")
workflow.add_edge("agent", "normalize")
workflow.add_conditional_edges("normalize", tools_condition)
workflow.add_edge("tools", "agent")

agent_app = workflow.compile()

# ==========================================
# API ENDPOINTS (The Communication Layer)
# ==========================================

@router.get("/conversations")
async def get_conversations(authorization: Optional[str] = Header(None)):
    """Fetches a list of all chat histories for the logged-in user."""
    user_id, username = verify_token(authorization)
    conversations = db.get_conversations(user_id)
    return {"conversations": conversations}

@router.post("/conversations")
async def create_conversation(authorization: Optional[str] = Header(None)):
    """Creates a brand new, empty chat thread."""
    user_id, username = verify_token(authorization)
    conv_id = db.create_conversation(user_id)
    if conv_id:
        return {"conversation_id": conv_id, "message": "Conversation created"}
    raise HTTPException(status_code=500, detail="Failed to create conversation")
    
@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, authorization: Optional[str] = Header(None)):
    """Loads all the messages inside a specific chat thread."""
    user_id, username = verify_token(authorization)
    conversation = db.get_conversation(conversation_id, user_id)
    if conversation:
        return conversation
    raise HTTPException(status_code=404, detail="Conversation not found")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, authorization: Optional[str] = Header(None)):
    """Deletes a specific chat thread from the database."""
    user_id, username = verify_token(authorization)
    success = db.delete_conversation(conversation_id, user_id)
    if success:
        return {"message": "Conversation deleted"}
    raise HTTPException(status_code=500, detail="Failed to delete conversation")

@router.post("/chat")
async def chat_endpoint(request: ChatRequest, authorization: Optional[str] = Header(None)):
    """The main engine. Receives a message, runs the AI, and saves the memory."""
    # 1. Bouncer: Check who the user is
    user_id, username = verify_token(authorization)
    user_query = request.message
    conv_id = request.conversation_id 

    # 2. Setup: Ensure we have a valid conversation ID to save messages to
    if not conv_id:
        conv_id = db.create_conversation(user_id)
        if not conv_id:
            raise HTTPException(status_code=500, detail="Failed to create conversation")

    # 3. Memory Retrieval: Ask Mem0 if it knows anything relevant about this user
    memories = []
    try:
        search_results = mem_client.search(query=user_query, user_id=user_id, limit=3)
        if search_results:
            raw = search_results if isinstance(search_results, list) else search_results.get("results", [])
            for mem in raw:
                score = mem.get('score', 0)
                if score > 0.7:
                    text = mem.get('memory', str(mem))[:200]
                    memories.append(text)
    except Exception as e:
        print(f"DEBUG: Memory Error: {e}")

    # 4. Prompt Assembly: Give the AI its instructions and the injected Mem0 context
    base_prompt = """You are a helpful AI assistant with access to a personal knowledge base of the user's uploaded documents.
                STRICT RULES:
                1. For ANY question about the user, their preferences, or specific facts — call `search_knowledge_base` FIRST, before responding.
                2. Only after searching, if nothing is found, say you don't know.
                3. NEVER assume the answer isn't in the documents without searching first.
                4. Only answer directly from your own knowledge for clearly general topics (e.g. "what is Python", "explain gravity").
                5. The ONLY tool available is `search_knowledge_base`. Do NOT use web search or any other tool."""

    if memories:
        SYSTEM_PROMPT = f"{base_prompt}\n\nCONTEXT FROM PREVIOUS CONVERSATIONS:\n{chr(10).join('- ' + m for m in memories)}\n\nUse this context ONLY if relevant. DO NOT repeat old answers."
    else:
        SYSTEM_PROMPT = base_prompt

    input_messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_query)]
    
    # 5. Execution: Run the LangGraph AI (with the Secret Tunnel for Data Privacy!)
    try:
        final_state = agent_app.invoke(
            {"messages": input_messages},
            config={"configurable": {"user_id": user_id}}
        )
        
        ai_response = final_state["messages"][-1].content

        # 6. Save Short-Term Memory (to SQLite for the UI)
        try:
            db.add_message_to_conversation(conv_id, user_id, user_query, ai_response)
        except Exception as conv_err:
            print(f"DEBUG: Failed to save to SQL: {conv_err}")
        
        # 7. Save Long-Term Memory (to Mem0/Qdrant for future AI context)
        try:
            mem_client.add(user_id=user_id, messages=[{"role": "user", "content": user_query}, {"role": "assistant", "content": ai_response}])
        except Exception as mem_err:
            print(f"DEBUG: Failed to save to Mem0: {mem_err}")
        
        return {"response": ai_response, "conversation_id": conv_id}
        
    except Exception as e:
        error_msg = str(e)
        if "rate_limit" in error_msg.lower() or "413" in error_msg:
            return {"response": "I am thinking too hard. Please wait 30 seconds."}
        return {"response": f"System Error: {error_msg}"}