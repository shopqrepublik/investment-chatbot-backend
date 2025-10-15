# test_tech_simple.py
import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(__file__))

try:
    from app.analysis.technical_analysis_service import TechnicalAnalysisService
    print("✅ Successfully imported TechnicalAnalysisService")
    
    # Тестируем сервис
    service = TechnicalAnalysisService()
    result = service.analyze_stock('AAPL')
    
    print(f"\n📊 Analysis Result:")
    print(f"Ticker: {result['ticker']}")
    print(f"Recommendation: {result['recommendation']}")
    print(f"Score: {result['technical_score']}/100")
    
except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Trying alternative import...")
    
    # Альтернативный импорт
    try:
        from analysis.technical_analysis_service import TechnicalAnalysisService
        print("✅ Successfully imported with alternative path")
    except ImportError as e2:
        print(f"❌ Alternative import also failed: {e2}")