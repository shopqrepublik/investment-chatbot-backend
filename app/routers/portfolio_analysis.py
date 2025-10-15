# app/routers/portfolio_analysis.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
import time
from app.models.schemas import AnalysisRequest, AnalysisResponse
from app.ai.analysis import PortfolioAIAnalyzer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/portfolio", tags=["Portfolio Analysis"])

@router.post("/analysis", response_model=AnalysisResponse)
async def analyze_portfolio(request: AnalysisRequest):
    """
    AI-powered investment portfolio analysis
    """
    start_time = time.time()
    logger.info(f"🔍 Starting portfolio analysis for {len(request.portfolio)} assets")
    
    try:
        if not request.portfolio:
            logger.warning("Empty portfolio received")
            raise HTTPException(status_code=400, detail="Portfolio cannot be empty")
        
        # Validate weight sum
        total_weight = sum(item.weight for item in request.portfolio)
        logger.info(f"📊 Total portfolio weight: {total_weight}%")
        
        if abs(total_weight - 100.0) > 1.0:  # 1% tolerance
            error_msg = f"Portfolio weights must sum to 100% (current: {total_weight:.1f}%)"
            logger.warning(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Convert to dict for analyzer
        portfolio_dict = [item.dict() for item in request.portfolio]
        logger.info(f"🔄 Portfolio tickers: {[p['ticker'] for p in portfolio_dict]}")
        
        # Create analyzer
        analyzer = PortfolioAIAnalyzer(
            portfolio=portfolio_dict,
            total_value=request.total_value
        )
        
        logger.info("🚀 Starting comprehensive analysis...")
        
        # Run analysis with timeout protection
        result = await analyzer.run_full_analysis()
        
        analysis_time = time.time() - start_time
        logger.info(f"✅ Analysis completed in {analysis_time:.2f} seconds")
        
        return AnalysisResponse(
            success=True,
            metrics=result["metrics"],
            ai_analysis=result["ai_analysis"],
            market_regime=result["market_regime"],
            correlation_matrix=result["correlation_matrix"]
        )
        
    except ValueError as e:
        logger.warning(f"Value error in portfolio analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in portfolio analysis: {e}")
        analysis_time = time.time() - start_time
        logger.error(f"❌ Analysis failed after {analysis_time:.2f} seconds")
        raise HTTPException(status_code=500, detail="Internal server error during analysis")

@router.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "portfolio_analysis",
        "ai_available": True,
        "timestamp": time.time()
    }