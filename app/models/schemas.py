# app/models/schemas.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from decimal import Decimal

class PortfolioItem(BaseModel):
    ticker: str = Field(..., description="Asset ticker symbol")
    weight: float = Field(..., ge=0, le=100, description="Weight in portfolio (%)")
    asset_type: Optional[str] = Field(None, description="Asset type (stock, etf, etc)")

class AnalysisRequest(BaseModel):
    portfolio: List[PortfolioItem] = Field(..., description="Portfolio composition")
    total_value: float = Field(10000.0, description="Total portfolio value")
    investment_horizon: str = Field("6m", description="Investment horizon")
    risk_tolerance: str = Field("medium", description="Risk tolerance level")

class PortfolioMetrics(BaseModel):
    total_return: float = Field(..., description="Total return")
    annual_volatility: float = Field(..., description="Annual volatility")
    sharpe_ratio: float = Field(..., description="Sharpe ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown")
    beta: float = Field(..., description="Beta to market")
    alpha: float = Field(..., description="Alpha to market")
    diversification_score: float = Field(..., description="Diversification score")
    sector_concentration: Dict[str, float] = Field(..., description="Sector concentration")

class AnalysisResponse(BaseModel):
    success: bool = Field(..., description="Execution status")
    metrics: PortfolioMetrics = Field(..., description="Calculated metrics")
    ai_analysis: str = Field(..., description="AI analysis and recommendations")
    market_regime: Dict[str, Any] = Field(..., description="Current market regime")
    correlation_matrix: Dict[str, Dict[str, float]] = Field(..., description="Correlation matrix")