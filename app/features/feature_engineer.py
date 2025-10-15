# app/features/feature_engineer.py
class AdvancedFeatureEngineer:
    def create_technical_features(self, price_data):
        features = {}
        
        # Базовые технические индикаторы
        features['sma_20'] = price_data.rolling(20).mean()
        features['sma_50'] = price_data.rolling(50).mean()
        features['rsi_14'] = self._calculate_rsi(price_data, 14)
        features['macd'] = self._calculate_macd(price_data)
        features['bollinger_bands'] = self._calculate_bollinger_bands(price_data)
        
        return features
    
    def create_macro_features(self, ticker_data):
        """Макроэкономические признаки"""
        # Интеграция с FRED API
        # Процентные ставки, инфляция, VIX и т.д.
        pass