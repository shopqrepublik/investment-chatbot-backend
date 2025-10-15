# app/api/endpoints/chat.py
from fastapi import APIRouter, HTTPException, Request, Depends, Query
from typing import Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])

# Development auth function
def get_current_user_development():
    """Simple development auth that always returns a user"""
    return {
        "user_id": 1,
        "username": "demo_user",
        "email": "demo@example.com"
    }

@router.post("/start")
async def start_chat(request: Request):
    """
    🚀 Start chat session - Development version
    """
    try:
        # Try to get request body
        try:
            data = await request.json()
        except:
            data = {}

        # Extract tickers
        tickers = data.get("tickers", ["AAPL", "MSFT", "GOOGL"])
        
        if not isinstance(tickers, list):
            tickers = ["AAPL", "MSFT", "GOOGL"]

        logger.info(f"💬 Chat start request | tickers={tickers}")

        # Simple analysis without external dependencies
        analysis_result = {
            "success": True,
            "analyzed_tickers": len(tickers),
            "market_sentiment": "Bullish 📈",
            "results": [
                {
                    "ticker": ticker,
                    "current_price": 100 + i * 50,
                    "price_change_%": 2.5 - i * 0.5,
                    "trend": "Uptrend 📈",
                    "recommendation": "Buy ✅",
                    "confidence": 0.8 - i * 0.1,
                    "key_metrics": {
                        "RSI": "55 (Neutral)",
                        "Trend": "Uptrend",
                        "Volatility": "Medium"
                    }
                } for i, ticker in enumerate(tickers)
            ],
            "ai_insights": [
                "Market shows positive momentum",
                "Consider diversification across sectors",
                "Monitor economic indicators"
            ]
        }

        response = {
            "success": True,
            "message": f"Portfolio analyzed for {len(tickers)} tickers",
            "session_id": f"session_{int(datetime.now().timestamp())}",
            "tickers": tickers,
            "data": analysis_result,
            "welcome_message": "🤖 Welcome to Investment Chat Bot! Ready to help with your investment questions."
        }

        logger.info("✅ Chat analysis completed successfully")
        return response

    except Exception as e:
        logger.error(f"❌ Chat analysis failed: {e}")
        return {
            "success": False,
            "message": f"Chat analysis failed: {str(e)}",
            "session_id": None,
            "data": None
        }

@router.post("/message")
async def send_message(request: Dict[str, Any]):
    """
    Send message to chat bot - Development version
    """
    try:
        message = request.get("message", "").strip()
        session_id = request.get("session_id", "")
        
        if not message:
            return {
                "success": False,
                "message": "Message cannot be empty",
                "response": "Please enter a message."
            }

        logger.info(f"💬 Chat message: {message}")

        # Simple response logic
        if "hello" in message.lower():
            response = "🤖 Hello! I'm your investment assistant. How can I help you today?"
        elif "analyze" in message.lower():
            response = "I can analyze stocks for you! Just give me a ticker symbol like AAPL or TSLA."
        elif "portfolio" in message.lower():
            response = "I can help with portfolio optimization. What's your investment horizon and risk tolerance?"
        else:
            response = f"🤖 Thanks for your message: '{message}'. I specialize in investment analysis. Ask me about stocks, portfolios, or market trends!"

        return {
            "success": True,
            "message": "Message processed successfully",
            "session_id": session_id,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Chat message processing failed: {e}")
        return {
            "success": False,
            "message": f"Message processing failed: {str(e)}",
            "response": "Sorry, I encountered an error. Please try again."
        }