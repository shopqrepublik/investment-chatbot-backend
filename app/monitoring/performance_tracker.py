# app/monitoring/performance_tracker.py
class PerformanceTracker:
    def __init__(self, db_session):
        self.db = db_session
    
    async def track_prediction_accuracy(self):
        """Трекинг точности прогнозов"""
        # Сравниваем прогнозы с фактическими ценами
        # Вычисляем Hit Rate, Information Ratio и т.д.
        pass
    
    def calculate_hit_rate(self, predictions, actuals):
        """Вычисление Hit Rate"""
        correct_direction = 0
        total = len(predictions)
        
        for pred, actual in zip(predictions, actuals):
            if (pred > 0 and actual > 0) or (pred < 0 and actual < 0):
                correct_direction += 1
        
        return correct_direction / total if total > 0 else 0