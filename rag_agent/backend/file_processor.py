import os
import tempfile
import uuid #generate unique id
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from endee import Endee, Precision

def process_and_ingest_document(file_obj,filename:str,embedding_model,user_id:str):
    temp_file_path=""
    try:
        file_extension = os.path.splitext(filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(file_obj.read())
            temp_file_path = temp_file.name

        if file_extension == '.pdf':
            loader = PyPDFLoader(temp_file_path)
        elif file_extension == '.txt':
            loader = TextLoader(temp_file_path)
        elif file_extension in ['.doc', '.docx']:
            loader = Docx2txtLoader(temp_file_path)
        else:
            return False, f"Unsupported file type: {file_extension}"
        
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(docs)

        client = Endee()
        index_name = "endee_rag"

        try:
            # indexes=client.list_indexes();
            # if index_name not in indexes:
            # print(f"DEBUG creating new Endee index:{index_name}")
            client.create_index(
                name=index_name,
                dimension=384,
                space_type="cosine",
                precision="float32" 
            )
        except Exception as e:
            # print(f"DEBUG: Endee Index Check Error: {e}")
            pass
        
        index = client.get_index(name=index_name)

        print(f"DEBUG: Embedding {len(splits)} chunks for user {user_id}...")
        vectors_to_upsert = []

        for chunk in splits:
            embedding=embedding_model.embed_query(chunk.page_content)
            chunk_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
            payload = {
                "id": chunk_id,                         
                "vector": embedding,                    
                "filter": {"user_id": user_id},          
                "meta": {                                # (Actual Data)
                    "text": chunk.page_content,
                    "filename": filename
                }
            }
            vectors_to_upsert.append(payload)
        index.upsert(vectors_to_upsert)
        return True, f"Successfully processed and saved {len(splits)} chunks to Endee."

    except Exception as e:
        print(f"Error processing file: {e}")
        return False, str(e)
        
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
    