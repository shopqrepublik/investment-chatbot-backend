# app/prediction/main_pipeline.py
class PredictionPipeline:
    def __init__(self, db_session):
        self.db = db_session
        self.data_collector = AdvancedDataCollector()
        self.feature_engineer = AdvancedFeatureEngineer() 
        self.predictor = MultiHorizonPredictor()
        self.recommendation_engine = AdvancedRecommendationEngine()
    
    async def run_full_analysis(self, tickers=None, horizons=['3m', '6m', '12m']):
        """Полный пайплайн анализа"""
        print("🎯 Запуск полного анализа...")
        
        # 1. Сбор данных
        print("📊 Сбор данных...")
        ticker_data = await self.data_collector.collect_comprehensive_data(tickers)
        
        # 2. Feature Engineering
        print("🔧 Создание признаков...")
        features = self.feature_engineer.create_all_features(ticker_data)
        
        # 3. Прогнозирование
        print("🤖 Прогнозирование...")
        predictions = {}
        for horizon in horizons:
            predictions[horizon] = await self.predictor.predict(
                features, horizon=horizon
            )
        
        # 4. Рекомендации
        print("💡 Генерация рекомендаций...")
        recommendations = self.recommendation_engine.generate_recommendations(
            predictions, horizons
        )
        
        return {
            'success': True,
            'predictions': predictions,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }