# app/api/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime, timedelta
import jwt
from app.database import get_db

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Development secret key
SECRET_KEY = "development-secret-key-change-in-production"
ALGORITHM = "HS256"

def create_access_token(data: Dict[str, Any], expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

@router.post("/login")
async def login() -> Dict[str, Any]:
    """Development login endpoint - returns a demo token"""
    user_data = {
        "user_id": 1,
        "username": "demo_user",
        "email": "demo@example.com"
    }
    
    access_token = create_access_token(data={"sub": user_data["username"], "user_id": user_data["user_id"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_data
    }

@router.post("/register")
async def register() -> Dict[str, Any]:
    """Development registration endpoint"""
    return {
        "success": True,
        "message": "Demo registration successful",
        "user": {
            "id": 1,
            "username": "demo_user",
            "email": "demo@example.com"
        }
    }

@router.get("/me")
async def get_current_user_info(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get current user information"""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    return {
        "id": payload.get("user_id", 1),
        "username": payload.get("sub", "demo_user"),
        "email": f"{payload.get('sub', 'demo_user')}@example.com"
    }