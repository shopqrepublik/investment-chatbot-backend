from sqlalchemy import create_engine, Column, Integer, String, Numeric, Date, Text, BigInteger, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///./investment_bot.db"

# Create SQLite database engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# User model
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)

# User profile model
class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    investment_horizon = Column(String(10))
    risk_tolerance = Column(String(10))
    preferred_markets = Column(Text)
    investment_priority = Column(String(20))
    investment_amount = Column(String(20))
    diversification_preference = Column(String(20))
    created_at = Column(DateTime, default=func.now())

# Price model
class Price(Base):
    __tablename__ = "prices"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(50), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Numeric(10, 4))
    high = Column(Numeric(10, 4))
    low = Column(Numeric(10, 4))
    close = Column(Numeric(10, 4))
    adj_close = Column(Numeric(10, 4))
    volume = Column(BigInteger)

# Portfolio model
class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    profile_id = Column(Integer, nullable=False)
    name = Column(String(255))
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)

# Portfolio assets model
class PortfolioAsset(Base):
    __tablename__ = "portfolio_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, nullable=False)
    ticker = Column(String(20), nullable=False)
    asset_type = Column(String(20))
    weight = Column(Numeric(5, 4))
    target_price = Column(Numeric(10, 4))
    horizon = Column(String(10))

# Function to create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Function to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()