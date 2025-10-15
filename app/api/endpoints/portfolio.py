# D:\investment-chatbot\app\api\endpoints\portfolio.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
from typing import List, Dict, Any
import os

router = APIRouter()
logger = logging.getLogger(__name__)

class PortfolioRequest(BaseModel):
    horizon: str = "12m"
    risk_tolerance: str = "medium"
    investment_amount: float = 10000
    diversification: str = "medium"
    preferred_markets: List[str] = ["sp500", "nasdaq"]
    investment_priority: str = "growth"

@router.post("/generate")
async def generate_smart_portfolio(request: PortfolioRequest):
    """
    Generate portfolio based on real analysis of S&P500 + Nasdaq
    """
    try:
        # 1. Get real tickers from S&P500 and Nasdaq
        from app.services.ticker_service import TickerService
        ticker_service = TickerService()
        
        # Get ALL tickers
        all_tickers = []
        if "sp500" in request.preferred_markets:
            all_tickers.extend(ticker_service.get_sp500_tickers())
        if "nasdaq" in request.preferred_markets:
            all_tickers.extend(ticker_service.get_nasdaq_tickers())
        
        # Remove duplicates
        all_tickers = list(set(all_tickers))
        
        logger.info(f"Analyzing {len(all_tickers)} tickers...")
        
        # 2. Analyze tickers with ML
        from app.ai.portfolio_optimizer import PortfolioOptimizer
        optimizer = PortfolioOptimizer()
        
        analyzed_tickers = []
        for ticker in all_tickers[:100]:  # Analyze first 100 for performance
            try:
                analysis = optimizer.analyze_ticker(
                    ticker, 
                    horizon=request.horizon
                )
                if analysis.get('score', 0) > 0.5:  # Minimum quality threshold
                    analyzed_tickers.append(analysis)
            except Exception as e:
                logger.debug(f"Failed to analyze {ticker}: {e}")
                continue
        
        # 3. Select best tickers based on risk profile
        risk_profile = {
            'risk_tolerance': request.risk_tolerance,
            'diversification': request.diversification,
            'investment_priority': request.investment_priority
        }
        
        selected_tickers = optimizer.select_top_tickers(
            analyzed_tickers, 
            risk_profile
        )
        
        # 4. Calculate allocation
        portfolio = optimizer.calculate_allocation(
            selected_tickers, 
            request.investment_amount
        )
        
        return {
            "status": "success",
            "portfolio": portfolio,
            "analysis_metadata": {
                "total_tickers_analyzed": len(all_tickers),
                "qualified_tickers": len(analyzed_tickers),
                "selected_count": len(selected_tickers),
                "risk_profile": risk_profile
            }
        }
        
    except Exception as e:
        logger.error(f"Portfolio generation failed: {str(e)}")
        return {
            "status": "error", 
            "message": f"Portfolio generation failed: {str(e)}"
        }

@router.get("/test-tickers")
async def test_ticker_service():
    """Test ticker service functionality"""
    try:
        from app.services.ticker_service import TickerService
        ticker_service = TickerService()
        
        sp500_tickers = ticker_service.get_sp500_tickers()
        nasdaq_tickers = ticker_service.get_nasdaq_tickers()
        
        return {
            "status": "success",
            "sp500_count": len(sp500_tickers),
            "nasdaq_count": len(nasdaq_tickers),
            "sp500_sample": sp500_tickers[:10],
            "nasdaq_sample": nasdaq_tickers[:10]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ticker service test failed: {str(e)}"
        }