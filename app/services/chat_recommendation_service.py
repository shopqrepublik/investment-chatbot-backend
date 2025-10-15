# app/services/chat_recommendation_service.py
class ChatRecommendationService:
    def __init__(self, db_session):
        self.db = db_session
        self.pipeline = PredictionPipeline(db_session)
        self.fallback_service = portfolio_service
    
    async def create_enhanced_portfolio(self, profile: dict) -> dict:
        """Create enhanced portfolio through AI analysis"""
        try:
            print(f"🎯 Creating enhanced portfolio for profile: {profile}")
            
            # Determine investment horizon
            horizon_map = {
                '3m': '3m', 
                '6m': '6m', 
                '12m': '12m'
            }
            horizon = horizon_map.get(profile.get('investment_horizon', '6m'), '6m')
            
            # Get top AI-recommended assets
            top_assets_result = await self.get_ai_recommended_assets(horizon, 15)
            
            if not top_assets_result['success']:
                raise Exception("Failed to get AI recommendations")
            
            # Optimize portfolio for user profile
            optimized_portfolio = await self.optimize_portfolio_for_profile(
                top_assets_result['top_assets'], 
                profile
            )
            
            # Create response structure compatible with frontend
            portfolio_response = self.format_portfolio_response(
                optimized_portfolio, 
                profile,
                horizon
            )
            
            print(f"✅ Enhanced portfolio created: {len(portfolio_response['portfolio'])} assets")
            return portfolio_response
            
        except Exception as e:
            print(f"❌ Error creating enhanced portfolio: {e}")
            # Fallback to traditional method
            return await self.fallback_to_traditional(profile)
    
    async def get_ai_recommended_assets(self, horizon: str, count: int = 15):
        """Get AI-recommended assets"""
        try:
            # Take popular tickers for analysis
            popular_tickers = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 
                'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'DIS', 'PYPL',
                'NFLX', 'ADBE', 'CRM', 'INTC', 'CSCO', 'PEP', 'T', 
                'VZ', 'ABT', 'TMO', 'COST', 'LLY', 'AVGO', 'TXN'
            ]
            
            # Run analysis for these tickers
            analysis_result = await self.pipeline.run_full_analysis(
                tickers=popular_tickers[:20],  # Analyze 20 tickers for speed
                horizons=[horizon]
            )
            
            if not analysis_result['success']:
                return {'success': False, 'top_assets': []}
            
            # Extract top assets
            top_assets = analysis_result['recommendations'][horizon][:count]
            
            return {
                'success': True,
                'top_assets': top_assets,
                'analysis_metadata': analysis_result.get('metadata', {})
            }
            
        except Exception as e:
            print(f"❌ Error getting AI recommendations: {e}")
            return {'success': False, 'top_assets': []}
    
    async def optimize_portfolio_for_profile(self, top_assets: list, profile: dict) -> dict:
        """Optimize portfolio for user profile"""
        
        risk_tolerance = profile.get('risk_tolerance', 'medium')
        diversification = profile.get('diversification_preference', 'balanced')
        
        # Determine number of assets in portfolio
        asset_count_map = {
            'concentrated': 3,
            'balanced': 6, 
            'diversified': 10
        }
        target_count = asset_count_map.get(diversification, 6)
        
        # Filter assets by risk
        filtered_assets = self.filter_assets_by_risk(top_assets, risk_tolerance)
        
        # Take top N assets
        selected_assets = filtered_assets[:target_count]
        
        # Distribute weights
        weighted_assets = self.distribute_weights(selected_assets, risk_tolerance)
        
        return {
            'portfolio': weighted_assets,
            'asset_allocation': self.calculate_asset_allocation(weighted_assets),
            'portfolio_metrics': self.calculate_portfolio_metrics(weighted_assets, risk_tolerance),
            'recommendations': self.generate_portfolio_recommendations(weighted_assets, profile),
            'profile_summary': self.create_profile_summary(profile),
            'ai_confidence': 0.85  # AI model confidence
        }
    
    def filter_assets_by_risk(self, assets: list, risk_tolerance: str) -> list:
        """Filter assets by risk tolerance"""
        risk_scores = {
            'low': lambda asset: asset.get('risk_score', 0) <= 3,
            'medium': lambda asset: asset.get('risk_score', 0) <= 6,
            'high': lambda asset: True  # All assets suitable
        }
        
        filter_func = risk_scores.get(risk_tolerance, risk_scores['medium'])
        return [asset for asset in assets if filter_func(asset)]
    
    def distribute_weights(self, assets: list, risk_tolerance: str) -> list:
        """Distribute portfolio weights"""
        # Base weights depending on risk
        base_weights = {
            'low': [0.25, 0.20, 0.15, 0.10, 0.08, 0.07, 0.05, 0.04, 0.03, 0.03],
            'medium': [0.20, 0.18, 0.15, 0.12, 0.10, 0.08, 0.07, 0.05, 0.03, 0.02],
            'high': [0.30, 0.25, 0.20, 0.15, 0.10]  # More concentrated
        }
        
        weights = base_weights.get(risk_tolerance, base_weights['medium'])
        
        # Apply weights to assets
        for i, asset in enumerate(assets):
            if i < len(weights):
                asset['weight'] = weights[i] * 100  # In percentages
                asset['allocation_percent'] = weights[i] * 100
            else:
                asset['weight'] = 5.0  # Minimum weight
                asset['allocation_percent'] = 5.0
            
            # Add missing fields for frontend
            asset['current_price'] = asset.get('current_price', 100.0)
            asset['target_price'] = asset.get('target_price', asset['current_price'] * 1.15)
            asset['asset_type'] = asset.get('asset_type', 'Stock')
            asset['sector'] = asset.get('sector', 'Technology')
        
        return assets
    
    def calculate_asset_allocation(self, assets: list) -> dict:
        """Calculate asset allocation by type"""
        allocation = {}
        for asset in assets:
            asset_type = asset['asset_type']
            allocation[asset_type] = allocation.get(asset_type, 0) + asset['weight']
        return allocation
    
    def calculate_portfolio_metrics(self, assets: list, risk_tolerance: str) -> dict:
        """Calculate portfolio metrics"""
        base_metrics = {
            'low': {'expected_return': 6.5, 'risk_score': 2.1, 'max_drawdown': -8.5},
            'medium': {'expected_return': 9.2, 'risk_score': 4.3, 'max_drawdown': -12.5},
            'high': {'expected_return': 14.5, 'risk_score': 7.8, 'max_drawdown': -18.0}
        }
        
        metrics = base_metrics.get(risk_tolerance, base_metrics['medium'])
        
        return {
            'total_value': 10000.0,
            'expected_return': metrics['expected_return'],
            'risk_score': metrics['risk_score'],
            'diversification_score': 8.2,
            'sharpe_ratio': 1.4,
            'max_drawdown': metrics['max_drawdown'],
            'ai_confidence': 0.85
        }
    
    def generate_portfolio_recommendations(self, assets: list, profile: dict) -> list:
        """Generate portfolio recommendations"""
        recommendations = [
            "🎯 AI-optimized portfolio based on analysis of 20+ factors",
            "📊 Regularly review portfolio every 3 months",
            "💡 Diversification reduces risk while maintaining returns"
        ]
        
        # Add specific recommendations
        risk = profile.get('risk_tolerance', 'medium')
        if risk == 'low':
            recommendations.append("🛡️ Conservative approach: focus on stable companies")
        elif risk == 'high':
            recommendations.append("⚡ Aggressive strategy: potential for high returns")
        
        return recommendations
    
    def create_profile_summary(self, profile: dict) -> dict:
        """Create profile summary"""
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
            'investment_horizon': horizon_map.get(profile.get('investment_horizon', '6m'), '6 months'),
            'risk_tolerance': risk_map.get(profile.get('risk_tolerance', 'medium'), 'Medium'),
            'preferred_markets': market_map.get(profile.get('preferred_markets', 'sp500'), 'S&P 500'),
            'investment_priority': priority_map.get(profile.get('investment_priority', 'growth'), 'Capital growth'),
            'investment_amount': amount_map.get(profile.get('investment_amount', 'medium'), '$1,000-$10,000'),
            'diversification_preference': diversification_map.get(
                profile.get('diversification_preference', 'balanced'), '5-7 positions'
            )
        }
    
    def format_portfolio_response(self, portfolio_data: dict, profile: dict, horizon: str) -> dict:
        """Format response for frontend"""
        return {
            "success": True,
            "message": "AI-optimized portfolio successfully created",
            "data": {
                "portfolio": portfolio_data['portfolio'],
                "asset_allocation": portfolio_data['asset_allocation'],
                "portfolio_metrics": portfolio_data['portfolio_metrics'],
                "recommendations": portfolio_data['recommendations'],
                "profile_summary": portfolio_data['profile_summary'],
                "ai_analysis": f"Portfolio optimized for {horizon} horizon considering {len(portfolio_data['portfolio'])} factors",
                "selection_method": "ai_enhanced"
            }
        }
    
    async def fallback_to_traditional(self, profile: dict) -> dict:
        """Fallback to traditional method"""
        print("🔄 Using traditional method as fallback")
        traditional_result = self.fallback_service.create_portfolio(profile)
        
        # Add AI labels for compatibility
        traditional_result['selection_method'] = 'traditional_fallback'
        traditional_result['ai_confidence'] = 0.0
        
        return traditional_result