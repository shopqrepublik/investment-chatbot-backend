# app/models/asset_models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    asset_type = Column(String(50))  # stock, etf, etc
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Float)  # in billions
    exchange = Column(String(50))  # NASDAQ, NYSE, etc
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)

class AssetMetrics(Base):
    __tablename__ = "asset_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), index=True, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    
    # Technical metrics
    price = Column(Float)
    volume = Column(Float)
    momentum_1m = Column(Float)
    momentum_3m = Column(Float) 
    momentum_6m = Column(Float)
    volatility_30d = Column(Float)
    rsi_14 = Column(Float)
    
    # Fundamental metrics
    pe_ratio = Column(Float)
    pb_ratio = Column(Float)
    dividend_yield = Column(Float)
    eps_growth = Column(Float)
    revenue_growth = Column(Float)
    
    # AI-generated scores
    technical_score = Column(Float)
    fundamental_score = Column(Float)
    sentiment_score = Column(Float)
    overall_score = Column(Float)
    
    # Market regime compatibility
    bull_score = Column(Float)
    bear_score = Column(Float)
    neutral_score = Column(Float)