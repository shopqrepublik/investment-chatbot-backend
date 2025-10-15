# app/analysis/technical_analysis_service.py
import pandas as pd
from typing import Dict, List, Optional
import yfinance as yf
import time
import random
import sys
import os

# ✅ Добавляем корневую директорию в путь Python
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

try:
    # ✅ Пробуем импортировать разными способами
    from app.analysis.technical_analyzer import TechnicalAnalyzer
except ImportError:
    try:
        # ✅ Альтернативный способ импорта
        from technical_analyzer import TechnicalAnalyzer
    except ImportError:
        # ✅ Создаем класс напрямую если импорт не работает
        print("⚠️  Could not import TechnicalAnalyzer, creating direct implementation")
        
        # Временно копируем класс TechnicalAnalyzer сюда
        import pandas as pd
        import numpy as np
        import talib
        
        class TechnicalAnalyzer:
            def __init__(self):
                self.indicators_config = {
                    'rsi_period': 14,
                    'macd_fast': 12,
                    'macd_slow': 26, 
                    'macd_signal': 9,
                    'bollinger_period': 20,
                    'bollinger_std': 2,
                    'sma_periods': [20, 50, 200],
                    'ema_periods': [12, 26]
                }
            
            def calculate_all_indicators(self, price_data: pd.DataFrame) -> Dict:
                if price_data.empty or len(price_data) < 50:
                    return self._get_empty_indicators()
                
                try:
                    indicators = {}
                    indicators.update(self._calculate_price_metrics(price_data))
                    indicators.update(self._calculate_rsi(price_data))
                    indicators.update(self._calculate_macd(price_data))
                    indicators.update(self._calculate_moving_averages(price_data))
                    indicators.update(self._calculate_bollinger_bands(price_data))
                    indicators.update(self._calculate_volatility(price_data))
                    indicators.update(self._calculate_volume_indicators(price_data))
                    indicators.update(self._calculate_technical_score(indicators))
                    return indicators
                except Exception as e:
                    print(f"❌ Error calculating indicators: {e}")
                    return self._get_empty_indicators()
            
            def _calculate_price_metrics(self, data: pd.DataFrame) -> Dict:
                close = data['Close']
                high = data['High'] 
                low = data['Low']
                
                return {
                    'current_price': float(close.iloc[-1]),
                    'price_change_1d': float(close.pct_change().iloc[-1] * 100) if len(close) > 1 else 0,
                    'price_change_1w': float(close.pct_change(5).iloc[-1] * 100) if len(close) > 5 else 0,
                    'high_52w': float(high.tail(252).max()) if len(high) >= 252 else float(high.max()),
                    'low_52w': float(low.tail(252).min()) if len(low) >= 252 else float(low.min()),
                }
            
            def _calculate_rsi(self, data: pd.DataFrame) -> Dict:
                close = data['Close']
                try:
                    rsi_14 = talib.RSI(close, timeperiod=14)
                    rsi_14_val = float(rsi_14.iloc[-1]) if not pd.isna(rsi_14.iloc[-1]) else 50
                    return {
                        'rsi_14': rsi_14_val,
                        'rsi_trend': 'bullish' if rsi_14_val > 50 else 'bearish',
                        'rsi_overbought': rsi_14_val > 70,
                        'rsi_oversold': rsi_14_val < 30
                    }
                except Exception as e:
                    return {'rsi_14': 50, 'rsi_trend': 'neutral', 'rsi_overbought': False, 'rsi_oversold': False}
            
            def _calculate_macd(self, data: pd.DataFrame) -> Dict:
                close = data['Close']
                try:
                    macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
                    macd_val = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0
                    return {
                        'macd_line': macd_val,
                        'macd_trend': 'bullish' if macd_val > 0 else 'bearish'
                    }
                except Exception as e:
                    return {'macd_line': 0, 'macd_trend': 'neutral'}
            
            def _calculate_moving_averages(self, data: pd.DataFrame) -> Dict:
                close = data['Close']
                current_price = close.iloc[-1]
                try:
                    sma_20 = close.rolling(20).mean()
                    sma_20_val = float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else current_price
                    price_vs_sma_20 = float((current_price - sma_20_val) / sma_20_val * 100) if sma_20_val > 0 else 0
                    return {
                        'sma_20': sma_20_val,
                        'price_vs_sma_20': price_vs_sma_20
                    }
                except Exception as e:
                    return {'sma_20': current_price, 'price_vs_sma_20': 0}
            
            def _calculate_bollinger_bands(self, data: pd.DataFrame) -> Dict:
                close = data['Close']
                current_price = close.iloc[-1]
                try:
                    bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
                    bb_upper_val = float(bb_upper.iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else current_price
                    bb_lower_val = float(bb_lower.iloc[-1]) if not pd.isna(bb_lower.iloc[-1]) else current_price
                    bb_position = (current_price - bb_lower_val) / (bb_upper_val - bb_lower_val) * 100 if (bb_upper_val - bb_lower_val) > 0 else 50
                    return {
                        'bb_upper': bb_upper_val,
                        'bb_lower': bb_lower_val,
                        'bb_position': float(bb_position)
                    }
                except Exception as e:
                    return {'bb_upper': current_price, 'bb_lower': current_price, 'bb_position': 50}
            
            def _calculate_volatility(self, data: pd.DataFrame) -> Dict:
                close = data['Close']
                try:
                    returns = close.pct_change().dropna()
                    volatility_20d = float(returns.tail(20).std() * np.sqrt(252) * 100) if len(returns) >= 20 else 0
                    return {
                        'volatility_20d': volatility_20d
                    }
                except Exception as e:
                    return {'volatility_20d': 0}
            
            def _calculate_volume_indicators(self, data: pd.DataFrame) -> Dict:
                volume = data['Volume']
                try:
                    volume_sma_20 = volume.rolling(20).mean()
                    volume_val = float(volume.iloc[-1])
                    volume_avg_20d = float(volume_sma_20.iloc[-1]) if not pd.isna(volume_sma_20.iloc[-1]) else volume_val
                    volume_ratio = volume_val / volume_avg_20d if volume_avg_20d > 0 else 1
                    return {
                        'volume_ratio': float(volume_ratio)
                    }
                except Exception as e:
                    return {'volume_ratio': 1}
            
            def _calculate_technical_score(self, indicators: Dict) -> Dict:
                try:
                    score = 50
                    # RSI scoring
                    rsi_score = 80 if 30 <= indicators['rsi_14'] <= 70 else 30
                    # Trend scoring
                    trend_score = 80 if indicators['price_vs_sma_20'] > 0 else 40
                    # MACD scoring
                    macd_score = 80 if indicators.get('macd_trend') == 'bullish' else 40
                    # Volatility scoring
                    vol_score = 100 - min(indicators.get('volatility_20d', 25), 50) * 2
                    
                    total_score = (rsi_score * 0.3 + trend_score * 0.3 + macd_score * 0.2 + vol_score * 0.2)
                    
                    return {
                        'technical_score': round(total_score, 1),
                        'technical_trend': 'bullish' if total_score > 60 else 'bearish' if total_score < 40 else 'neutral'
                    }
                except Exception as e:
                    return {'technical_score': 50, 'technical_trend': 'neutral'}
            
            def _get_empty_indicators(self) -> Dict:
                return {
                    'technical_score': 0,
                    'technical_trend': 'neutral',
                    'current_price': 0,
                    'error': True
                }
            
            def create_sample_data(self) -> pd.DataFrame:
                print("📊 Generating realistic sample data...")
                dates = pd.date_range(start='2024-01-01', end='2024-06-30', freq='D')
                dates = dates[dates.dayofweek < 5]
                
                np.random.seed(42)
                base_price = 150.0
                returns = np.random.normal(0.0005, 0.015, len(dates))
                prices = base_price * np.cumprod(1 + returns)
                
                data = pd.DataFrame(index=dates)
                data['Close'] = prices
                data['Open'] = data['Close'].shift(1) * (1 + np.random.normal(0, 0.005, len(dates)))
                data['High'] = data[['Open', 'Close']].max(axis=1) * (1 + np.abs(np.random.normal(0.005, 0.003, len(dates))))
                data['Low'] = data[['Open', 'Close']].min(axis=1) * (1 - np.abs(np.random.normal(0.005, 0.003, len(dates))))
                data['High'] = data[['Open', 'High', 'Close']].max(axis=1)
                data['Low'] = data[['Open', 'Low', 'Close']].min(axis=1)
                
                daily_volatility = (data['High'] - data['Low']) / data['Close']
                base_volume = 10000000
                data['Volume'] = (base_volume * (1 + daily_volatility * 10) * np.random.uniform(0.8, 1.2, len(dates))).astype(int)
                data = data.ffill().bfill()
                
                print(f"✅ Created {len(data)} days of realistic sample data")
                return data

class TechnicalAnalysisService:
    """
    Service for providing technical analysis in the chatbot
    """
    
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
    
    def analyze_stock(self, ticker: str, period: str = '6mo') -> Dict:
        """
        Analyze a stock and return formatted results for chatbot
        """
        try:
            # Get stock data
            stock_data = self._get_stock_data(ticker, period)
            
            if stock_data.empty:
                # Use sample data for demonstration
                stock_data = self.analyzer.create_sample_data()
                indicators = self.analyzer.calculate_all_indicators(stock_data)
                indicators['using_sample_data'] = True
                indicators['ticker'] = ticker.upper()
            else:
                indicators = self.analyzer.calculate_all_indicators(stock_data)
                indicators['using_sample_data'] = False
                indicators['ticker'] = ticker.upper()
            
            # Format response for chatbot
            return self._format_chatbot_response(indicators)
            
        except Exception as e:
            return {
                'error': True,
                'message': f"Error analyzing {ticker}: {str(e)}",
                'ticker': ticker
            }
    
    def _get_stock_data(self, ticker: str, period: str) -> pd.DataFrame:
        """
        Get stock data with error handling
        """
        try:
            time.sleep(random.uniform(1, 2))
            
            data = yf.download(
                ticker, 
                period=period, 
                interval='1d', 
                progress=False, 
                auto_adjust=True
            )
            
            return data if not data.empty else pd.DataFrame()
            
        except:
            return pd.DataFrame()
    
    def _format_chatbot_response(self, indicators: Dict) -> Dict:
        """
        Format technical indicators for chatbot response
        """
        if indicators.get('error'):
            return {
                'error': True,
                'message': 'Could not calculate technical indicators'
            }
        
        score = indicators.get('technical_score', 50)
        trend = indicators.get('technical_trend', 'neutral')
        
        # Generate recommendation
        if score >= 70:
            recommendation = "STRONG BUY"
            emoji = "🚀"
            reasoning = "Multiple technical indicators show strong bullish signals"
        elif score >= 60:
            recommendation = "BUY" 
            emoji = "📈"
            reasoning = "Technical indicators are generally positive"
        elif score >= 40:
            recommendation = "HOLD"
            emoji = "⚖️"
            reasoning = "Mixed signals, maintain current position"
        elif score >= 30:
            recommendation = "SELL"
            emoji = "📉"
            reasoning = "Technical indicators show bearish tendencies"
        else:
            recommendation = "STRONG SELL"
            emoji = "🔻"
            reasoning = "Multiple indicators show strong bearish signals"
        
        response = {
            'ticker': indicators.get('ticker', 'Unknown'),
            'using_sample_data': indicators.get('using_sample_data', False),
            'technical_score': score,
            'trend': trend.upper(),
            'recommendation': recommendation,
            'emoji': emoji,
            'reasoning': reasoning,
            'key_metrics': {
                'Current Price': f"${indicators.get('current_price', 0):.2f}",
                'Daily Change': f"{indicators.get('price_change_1d', 0):+.2f}%",
                'RSI (14)': f"{indicators.get('rsi_14', 0):.1f}",
                'MACD Trend': indicators.get('macd_trend', 'N/A').title(),
                'Price vs SMA 20': f"{indicators.get('price_vs_sma_20', 0):+.1f}%",
                'Volatility (20d)': f"{indicators.get('volatility_20d', 0):.1f}%",
                'Volume Ratio': f"{indicators.get('volume_ratio', 0):.1f}x"
            }
        }
        
        return response

# Example usage
def test_service():
    """Test the technical analysis service"""
    service = TechnicalAnalysisService()
    
    # Test with a stock
    result = service.analyze_stock('AAPL')
    
    print("🤖 CHATBOT TECHNICAL ANALYSIS")
    print("=" * 50)
    print(f"Ticker: {result['ticker']}")
    print(f"Recommendation: {result['emoji']} {result['recommendation']}")
    print(f"Technical Score: {result['technical_score']}/100")
    print(f"Trend: {result['trend']}")
    print(f"Reasoning: {result['reasoning']}")
    print("\n📊 Key Metrics:")
    for metric, value in result['key_metrics'].items():
        print(f"  {metric}: {value}")
    
    if result['using_sample_data']:
        print("\n⚠️  Note: Using sample data for demonstration")

if __name__ == "__main__":
    test_service()