from fastapi import APIRouter, File, UploadFile, Header
from typing import Optional
from langchain_huggingface import HuggingFaceEmbeddings
from file_processor import process_and_ingest_document
from api.auth import verify_token


router = APIRouter()

embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

@router.post("/upload-doc")
async def upload_and_ingest(
    file: UploadFile=File(...),
    authorization: Optional[str]=Header(None) #this checks if authorization(metadata header in http) is present or not.if yes user is loged in.the authorization string looks like "Bearer ....."this is a JWT.
    ):
        try:
            user_id, username=verify_token(authorization)

            success,message=process_and_ingest_document(
                file_obj=file.file,
                filename=file.filename,
                embedding_model=embedding_model,
                user_id=user_id
            )
            if success:
                return {"status": "success", "message": message}
            else:
                return {"status": "error", "message": message}

        except Exception as e:
            return {"status": "error", "message": str(e)}