# app/ai/asset_selector.py
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Dict, Any, Tuple
import logging
from sqlalchemy.orm import Session
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import asyncio

from app.models.asset_models import Asset, AssetMetrics
from app.ai.explanations import AIExplanationEngine

logger = logging.getLogger(__name__)

class AIAssetSelector:
    def __init__(self, db: Session):
        self.db = db
        self.ai_engine = AIExplanationEngine()
        self.scaler = StandardScaler()
        
    async def select_optimal_assets(self, 
                                  profile: Dict[str, Any],
                                  max_assets: int = 10) -> Dict[str, Any]:
        """
        AI-driven asset selection from entire market
        """
        try:
            logger.info(f"🎯 Starting AI asset selection for profile: {profile}")
            
            # Step 1: Get available assets
            available_assets = await self._get_available_assets(profile)
            logger.info(f"📊 Found {len(available_assets)} available assets")
            
            # Step 2: Calculate comprehensive metrics
            assets_with_metrics = await self._calculate_asset_metrics(available_assets)
            
            # Step 3: AI scoring based on investment profile
            scored_assets = await self._ai_score_assets(assets_with_metrics, profile)
            
            # Step 4: Portfolio optimization
            optimal_portfolio = await self._optimize_portfolio(scored_assets, profile, max_assets)
            
            # Step 5: Generate AI explanation
            ai_explanation = await self._generate_selection_explanation(optimal_portfolio, profile)
            
            return {
                "success": True,
                "selected_assets": optimal_portfolio,
                "ai_explanation": ai_explanation,
                "profile_compatibility": self._calculate_profile_compatibility(optimal_portfolio, profile),
                "market_analysis": await self._get_market_analysis()
            }
            
        except Exception as e:
            logger.error(f"Asset selection error: {e}")
            return {
                "success": False,
                "error": str(e),
                "selected_assets": []
            }
    
    async def _get_available_assets(self, profile: Dict[str, Any]) -> List[Dict]:
        """Get available assets based on profile preferences"""
        try:
            # Base query
            query = self.db.query(Asset).filter(Asset.is_active == True)
            
            # Filter by preferred markets
            market_filters = {
                "sp500": Asset.exchange.in_(["NYSE", "NASDAQ"]),  # S&P 500 companies
                "nasdaq": Asset.exchange == "NASDAQ",
                "microcap": Asset.market_cap < 2.0  # Micro-cap companies
            }
            
            if profile.get('preferred_markets') in market_filters:
                query = query.filter(market_filters[profile['preferred_markets']])
            
            # Filter by risk tolerance
            risk_filters = {
                "low": Asset.volatility_30d < 0.2,  # Low volatility
                "medium": (Asset.volatility_30d >= 0.2) & (Asset.volatility_30d < 0.4),
                "high": Asset.volatility_30d >= 0.4
            }
            
            if profile.get('risk_tolerance') in risk_filters:
                query = query.filter(risk_filters[profile['risk_tolerance']])
            
            assets = query.limit(200).all()  # Limit for performance
            
            return [
                {
                    "ticker": asset.ticker,
                    "name": asset.name,
                    "sector": asset.sector,
                    "market_cap": asset.market_cap,
                    "exchange": asset.exchange
                }
                for asset in assets
            ]
            
        except Exception as e:
            logger.warning(f"Database query failed, using fallback: {e}")
            return self._get_fallback_assets(profile)
    
    def _get_fallback_assets(self, profile: Dict[str, Any]) -> List[Dict]:
        """Fallback asset list if database is unavailable"""
        # Popular ETFs and stocks across different segments
        base_assets = [
            # ETFs
            {"ticker": "SPY", "name": "SPDR S&P 500 ETF", "sector": "ETF", "market_cap": 400, "exchange": "ARCA"},
            {"ticker": "QQQ", "name": "Invesco QQQ Trust", "sector": "ETF", "market_cap": 200, "exchange": "NASDAQ"},
            {"ticker": "IWM", "name": "iShares Russell 2000 ETF", "sector": "ETF", "market_cap": 50, "exchange": "ARCA"},
            {"ticker": "VTI", "name": "Vanguard Total Stock Market ETF", "sector": "ETF", "market_cap": 300, "exchange": "ARCA"},
            
            # Large Cap Stocks
            {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "market_cap": 2800, "exchange": "NASDAQ"},
            {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "market_cap": 3000, "exchange": "NASDAQ"},
            {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "market_cap": 1800, "exchange": "NASDAQ"},
            {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "market_cap": 1600, "exchange": "NASDAQ"},
            
            # Medium Cap Stocks
            {"ticker": "SNOW", "name": "Snowflake Inc.", "sector": "Technology", "market_cap": 60, "exchange": "NYSE"},
            {"ticker": "DDOG", "name": "Datadog Inc.", "sector": "Technology", "market_cap": 40, "exchange": "NASDAQ"},
            
            # Small Cap Stocks
            {"ticker": "UPST", "name": "Upstart Holdings Inc.", "sector": "Financial Services", "market_cap": 3, "exchange": "NASDAQ"},
            {"ticker": "SOFI", "name": "SoFi Technologies Inc.", "sector": "Financial Services", "market_cap": 8, "exchange": "NASDAQ"},
        ]
        
        # Filter based on profile
        filtered_assets = []
        for asset in base_assets:
            if self._matches_profile(asset, profile):
                filtered_assets.append(asset)
                
        return filtered_assets[:100]  # Limit to 100 assets
    
    def _matches_profile(self, asset: Dict, profile: Dict) -> bool:
        """Check if asset matches investment profile"""
        # Market filter
        market_pref = profile.get('preferred_markets', 'sp500')
        if market_pref == 'nasdaq' and asset['exchange'] != 'NASDAQ':
            return False
        if market_pref == 'microcap' and asset.get('market_cap', 100) > 2:
            return False
            
        # Risk filter (simplified)
        risk_tolerance = profile.get('risk_tolerance', 'medium')
        if risk_tolerance == 'low' and asset['sector'] in ['Technology', 'Biotechnology']:
            return False
            
        return True
    
    async def _calculate_asset_metrics(self, assets: List[Dict]) -> List[Dict]:
        """Calculate comprehensive metrics for each asset"""
        tasks = []
        for asset in assets:
            task = self._calculate_single_asset_metrics(asset)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out failed calculations
        successful_results = []
        for result in results:
            if isinstance(result, dict) and 'ticker' in result:
                successful_results.append(result)
        
        logger.info(f"✅ Calculated metrics for {len(successful_results)} assets")
        return successful_results
    
    async def _calculate_single_asset_metrics(self, asset: Dict) -> Dict:
        """Calculate metrics for a single asset"""
        try:
            ticker = asset['ticker']
            
            # Download price data
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            
            if hist.empty:
                return asset
                
            # Calculate technical metrics
            prices = hist['Close']
            returns = prices.pct_change().dropna()
            
            # Momentum metrics
            momentum_1m = (prices.iloc[-1] / prices.iloc[-22] - 1) if len(prices) >= 22 else 0
            momentum_3m = (prices.iloc[-1] / prices.iloc[-66] - 1) if len(prices) >= 66 else 0
            momentum_6m = (prices.iloc[-1] / prices.iloc[-126] - 1) if len(prices) >= 126 else 0
            
            # Volatility
            volatility_30d = returns.tail(30).std() * np.sqrt(252) if len(returns) >= 30 else 0
            
            # RSI (simplified)
            gains = returns[returns > 0].mean() if len(returns[returns > 0]) > 0 else 0
            losses = -returns[returns < 0].mean() if len(returns[returns < 0]) > 0 else 0
            rsi = 100 - (100 / (1 + gains/losses)) if losses != 0 else 50
            
            # Get fundamental data
            info = stock.info
            pe_ratio = info.get('trailingPE', 0)
            pb_ratio = info.get('priceToBook', 0)
            dividend_yield = info.get('dividendYield', 0) or 0
            
            asset.update({
                'current_price': prices.iloc[-1],
                'momentum_1m': momentum_1m,
                'momentum_3m': momentum_3m, 
                'momentum_6m': momentum_6m,
                'volatility_30d': volatility_30d,
                'rsi_14': rsi,
                'pe_ratio': pe_ratio,
                'pb_ratio': pb_ratio,
                'dividend_yield': dividend_yield,
                'volume_avg': hist['Volume'].tail(30).mean()
            })
            
            return asset
            
        except Exception as e:
            logger.warning(f"Failed to calculate metrics for {asset['ticker']}: {e}")
            return asset
    
    async def _ai_score_assets(self, assets: List[Dict], profile: Dict) -> List[Dict]:
        """AI-powered scoring of assets based on investment profile"""
        scored_assets = []
        
        for asset in assets:
            score = await self._calculate_ai_score(asset, profile)
            asset['ai_score'] = score
            asset['profile_compatibility'] = self._calculate_profile_compatibility_single(asset, profile)
            scored_assets.append(asset)
        
        # Sort by AI score
        scored_assets.sort(key=lambda x: x['ai_score'], reverse=True)
        return scored_assets
    
    async def _calculate_ai_score(self, asset: Dict, profile: Dict) -> float:
        """Calculate AI score for asset based on profile"""
        base_score = 0.0
        
        # Investment horizon weighting
        horizon_weights = {
            '3m': {'momentum_1m': 0.4, 'momentum_3m': 0.3, 'momentum_6m': 0.1, 'volatility': 0.2},
            '6m': {'momentum_1m': 0.2, 'momentum_3m': 0.4, 'momentum_6m': 0.3, 'volatility': 0.1},
            '12m': {'momentum_1m': 0.1, 'momentum_3m': 0.2, 'momentum_6m': 0.5, 'fundamentals': 0.2}
        }
        
        weights = horizon_weights.get(profile.get('investment_horizon', '6m'), horizon_weights['6m'])
        
        # Calculate score components
        momentum_score = self._calculate_momentum_score(asset, weights)
        volatility_score = self._calculate_volatility_score(asset, profile)
        fundamental_score = self._calculate_fundamental_score(asset, profile)
        
        # Combine scores based on weights
        if 'fundamentals' in weights:
            base_score = (momentum_score * (1 - weights['fundamentals']) + 
                         fundamental_score * weights['fundamentals'])
        else:
            base_score = momentum_score
            
        # Adjust for risk tolerance
        risk_adjustment = self._adjust_for_risk_tolerance(base_score, asset, profile)
        
        final_score = base_score * risk_adjustment
        
        return min(10.0, max(0.0, final_score))  # Clamp between 0-10
    
    def _calculate_momentum_score(self, asset: Dict, weights: Dict) -> float:
        """Calculate momentum-based score"""
        score = 0.0
        
        if 'momentum_1m' in weights and asset.get('momentum_1m'):
            score += asset['momentum_1m'] * 100 * weights['momentum_1m']  # Convert to percentage
        
        if 'momentum_3m' in weights and asset.get('momentum_3m'):
            score += asset['momentum_3m'] * 100 * weights['momentum_3m']
            
        if 'momentum_6m' in weights and asset.get('momentum_6m'):
            score += asset['momentum_6m'] * 100 * weights['momentum_6m']
            
        return max(0.0, score)
    
    def _calculate_volatility_score(self, asset: Dict, profile: Dict) -> float:
        """Calculate volatility score (lower volatility is better for low risk)"""
        volatility = asset.get('volatility_30d', 0.3)
        risk_tolerance = profile.get('risk_tolerance', 'medium')
        
        # Ideal volatility ranges by risk tolerance
        ideal_ranges = {
            'low': (0.1, 0.2),
            'medium': (0.15, 0.35),
            'high': (0.25, 0.5)
        }
        
        low, high = ideal_ranges.get(risk_tolerance, (0.15, 0.35))
        
        if volatility < low:
            return 0.8  # Too low volatility might mean low returns
        elif low <= volatility <= high:
            return 1.0  # Ideal range
        else:
            # Exponential penalty for high volatility
            excess = volatility - high
            return max(0.1, 1.0 - excess * 2)
    
    def _calculate_fundamental_score(self, asset: Dict, profile: Dict) -> float:
        """Calculate fundamental analysis score"""
        score = 5.0  # Neutral base
        
        # P/E ratio analysis
        pe = asset.get('pe_ratio', 0)
        if 0 < pe < 25:  # Reasonable P/E range
            score += 2.0
        elif pe >= 25:
            score -= 1.0
            
        # Dividend yield (good for income focus)
        dividend_yield = asset.get('dividend_yield', 0)
        if profile.get('investment_priority') == 'income' and dividend_yield > 0.02:
            score += 3.0
            
        # Positive momentum
        if asset.get('momentum_6m', 0) > 0:
            score += 1.0
            
        return max(0.0, score)
    
    def _adjust_for_risk_tolerance(self, score: float, asset: Dict, profile: Dict) -> float:
        """Adjust score based on risk tolerance"""
        risk_tolerance = profile.get('risk_tolerance', 'medium')
        volatility = asset.get('volatility_30d', 0.3)
        
        adjustments = {
            'low': 1.2 if volatility < 0.2 else 0.6,
            'medium': 1.0,  # No adjustment
            'high': 0.8 if volatility < 0.3 else 1.3
        }
        
        return adjustments.get(risk_tolerance, 1.0)
    
    def _calculate_profile_compatibility_single(self, asset: Dict, profile: Dict) -> float:
        """Calculate how well asset matches investment profile"""
        compatibility = 0.0
        
        # Market preference
        market_pref = profile.get('preferred_markets')
        if market_pref == 'nasdaq' and asset.get('exchange') == 'NASDAQ':
            compatibility += 0.3
        elif market_pref == 'sp500' and asset.get('market_cap', 0) > 10:
            compatibility += 0.3
        elif market_pref == 'microcap' and asset.get('market_cap', 100) < 2:
            compatibility += 0.3
            
        # Investment priority
        priority = profile.get('investment_priority')
        if priority == 'income' and asset.get('dividend_yield', 0) > 0.03:
            compatibility += 0.4
        elif priority == 'growth' and asset.get('momentum_6m', 0) > 0.1:
            compatibility += 0.4
        elif priority == 'potential' and asset.get('market_cap', 100) < 5:
            compatibility += 0.4
            
        # Risk tolerance
        risk_tol = profile.get('risk_tolerance')
        volatility = asset.get('volatility_30d', 0.3)
        if risk_tol == 'low' and volatility < 0.25:
            compatibility += 0.3
        elif risk_tol == 'high' and volatility > 0.35:
            compatibility += 0.3
        elif risk_tol == 'medium' and 0.2 <= volatility <= 0.4:
            compatibility += 0.3
            
        return min(1.0, compatibility)
    
    async def _optimize_portfolio(self, scored_assets: List[Dict], profile: Dict, max_assets: int) -> List[Dict]:
        """Optimize portfolio selection considering diversification"""
        diversification_pref = profile.get('diversification_preference', 'balanced')
        
        # Determine target number of assets
        asset_counts = {
            'concentrated': (2, 4),
            'balanced': (5, 8), 
            'diversified': (9, 15)
        }
        
        min_assets, max_assets_target = asset_counts.get(diversification_pref, (5, 8))
        target_assets = min(max_assets, max_assets_target)
        
        # Select top assets with sector diversification
        selected = []
        sectors_seen = set()
        
        for asset in scored_assets:
            if len(selected) >= target_assets:
                break
                
            # Ensure sector diversification
            sector = asset.get('sector', 'Unknown')
            if sector not in sectors_seen or len(sectors_seen) >= 3:
                selected.append(asset)
                sectors_seen.add(sector)
        
        # If we don't have enough assets, add more regardless of sector
        if len(selected) < min_assets:
            for asset in scored_assets:
                if asset not in selected and len(selected) < target_assets:
                    selected.append(asset)
        
        # Calculate weights based on AI scores
        total_score = sum(asset['ai_score'] for asset in selected)
        for asset in selected:
            asset['weight'] = round((asset['ai_score'] / total_score) * 100, 1)
        
        # Normalize weights to sum to 100%
        total_weight = sum(asset['weight'] for asset in selected)
        if total_weight != 100:
            adjustment = 100 / total_weight
            for asset in selected:
                asset['weight'] = round(asset['weight'] * adjustment, 1)
        
        return selected
    
    async def _generate_selection_explanation(self, portfolio: List[Dict], profile: Dict) -> str:
        """Generate AI explanation for portfolio selection"""
        portfolio_summary = ", ".join([f"{p['ticker']} ({p['weight']}%)" for p in portfolio])
        sectors = list(set(p.get('sector', 'Unknown') for p in portfolio))
        
        prompt = f"""
As an expert portfolio manager, explain why this portfolio was selected for the investor's profile.

INVESTOR PROFILE:
- Risk Tolerance: {profile.get('risk_tolerance', 'medium')}
- Investment Horizon: {profile.get('investment_horizon', '6m')}  
- Preferred Markets: {profile.get('preferred_markets', 'sp500')}
- Investment Priority: {profile.get('investment_priority', 'growth')}
- Diversification: {profile.get('diversification_preference', 'balanced')}

SELECTED PORTFOLIO:
{portfolio_summary}

SECTOR DIVERSIFICATION: {', '.join(sectors)}

TOP ASSETS ANALYSIS:
{chr(10).join(f"- {p['ticker']}: AI Score {p['ai_score']:.1f}/10, Momentum {p.get('momentum_6m', 0)*100:.1f}%, Volatility {p.get('volatility_30d', 0)*100:.1f}%" for p in portfolio[:3])}

Please provide:
1. Overall strategy explanation
2. Key strengths of this selection
3. Risk considerations
4. Recommended monitoring approach

Keep it professional but accessible for retail investors.
"""
        
        try:
            return await self.ai_engine.generate_portfolio_explanation({
                "portfolio_summary": portfolio_summary,
                "sectors": sectors,
                "profile": profile,
                "top_assets": portfolio[:3]
            })
        except Exception as e:
            logger.warning(f"AI explanation failed: {e}")
            return "Portfolio selected based on AI analysis of market conditions and your investment profile."
    
    def _calculate_profile_compatibility(self, portfolio: List[Dict], profile: Dict) -> Dict[str, float]:
        """Calculate overall portfolio compatibility with profile"""
        avg_compatibility = np.mean([p.get('profile_compatibility', 0) for p in portfolio])
        
        return {
            "overall_compatibility": round(avg_compatibility, 2),
            "risk_alignment": self._calculate_risk_alignment(portfolio, profile),
            "diversification_score": len(set(p.get('sector', 'Unknown') for p in portfolio)) / len(portfolio)
        }
    
    def _calculate_risk_alignment(self, portfolio: List[Dict], profile: Dict) -> float:
        """Calculate how well portfolio aligns with risk tolerance"""
        avg_volatility = np.mean([p.get('volatility_30d', 0.3) for p in portfolio])
        risk_tolerance = profile.get('risk_tolerance', 'medium')
        
        target_volatilities = {'low': 0.2, 'medium': 0.3, 'high': 0.4}
        target_vol = target_volatilities.get(risk_tolerance, 0.3)
        
        deviation = abs(avg_volatility - target_vol)
        return max(0.0, 1.0 - deviation * 3)  # Penalize deviation from target
    
    async def _get_market_analysis(self) -> Dict[str, Any]:
        """Get current market analysis"""
        # This would integrate with your existing market regime detector
        return {
            "market_regime": "bull_calm",
            "vix_level": 15.2,
            "sector_rotation": "Technology",
            "market_outlook": "positive"
        }