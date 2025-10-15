from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .auth_utils import verify_token

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Зависимость для получения текущего пользователя из JWT токена"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или просроченный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # В нашей упрощенной системе у нас только один пользователь
    # В реальной системе здесь бы мы искали пользователя в БД по payload
    user_data = {
        "id": 1,
        "email": "admin@investment-bot.com",
        "is_active": True
    }
    
    return user_data

def require_auth(current_user: dict = Depends(get_current_user)):
    """Зависимость для проверки аутентификации"""
    if not current_user or not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация",
        )
    return current_user