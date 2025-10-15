# test_chatbot.py
import sys
import os

# Добавьте путь для импорта
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from analysis.technical_analysis_service import TechnicalAnalysisService

class SimpleChatBot:
    def __init__(self):
        self.tech_service = TechnicalAnalysisService()
    
    def analyze_stock(self, ticker: str):
        """Simple analysis function"""
        print(f"\n🔍 Analyzing {ticker}...")
        result = self.tech_service.analyze_stock(ticker)
        
        print(f"\n🤖 TECHNICAL ANALYSIS RESULTS:")
        print("=" * 50)
        print(f"Stock: {result['ticker']}")
        print(f"Recommendation: {result['emoji']} {result['recommendation']}")
        print(f"Score: {result['technical_score']}/100")
        print(f"Trend: {result['trend']}")
        print(f"Reason: {result['reasoning']}")
        
        print("\n📊 Key Metrics:")
        for metric, value in result['key_metrics'].items():
            print(f"  {metric}: {value}")
        
        if result['using_sample_data']:
            print("\n⚠️  Note: Using sample data (Yahoo Finance might be blocked)")

# Test the integration
if __name__ == "__main__":
    bot = SimpleChatBot()
    
    print("🧪 Testing ChatBot Integration")
    print("=" * 60)
    
    # Test with different stocks
    test_commands = [
        "AAPL",
        "TSLA", 
        "MSFT",
        "GOOGL"
    ]
    
    for stock in test_commands:
        print(f"\n{'='*60}")
        print(f"Testing analysis for {stock}...")
        print('='*60)
        bot.analyze_stock(stock)