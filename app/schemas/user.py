from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Схемы для аутентификации
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    password: str

# Схемы для опроса
class SurveyAnswer(BaseModel):
    question_id: int
    answer: str

class SurveyResponse(BaseModel):
    answers: List[SurveyAnswer]

class UserProfileCreate(BaseModel):
    investment_horizon: str  # '3m', '6m', '12m'
    risk_tolerance: str      # 'low', 'medium', 'high'
    preferred_markets: str   # 'sp500', 'nasdaq', 'microcap'
    investment_priority: str # 'income', 'growth', 'potential'
    investment_amount: str   # 'low', 'medium', 'high'
    diversification_preference: str  # 'concentrated', 'balanced', 'diversified'

# Схемы для пользователя
class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class UserProfileResponse(UserProfileCreate):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
