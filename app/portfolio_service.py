from typing import Dict, List, Optional
import json
from sqlalchemy.orm import Session
import logging
from .data_collector import data_collector
from .ticker_lists import ticker_lists
from app.ai.asset_selector import AIAssetSelector

# Настройка логирования
logger = logging.getLogger(__name__)

class PortfolioService:
    """Service for creating investment portfolios with AI optimization"""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.asset_selector = AIAssetSelector(db) if db else None
        self.ASSETS = {
            'etf': {},
            'stocks': {}
        }
        # Initialize with fallback data for faster performance
        self._initialize_fallback_assets()

    def _initialize_fallback_assets(self):
        """Initialize fallback asset lists for fast operation"""
        # Fallback ETFs
        fallback_etfs = {
            'SPY': {'name': 'SPDR S&P 500 ETF', 'risk': 'low', 'type': 'etf', 'sector': 'broad_market'},
            'QQQ': {'name': 'Invesco QQQ Trust', 'risk': 'medium', 'type': 'etf', 'sector': 'technology'},
            'IWM': {'name': 'iShares Russell 2000 ETF', 'risk': 'high', 'type': 'etf', 'sector': 'small_cap'},
            'BND': {'name': 'Vanguard Total Bond Market ETF', 'risk': 'low', 'type': 'etf', 'sector': 'bonds'},
            'GLD': {'name': 'SPDR Gold Shares', 'risk': 'low', 'type': 'etf', 'sector': 'commodities'},
            'VTI': {'name': 'Vanguard Total Stock Market ETF', 'risk': 'low', 'type': 'etf', 'sector': 'broad_market'},
            'VOO': {'name': 'Vanguard S&P 500 ETF', 'risk': 'low', 'type': 'etf', 'sector': 'broad_market'},
            'XLK': {'name': 'Technology Select Sector SPDR', 'risk': 'medium', 'type': 'etf', 'sector': 'technology'},
        }
        
        # Fallback stocks
        fallback_stocks = {
            'AAPL': {'name': 'Apple Inc', 'risk': 'low', 'sector': 'technology'},
            'MSFT': {'name': 'Microsoft Corp', 'risk': 'low', 'sector': 'technology'},
            'GOOGL': {'name': 'Alphabet Inc', 'risk': 'medium', 'sector': 'technology'},
            'AMZN': {'name': 'Amazon.com Inc', 'risk': 'medium', 'sector': 'consumer_discretionary'},
            'TSLA': {'name': 'Tesla Inc', 'risk': 'high', 'sector': 'consumer_discretionary'},
            'NVDA': {'name': 'NVIDIA Corp', 'risk': 'high', 'sector': 'technology'},
            'META': {'name': 'Meta Platforms Inc', 'risk': 'medium', 'sector': 'communication'},
            'JPM': {'name': 'JPMorgan Chase', 'risk': 'medium', 'sector': 'financial'},
            'JNJ': {'name': 'Johnson & Johnson', 'risk': 'low', 'sector': 'healthcare'},
            'V': {'name': 'Visa Inc', 'risk': 'low', 'sector': 'financial'},
            'MSTR': {'name': 'MicroStrategy Inc', 'risk': 'high', 'sector': 'technology'},
            'ARKK': {'name': 'ARK Innovation ETF', 'risk': 'high', 'sector': 'etf'},
        }
        
        # Fixed prices for performance (new tickers added)
        fixed_prices = {
            'SPY': 450.25, 'QQQ': 380.50, 'IWM': 195.75, 'BND': 72.30, 'GLD': 185.40,
            'VTI': 225.60, 'VOO': 420.80, 'XLK': 195.30,
            'AAPL': 175.25, 'MSFT': 330.45, 'GOOGL': 140.75, 'AMZN': 145.80, 'TSLA': 245.30,
            'NVDA': 430.15, 'META': 310.20, 'JPM': 155.60, 'JNJ': 152.40, 'V': 240.85,
            'MSTR': 650.75, 'ARKK': 45.60
        }
        
        # Fixed returns (new tickers added)
        fixed_returns = {
            'SPY': 2.5, 'QQQ': 4.2, 'IWM': 6.8, 'BND': 0.8, 'GLD': 1.2,
            'VTI': 2.8, 'VOO': 2.6, 'XLK': 5.1,
            'AAPL': 3.5, 'MSFT': 2.9, 'GOOGL': 4.1, 'AMZN': 5.2, 'TSLA': 12.5,
            'NVDA': 15.8, 'META': 6.3, 'JPM': 1.8, 'JNJ': 1.2, 'V': 2.4,
            'MSTR': 25.3, 'ARKK': 8.7
        }
        
        for ticker, data in fallback_etfs.items():
            data['current_price'] = fixed_prices.get(ticker, 100.0)
            data['monthly_return'] = fixed_returns.get(ticker, 2.0)
            self.ASSETS['etf'][ticker] = data
            
        for ticker, data in fallback_stocks.items():
            data['current_price'] = fixed_prices.get(ticker, 100.0)
            data['monthly_return'] = fixed_returns.get(ticker, 2.0)
            self.ASSETS['stocks'][ticker] = data
        
        print("✅ Using optimized fallback asset lists")

    async def create_ai_optimized_portfolio(self, profile: dict) -> dict:
        """Create portfolio using AI selection from entire market"""
        try:
            if not self.asset_selector:
                logger.warning("AI Asset Selector not available, using fallback")
                return self.create_portfolio(profile)
            
            # Use AI to select optimal assets
            selection_result = await self.asset_selector.select_optimal_assets(profile)
            
            if not selection_result['success']:
                return self._create_fallback_portfolio(profile)
            
            # Format response
            portfolio_assets = [
                {
                    "ticker": asset["ticker"],
                    "name": asset["name"], 
                    "weight": asset["weight"],
                    "asset_type": "ETF" if "ETF" in asset.get("sector", "") else "Stock",
                    "sector": asset.get("sector", "Unknown"),
                    "current_price": asset.get("current_price", 0),
                    "target_price": round(asset.get("current_price", 0) * 1.15, 2),  # 15% target
                    "ai_score": asset.get("ai_score", 0)
                }
                for asset in selection_result['selected_assets']
            ]
            
            # Calculate portfolio metrics
            portfolio_metrics = self._calculate_portfolio_metrics_fast(portfolio_assets)
            
            result = {
                "portfolio": portfolio_assets,
                "asset_allocation": self._calculate_ai_asset_allocation(portfolio_assets),
                "portfolio_metrics": portfolio_metrics,
                "ai_analysis": selection_result.get('ai_explanation', ''),
                "profile_compatibility": selection_result.get('profile_compatibility', 0),
                "market_analysis": selection_result.get('market_analysis', ''),
                "recommendations": self._generate_recommendations(profile, portfolio_metrics),
                "profile_summary": self._summarize_profile(profile),
                "selection_method": "ai_optimized"
            }
            
            logger.info(f"✅ AI-optimized portfolio created with {len(portfolio_assets)} assets")
            return result
            
        except Exception as e:
            logger.error(f"AI portfolio creation failed: {e}")
            return self._create_fallback_portfolio(profile)

    def create_portfolio(self, profile: Dict, use_ai: bool = False) -> Dict:
        """Creates portfolio based on user profile (supports both AI and classic)"""
        
        if use_ai and self.asset_selector:
            # For sync calls, we'll use thread or return fallback
            logger.info("AI portfolio requested but async method recommended")
            return self._create_fallback_portfolio(profile)
        
        print(f"🔄 Creating classic portfolio for profile: {profile}")
        
        # Calculate asset allocation
        asset_allocation = self._calculate_asset_allocation(profile)
        print(f"📊 Asset allocation: {asset_allocation}")
        
        # Select specific instruments
        portfolio = self._select_instruments_fast(asset_allocation, profile)
        print(f"📈 Selected instruments: {len(portfolio)}")
        
        # Calculate portfolio metrics
        portfolio_metrics = self._calculate_portfolio_metrics_fast(portfolio)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(profile, portfolio_metrics)
        
        result = {
            'portfolio': portfolio,
            'asset_allocation': asset_allocation,
            'portfolio_metrics': portfolio_metrics,
            'recommendations': recommendations,
            'profile_summary': self._summarize_profile(profile),
            'selection_method': 'classic'
        }
        
        print(f"✅ Classic portfolio created: {len(portfolio)} instruments")
        return result
    
    def _create_fallback_portfolio(self, profile: Dict) -> Dict:
        """Create fallback portfolio when AI fails"""
        logger.info("Using fallback portfolio creation")
        return self.create_portfolio(profile, use_ai=False)

    def _calculate_ai_asset_allocation(self, portfolio: List[Dict]) -> Dict:
        """Calculate asset allocation from AI-selected portfolio"""
        allocation = {'etf': 0, 'stocks': 0}
        
        for asset in portfolio:
            if asset['asset_type'] == 'ETF':
                allocation['etf'] += asset['weight']
            else:
                allocation['stocks'] += asset['weight']
        
        return allocation

    def _calculate_asset_allocation(self, profile: Dict) -> Dict:
        """Calculates asset allocation by type (optimized version)"""
        
        horizon = profile['investment_horizon']
        risk = profile['risk_tolerance']
        markets = profile['preferred_markets']
        diversification = profile['diversification_preference']
        
        # Fast predefined allocations
        base_allocations = {
            '3m': {'etf': 30, 'stocks': 70},
            '6m': {'etf': 50, 'stocks': 50},
            '12m': {'etf': 70, 'stocks': 30}
        }
        
        allocation = base_allocations.get(horizon, {'etf': 50, 'stocks': 50}).copy()
        
        # Fast adjustments
        risk_adjustments = {
            'low': {'etf': +20, 'stocks': -20},
            'medium': {'etf': 0, 'stocks': 0},
            'high': {'etf': -20, 'stocks': +20}
        }
        
        adjustment = risk_adjustments.get(risk, {'etf': 0, 'stocks': 0})
        allocation['etf'] += adjustment['etf']
        allocation['stocks'] += adjustment['stocks']
        
        # Normalize to 100%
        total = allocation['etf'] + allocation['stocks']
        if total != 100:
            allocation['etf'] = round(allocation['etf'] / total * 100)
            allocation['stocks'] = 100 - allocation['etf']
        
        return allocation
    
    def _select_instruments_fast(self, allocation: Dict, profile: Dict) -> List[Dict]:
        """Fast instrument selection for portfolio"""
        
        portfolio = []
        risk = profile['risk_tolerance']
        markets = profile['preferred_markets']
        diversification = profile['diversification_preference']
        
        # Determine number of positions
        position_counts = {
            'concentrated': 3,
            'balanced': 6,
            'diversified': 10
        }
        num_positions = position_counts.get(diversification, 6)
        
        # ETF portion of portfolio
        etf_weight = allocation['etf']
        if etf_weight > 0:
            etf_selection = self._select_etfs_fast(risk, markets, max(1, num_positions // 2))
            if etf_selection:
                weight_per_etf = etf_weight / len(etf_selection)
                
                for etf in etf_selection:
                    asset_data = self.ASSETS['etf'][etf]
                    portfolio.append({
                        'ticker': etf,
                        'name': asset_data['name'],
                        'asset_type': 'ETF',
                        'weight': round(weight_per_etf, 1),
                        'current_price': asset_data.get('current_price', 0),
                        'target_price': round(asset_data.get('current_price', 0) * 1.1, 2),
                        'sector': asset_data['sector'],
                        'allocation_percent': round(weight_per_etf, 1)
                    })
        
        # Stock portion of portfolio
        stock_weight = allocation['stocks']
        if stock_weight > 0:
            stock_selection = self._select_stocks_fast(risk, markets, max(1, num_positions))
            if stock_selection:
                weight_per_stock = stock_weight / len(stock_selection)
                
                for stock in stock_selection:
                    asset_data = self.ASSETS['stocks'][stock]
                    portfolio.append({
                        'ticker': stock,
                        'name': asset_data['name'],
                        'asset_type': 'Stock',
                        'weight': round(weight_per_stock, 1),
                        'current_price': asset_data.get('current_price', 0),
                        'target_price': round(asset_data.get('current_price', 0) * 1.15, 2),
                        'sector': asset_data['sector'],
                        'allocation_percent': round(weight_per_stock, 1)
                    })
        
        # GUARANTEE PORTFOLIO IS NOT EMPTY
        if not portfolio:
            # Add default basic instruments
            default_etf = 'VOO'
            asset_data = self.ASSETS['etf'][default_etf]
            portfolio.append({
                'ticker': default_etf,
                'name': asset_data['name'],
                'asset_type': 'ETF',
                'weight': 100.0,
                'current_price': asset_data.get('current_price', 0),
                'target_price': round(asset_data.get('current_price', 0) * 1.1, 2),
                'sector': asset_data['sector'],
                'allocation_percent': 100.0
            })
        
        return portfolio
    
    def _select_etfs_fast(self, risk: str, markets: str, max_count: int) -> List[str]:
        """Fast ETF selection"""
        
        # Predefined lists by risk
        risk_based_etfs = {
            'low': ['VOO', 'VTI', 'BND', 'GLD'],
            'medium': ['SPY', 'QQQ', 'VOO', 'IWM'],
            'high': ['QQQ', 'IWM', 'SPY']
        }
        
        candidates = risk_based_etfs.get(risk, ['VOO', 'SPY', 'QQQ'])
        
        # Market-based adjustments
        if markets == 'nasdaq':
            candidates = ['QQQ', 'XLK'] + [c for c in candidates if c != 'QQQ']
        elif markets == 'sp500':
            candidates = ['SPY', 'VOO'] + [c for c in candidates if c not in ['SPY', 'VOO']]
        
        # FILTER ONLY EXISTING TICKERS
        available_etfs = [ticker for ticker in candidates if ticker in self.ASSETS['etf']]
        
        # If no ETFs available, return basic ones
        if not available_etfs:
            available_etfs = ['VOO', 'SPY', 'QQQ']
        
        return available_etfs[:max_count]
    
    def _select_stocks_fast(self, risk: str, markets: str, max_count: int) -> List[str]:
        """Fast stock selection"""
        
        # Predefined lists by risk
        risk_based_stocks = {
            'low': ['AAPL', 'MSFT', 'JNJ', 'V', 'JPM'],
            'medium': ['GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA'],
            'high': ['TSLA', 'NVDA', 'MSTR', 'ARKK']
        }
        
        candidates = risk_based_stocks.get(risk, ['AAPL', 'MSFT', 'GOOGL'])
        
        # Market-based adjustments
        if markets == 'nasdaq':
            tech_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA']
            candidates = tech_stocks + [c for c in candidates if c not in tech_stocks]
        elif markets == 'sp500':
            stable_stocks = ['JNJ', 'JPM', 'V', 'XOM', 'PG']
            candidates = stable_stocks + [c for c in candidates if c not in stable_stocks]
        
        # FILTER ONLY EXISTING STOCKS
        available_stocks = [ticker for ticker in candidates if ticker in self.ASSETS['stocks']]
        
        # If no stocks available, return basic ones
        if not available_stocks:
            available_stocks = ['AAPL', 'MSFT', 'GOOGL']
        
        return available_stocks[:max_count]
    
    def _calculate_portfolio_metrics_fast(self, portfolio: List[Dict]) -> Dict:
        """Fast portfolio metrics calculation"""
        if not portfolio:
            return {
                "total_value": 10000.0,
                "expected_return": 5.0,
                "risk_score": 3.0,
                "diversification_score": 5.0,
                "sharpe_ratio": 1.0,
                "max_drawdown": -10.0
            }
        
        # Simple calculation based on weights and predefined data
        total_return = sum(item['weight'] * self._get_expected_return(item['ticker']) for item in portfolio) / 100
        risk_score = sum(item['weight'] * self._get_risk_score(item['ticker']) for item in portfolio) / 100
        
        return {
            "total_value": 10000.0,
            "expected_return": round(total_return, 2),
            "risk_score": round(risk_score, 2),
            "diversification_score": min(10, len(portfolio) * 1.5),
            "sharpe_ratio": round(total_return / max(risk_score, 0.1), 2),
            "max_drawdown": round(-risk_score * 3, 2)
        }
    
    def _get_expected_return(self, ticker: str) -> float:
        """Returns expected return for ticker"""
        returns_map = {
            'VOO': 7.5, 'SPY': 7.8, 'QQQ': 9.2, 'IWM': 8.5, 'BND': 3.2, 'GLD': 2.5,
            'VTI': 7.2, 'XLK': 8.1,
            'AAPL': 8.5, 'MSFT': 7.9, 'GOOGL': 9.1, 'AMZN': 10.2, 'TSLA': 15.5,
            'NVDA': 18.8, 'META': 11.3, 'JPM': 5.8, 'JNJ': 4.2, 'V': 6.4,
            'MSTR': 22.5, 'ARKK': 12.3
        }
        return returns_map.get(ticker, 7.0)
    
    def _get_risk_score(self, ticker: str) -> float:
        """Returns risk score for ticker"""
        risk_map = {
            'VOO': 2.0, 'SPY': 2.1, 'QQQ': 3.5, 'IWM': 4.2, 'BND': 1.2, 'GLD': 1.8,
            'VTI': 2.3, 'XLK': 3.8,
            'AAPL': 2.5, 'MSFT': 2.4, 'GOOGL': 3.2, 'AMZN': 3.8, 'TSLA': 6.5,
            'NVDA': 5.8, 'META': 4.3, 'JPM': 2.8, 'JNJ': 1.9, 'V': 2.6,
            'MSTR': 7.2, 'ARKK': 6.8
        }
        return risk_map.get(ticker, 3.0)
    
    def _generate_recommendations(self, profile: Dict, metrics: Dict) -> List[str]:
        """Generates recommendations based on profile and metrics"""
        
        recommendations = []
        horizon = profile['investment_horizon']
        risk = profile['risk_tolerance']
        
        # Horizon-based recommendations
        if horizon == '3m':
            recommendations.append("🕒 Short horizon (3 months): Recommend active monitoring and readiness for corrections")
        elif horizon == '6m':
            recommendations.append("📊 Medium horizon (6 months): Balance of growth and stability, periodic rebalancing")
        else:
            recommendations.append("🎯 Long horizon (12 months): Can take more risk, focus on fundamental indicators")
        
        # Risk-based recommendations
        if risk == 'low':
            recommendations.append("🛡️ Conservative approach: Main focus on capital protection and stable income")
        elif risk == 'high':
            recommendations.append("🚀 Aggressive strategy: High return potential, be prepared for volatility")
        
        # Diversification recommendations
        if profile['diversification_preference'] == 'concentrated':
            recommendations.append("🎯 Concentrated portfolio: High growth potential but requires active management")
        elif profile['diversification_preference'] == 'diversified':
            recommendations.append("🌍 Diversified portfolio: Risk reduction through broad market coverage")
        
        # General recommendations
        recommendations.append("💰 Start with a small amount to test the strategy")
        recommendations.append("📈 Regularly monitor portfolio performance")
        
        return recommendations[:4]  # Limit to 4 recommendations
    
    def _summarize_profile(self, profile: Dict) -> Dict:
        """Creates user profile summary"""
        
        horizon_map = {'3m': '3 months', '6m': '6 months', '12m': '12 months'}
        risk_map = {'low': 'Low', 'medium': 'Medium', 'high': 'High'}
        market_map = {'sp500': 'S&P 500', 'nasdaq': 'Nasdaq', 'microcap': 'Micro-cap'}
        priority_map = {'income': 'Stable income', 'growth': 'Capital growth', 'potential': 'Maximum potential'}
        amount_map = {'low': 'up to $1,000', 'medium': '$1,000-$10,000', 'high': '$10,000+'}
        diversification_map = {
            'concentrated': '2-3 ideas', 
            'balanced': '5-7 positions', 
            'diversified': '10+ instruments'
        }
        
        return {
            'investment_horizon': horizon_map[profile['investment_horizon']],
            'risk_tolerance': risk_map[profile['risk_tolerance']],
            'preferred_markets': market_map[profile['preferred_markets']],
            'investment_priority': priority_map[profile['investment_priority']],
            'investment_amount': amount_map[profile['investment_amount']],
            'diversification_preference': diversification_map[profile['diversification_preference']]
        }

# Create service instance (maintains backward compatibility)
portfolio_service = PortfolioService()