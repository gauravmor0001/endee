import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import auth,documents,chat

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["Authentication"])
app.include_router(documents.router, tags=["Documents"])
app.include_router(chat.router, tags=["Chat Engine"])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)