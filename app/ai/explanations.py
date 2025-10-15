# app/ai/explanations.py
import os
import logging
from typing import Dict, Any
from openai import OpenAI, APIError, RateLimitError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class AIExplanationEngine:
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            self._client = OpenAI(api_key=api_key)
        return self._client

    async def generate_portfolio_analysis(self, metrics: Dict[str, Any], 
                                       portfolio: list, 
                                       market_regime: Dict[str, Any]) -> str:
        """Generate AI portfolio analysis"""
        
        prompt = self._build_portfolio_prompt(metrics, portfolio, market_regime)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800,
            )
            return response.choices[0].message.content.strip()
            
        except RateLimitError:
            logger.warning("OpenAI rate limit exceeded")
            return "Analysis temporarily unavailable due to high load. Please try again later."
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return "Analysis service is temporarily unavailable."
        except Exception as e:
            logger.error(f"Unexpected error in AI analysis: {e}")
            return "Could not generate analysis at this time."

    def _build_portfolio_prompt(self, metrics: Dict[str, Any], 
                              portfolio: list, 
                              market_regime: Dict[str, Any]) -> str:
        
        portfolio_summary = ", ".join([f"{p['ticker']} ({p['weight']}%)" for p in portfolio])
        
        return f"""
You are a senior investment analyst. Analyze the portfolio and provide a comprehensive report for a retail investor.

PORTFOLIO DATA:
- Composition: {portfolio_summary}
- Total Return: {metrics.get('total_return', 0):.2f}%
- Volatility: {metrics.get('annual_volatility', 0):.2f}%
- Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}
- Maximum Drawdown: {metrics.get('max_drawdown', 0):.2f}%
- Beta (Market Risk): {metrics.get('beta', 0):.2f}
- Diversification Score: {metrics.get('diversification_score', 0):.1f}/10

MARKET REGIME:
- Current Regime: {market_regime.get('regime', 'neutral')}
- Confidence: {market_regime.get('confidence', 0):.1%}

FORMAT YOUR RESPONSE AS FOLLOWS:

📊 **OVERALL ASSESSMENT**
[2-3 sentences about portfolio overall condition]

✅ **STRENGTHS**
• [Point 1]
• [Point 2]

⚠️ **RISKS & WEAKNESSES**
• [Point 1] 
• [Point 2]

🎯 **RECOMMENDATIONS**
• [Specific action 1]
• [Specific action 2]

📈 **OUTLOOK**
[Brief forecast considering market regime]

Use simple, clear language without excessive jargon. Be specific in your recommendations.
"""

    async def generate_ticker_analysis(self, ticker: str, facts: Dict[str, Any]) -> str:
        """Analyze individual ticker"""
        prompt = f"""
Analyze investment attractiveness of {ticker}:

DATA:
- Price: ${facts.get('current_price', 0):.2f}
- 6-month momentum: {facts.get('momentum_6m', 0):.2f}%
- Volatility: {facts.get('volatility', 0):.2f}%
- P/E: {facts.get('pe_ratio', 'N/A')}
- Dividend Yield: {facts.get('dividend_yield', 0):.2f}%

Provide brief assessment for 3-6-12 months in format:
• Short-term outlook (3 months)
• Medium-term perspective (6 months) 
• Long-term potential (12 months)
• Key risks
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.25,
                max_tokens=400,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error in ticker analysis: {e}")
            return f"Analysis for {ticker} is temporarily unavailable."