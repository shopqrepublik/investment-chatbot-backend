# app/models/prediction_pipeline.py
class MultiHorizonPredictor:
    def __init__(self):
        self.horizon_models = {
            '3m': ShortTermPredictor(),      # LSTM + технические индикаторы
            '6m': MediumTermPredictor(),     # XGBoost + фундаментальные
            '12m': LongTermPredictor()       # Фундаментальный анализ
        }
    
    async def predict_all_horizons(self, ticker_data):
        predictions = {}
        
        for horizon, model in self.horizon_models.items():
            predictions[horizon] = await model.predict(ticker_data)
        
        return predictions