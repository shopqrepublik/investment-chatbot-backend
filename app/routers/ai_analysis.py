from fastapi import APIRouter, HTTPException
from app.ai_analysis import PortfolioAIAnalyzer

router = APIRouter(prefix="/api/portfolio", tags=["AI Analysis"])

@router.post("/analysis")
async def analyze_portfolio(payload: dict):
    portfolio = payload.get("portfolio")
    total_value = payload.get("total_value", 10000)
    if not portfolio:
        raise HTTPException(status_code=400, detail="Portfolio data is required")

    analyzer = PortfolioAIAnalyzer(portfolio, total_value)
    result = await analyzer.run_full_analysis()
    return {"success": True, "data": result}
