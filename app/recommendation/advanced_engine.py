# app/recommendation/advanced_engine.py
class AdvancedRecommendationEngine:
    def calculate_integral_score(self, ticker_data, horizon):
        """Интегральный скоринг по ТЗ"""
        scores = {
            'technical': self._technical_analysis_score(ticker_data),
            'fundamental': self._fundamental_score(ticker_data),
            'sentiment': self._sentiment_score(ticker_data),
            'momentum': self._momentum_score(ticker_data),
            'risk_adjusted': self._risk_adjusted_score(ticker_data)
        }
        
        # Веса из ТЗ
        weights = {
            'technical': 0.3,
            'fundamental': 0.25, 
            'sentiment': 0.2,
            'momentum': 0.15,
            'risk_adjusted': 0.1
        }
        
        total_score = sum(scores[k] * weights[k] for k in scores)
        return total_score