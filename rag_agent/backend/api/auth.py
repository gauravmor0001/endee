from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import jwt
from datetime import datetime, timedelta
from database import UserDatabase

router = APIRouter()
db = UserDatabase()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

def create_token(user_id:str ,username:str):
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(authorization: str = None):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization token")
    
    try:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        username = payload.get("username")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id, username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
@router.post("/register")
async def register(request: RegisterRequest):
    if len(request.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    success, message, user_id = db.create_user(request.username, request.password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, "user_id": user_id, "username": request.username}

@router.post("/login")
async def login(request: LoginRequest):
    success, message, user_id = db.verify_user(request.username, request.password)
    if not success:
        raise HTTPException(status_code=401, detail=message)
    
    token = create_token(user_id, request.username)
    return {"token": token, "user_id": user_id, "username": request.username, "message": "Login successful"}