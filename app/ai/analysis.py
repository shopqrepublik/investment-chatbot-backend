from app.ai.forecast_model import GrowthForecaster

class PortfolioAIAnalyzer:
    """AI-анализ портфеля с прогнозом роста и диверсификацией"""

    def __init__(self):
        self.forecaster = GrowthForecaster()

    def analyze(self, tickers):
        results = []
        for t in tickers:
            forecast = self.forecaster.predict_growth(t)
            results.append({
                "ticker": t,
                "predicted_growth_%": forecast.get("predicted_growth_%"),
                "confidence": forecast.get("confidence"),
                "last_close": forecast.get("last_close"),
                "recommendation": forecast.get("predicted_growth_%") and (
                    "Buy ✅" if forecast["predicted_growth_%"] > 5 else
                    "Hold ⚠️" if forecast["predicted_growth_%"] > 0 else
                    "Sell ❌"
                )
            })

        avg_growth = sum(r["predicted_growth_%"] or 0 for r in results) / len(results)
        return {
            "success": True,
            "results": results,
            "average_predicted_growth_%": round(avg_growth, 2),
            "market_sentiment": "Bullish 📈" if avg_growth > 3 else "Neutral ➡️" if avg_growth > 0 else "Bearish 📉"
        }
