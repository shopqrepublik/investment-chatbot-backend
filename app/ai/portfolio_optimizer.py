# D:\investment-chatbot\app\ai\portfolio_optimizer.py
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    def __init__(self):
        self.horizon_map = {'3m': 90, '6m': 180, '12m': 365}
    
    def analyze_ticker(self, ticker: str, horizon: str = '12m') -> Dict:
        """Analyze single ticker with technical analysis"""
        try:
            stock = yf.Ticker(ticker)
            days = self.horizon_map.get(horizon, 365)
            
            # Get historical data
            hist = stock.history(period="1y")  # 1 year for better analysis
            
            if hist.empty or len(hist) < 30:
                return {"ticker": ticker, "score": 0, "error": "Insufficient data"}
            
            # Calculate technical indicators
            current_price = hist['Close'].iloc[-1]
            
            # Price momentum (short-term vs long-term)
            sma_20 = hist['Close'].rolling(20).mean().iloc[-1]
            sma_50 = hist['Close'].rolling(50).mean().iloc[-1]
            
            # Returns
 returns_30d = (current_price / hist['Close'].iloc[-30] - 1) * 100
            returns_90d = (current_price / hist['Close'].iloc[-90] - 1) * 100
            
            # Volatility
            volatility = hist['Close'].pct_change().std() * np.sqrt(252) * 100
            
            # ML-like scoring
            score = self.calculate_score(
                current_price, sma_20, sma_50, 
                returns_30d, returns_90d, volatility, horizon
            )
            
            return {
                "ticker": ticker,
                "current_price": round(current_price, 2),
                "price_vs_sma20": round((current_price / sma_20 - 1) * 100, 2),
                "returns_30d": round(returns_30d, 2),
                "returns_90d": round(returns_90d, 2),
                "volatility": round(volatility, 2),
                "score": round(score, 3),
                "volume_avg": int(hist['Volume'].mean())
            }
            
        except Exception as e:
            logger.error(f"Analysis failed for {ticker}: {e}")
            return {"ticker": ticker, "score": 0, "error": str(e)}
    
    def calculate_score(self, price, sma_20, sma_50, ret_30d, ret_90d, vol, horizon):
        """Calculate investment score based on multiple factors"""
        
        # Momentum factor (weight depends on horizon)
        momentum_weight = 0.4 if horizon == '3m' else 0.3
        momentum_score = (ret_30d * 0.6 + ret_90d * 0.4) / 10  # Normalize
        
        # Trend factor
        trend_score = 0
        if price > sma_20 > sma_50:
            trend_score = 1.0
        elif price > sma_20:
            trend_score = 0.7
        elif price > sma_50:
            trend_score = 0.4
        else:
            trend_score = 0.1
        
        # Volatility factor (inverse - lower volatility is better for conservative)
        volatility_score = max(0, 1 - (vol / 100))
        
        # Combine scores
        total_score = (
            momentum_weight * momentum_score +
            0.3 * trend_score +
            0.3 * volatility_score
        )
        
        return max(0, min(1, total_score))
    
    def select_top_tickers(self, analyzed_tickers: List[Dict], risk_profile: Dict) -> List[Dict]:
        """Select best tickers based on risk profile"""
        
        # Filter by minimum score based on risk tolerance
        min_scores = {'low': 0.7, 'medium': 0.6, 'high': 0.5}
        min_score = min_scores.get(risk_profile['risk_tolerance'], 0.6)
        
        filtered = [t for t in analyzed_tickers if t.get('score', 0) >= min_score]
        
        # Sort by score descending
        filtered.sort(key=lambda x: x['score'], reverse=True)
        
        # Select count based on diversification
        diversification_map = {'low': 3, 'medium': 6, 'high': 10}
        target_count = diversification_map.get(risk_profile.get('diversification', 'medium'), 6)
        
        return filtered[:target_count]
    
    def calculate_allocation(self, selected_tickers: List[Dict], total_amount: float) -> Dict:
        """Calculate optimal allocation weights"""
        
        if not selected_tickers:
            return {"assets": [], "total_amount": total_amount}
        
        # Use score-based weighting
        scores = [t['score'] for t in selected_tickers]
        total_score = sum(scores)
        
        assets = []
        for ticker_data in selected_tickers:
            weight = (ticker_data['score'] / total_score) * 100
            amount = total_amount * (weight / 100)
            
            # Calculate whole shares
            shares = int(amount / ticker_data['current_price'])
            actual_amount = shares * ticker_data['current_price']
            
            assets.append({
                "ticker": ticker_data['ticker"],
                "allocation": round(weight, 2),
                "shares": shares,
                "amount": round(actual_amount, 2),
                "current_price": ticker_data['current_price'],
                "score": ticker_data['score']
            })
        
        # Recalculate total based on actual share amounts
        actual_total = sum(asset['amount'] for asset in assets)
        
        return {
            "assets": assets,
            "total_amount": round(actual_total, 2),
            "expected_return": round(sum(a['score'] * a['allocation'] for a in assets) / 100, 3),
            "diversification_score": len(assets)
        }