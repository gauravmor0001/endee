from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from endee import Endee
from langchain_huggingface import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
@tool
def search_knowledge_base(query: str , config: RunnableConfig):
    """
     Use this tool to search for information inside the uploaded PDF documents or text files.
    Input should be a specific search query related to the documents.
    Returns the relevant text snippets from the files using a Two-Stage Advanced RAG pipeline.
    """

    user_id = config.get("configurable", {}).get("user_id")
    if not user_id:
        return "Error: Authentication missing. Cannot search database."
    try:
        query_vector = embedding_model.embed_query(query)

       
        client = Endee()
        index = client.get_index(name="endee_rag")
        results = index.query(
            vector=query_vector,
            top_k=3, # Give us the top 3 best matches
            filter=[{"user_id": user_id}] # The Bouncer: ONLY search this user's files!
        )

        if not results:
            return "No relevant documents found in the database."
        
        context_pieces = []
        for item in results:
            # Endee returns a list of dictionaries. We want to open the 'meta' backpack and grab the 'text'.
            # It usually looks like: {"id": "...", "similarity": 0.89, "meta": {"text": "...", "filename": "..."}}
            meta_data = item.get("meta", {})
            chunk_text = meta_data.get("text", "")
            
            if chunk_text:
                context_pieces.append(chunk_text)
        final_context = "\n\n---\n\n".join(context_pieces)
        return final_context

    except Exception as e:
        print(f"DEBUG: Endee Search Error: {e}")
        return f"Error searching the knowledge base: {str(e)}"
tools_list=[search_knowledge_base]