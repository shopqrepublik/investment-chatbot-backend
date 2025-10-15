# app/analysis/technical_analyzer.py
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, List, Optional
import talib
from datetime import datetime, timedelta
import time
import random

class TechnicalAnalyzer:
    """
    Technical indicator analyzer for stocks and ETFs
    """
    
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
    
    def get_stock_data(self, ticker: str, period: str = '6mo') -> pd.DataFrame:
        """
        Get stock data with robust error handling and rate limiting
        """
        try:
            print(f"📥 Downloading data for {ticker}...")
            
            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))
            
            # Method 1: Try direct download first (less API calls)
            try:
                data = yf.download(
                    ticker, 
                    period=period, 
                    interval='1d', 
                    progress=False, 
                    auto_adjust=True,
                    threads=False  # Disable parallel downloads
                )
                
                if not data.empty:
                    print(f"✅ Successfully downloaded {len(data)} days for {ticker}")
                    return data
                    
            except Exception as e:
                print(f"⚠️  Direct download failed for {ticker}: {e}")
            
            # Method 2: Fallback to Ticker method
            try:
                stock = yf.Ticker(ticker)
                
                # Get history directly without checking info first
                data = stock.history(
                    period=period, 
                    interval='1d', 
                    auto_adjust=True,
                    actions=False  # Disable dividend and stock split adjustments
                )
                
                if data.empty:
                    print(f"❌ No historical data for {ticker}")
                    return pd.DataFrame()
                
                print(f"✅ Successfully downloaded {len(data)} days for {ticker} (method 2)")
                return data
                
            except Exception as e:
                print(f"❌ Both methods failed for {ticker}: {e}")
                return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ Error downloading {ticker}: {e}")
            return pd.DataFrame()
    
    def calculate_all_indicators(self, price_data: pd.DataFrame) -> Dict:
        """
        Calculate all technical indicators
        
        Args:
            price_data: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
            
        Returns:
            Dict with all calculated indicators
        """
        if price_data.empty or len(price_data) < 50:
            return self._get_empty_indicators()
        
        try:
            indicators = {}
            
            # 1. Basic price metrics
            indicators.update(self._calculate_price_metrics(price_data))
            
            # 2. RSI - Relative Strength Index
            indicators.update(self._calculate_rsi(price_data))
            
            # 3. MACD - Moving Average Convergence Divergence
            indicators.update(self._calculate_macd(price_data))
            
            # 4. Moving averages
            indicators.update(self._calculate_moving_averages(price_data))
            
            # 5. Bollinger Bands
            indicators.update(self._calculate_bollinger_bands(price_data))
            
            # 6. Volatility
            indicators.update(self._calculate_volatility(price_data))
            
            # 7. Volume indicators
            indicators.update(self._calculate_volume_indicators(price_data))
            
            # 8. Combined technical score
            indicators.update(self._calculate_technical_score(indicators))
            
            return indicators
            
        except Exception as e:
            print(f"❌ Error calculating indicators: {e}")
            return self._get_empty_indicators()
    
    def _calculate_price_metrics(self, data: pd.DataFrame) -> Dict:
        """Basic price metrics"""
        close = data['Close']
        high = data['High'] 
        low = data['Low']
        
        return {
            'current_price': float(close.iloc[-1]),
            'price_change_1d': float(close.pct_change().iloc[-1] * 100) if len(close) > 1 else 0,
            'price_change_1w': float(close.pct_change(5).iloc[-1] * 100) if len(close) > 5 else 0,
            'price_change_1m': float(close.pct_change(21).iloc[-1] * 100) if len(close) > 21 else 0,
            'high_52w': float(high.tail(252).max()) if len(high) >= 252 else float(high.max()),
            'low_52w': float(low.tail(252).min()) if len(low) >= 252 else float(low.min()),
            'distance_to_high': float((close.iloc[-1] - high.tail(252).max()) / high.tail(252).max() * 100) if len(high) >= 252 else 0,
            'distance_to_low': float((close.iloc[-1] - low.tail(252).min()) / low.tail(252).min() * 100) if len(low) >= 252 else 0
        }
    
    def _calculate_rsi(self, data: pd.DataFrame) -> Dict:
        """Calculate RSI"""
        close = data['Close']
        
        try:
            # Use TA-Lib for accurate RSI
            rsi_14 = talib.RSI(close, timeperiod=14)
            rsi_7 = talib.RSI(close, timeperiod=7)
            rsi_21 = talib.RSI(close, timeperiod=21)
            
            rsi_14_val = float(rsi_14.iloc[-1]) if not pd.isna(rsi_14.iloc[-1]) else 50
            rsi_7_val = float(rsi_7.iloc[-1]) if not pd.isna(rsi_7.iloc[-1]) else 50
            rsi_21_val = float(rsi_21.iloc[-1]) if not pd.isna(rsi_21.iloc[-1]) else 50
            
            return {
                'rsi_14': rsi_14_val,
                'rsi_7': rsi_7_val,
                'rsi_21': rsi_21_val,
                'rsi_trend': 'bullish' if rsi_14_val > 50 else 'bearish',
                'rsi_overbought': rsi_14_val > 70,
                'rsi_oversold': rsi_14_val < 30
            }
        except Exception as e:
            print(f"❌ RSI calculation error: {e}")
            return {
                'rsi_14': 50, 'rsi_7': 50, 'rsi_21': 50,
                'rsi_trend': 'neutral', 'rsi_overbought': False, 'rsi_oversold': False
            }
    
    def _calculate_macd(self, data: pd.DataFrame) -> Dict:
        """Calculate MACD"""
        close = data['Close']
        
        try:
            macd, macd_signal, macd_hist = talib.MACD(
                close, 
                fastperiod=12, 
                slowperiod=26, 
                signalperiod=9
            )
            
            macd_val = float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0
            macd_signal_val = float(macd_signal.iloc[-1]) if not pd.isna(macd_signal.iloc[-1]) else 0
            macd_hist_val = float(macd_hist.iloc[-1]) if not pd.isna(macd_hist.iloc[-1]) else 0
            
            return {
                'macd_line': macd_val,
                'macd_signal': macd_signal_val,
                'macd_histogram': macd_hist_val,
                'macd_trend': 'bullish' if macd_val > macd_signal_val else 'bearish',
                'macd_crossed': 'above' if macd_val > macd_signal_val and macd.iloc[-2] <= macd_signal.iloc[-2] else 
                               'below' if macd_val < macd_signal_val and macd.iloc[-2] >= macd_signal.iloc[-2] else 'none'
            }
        except Exception as e:
            print(f"❌ MACD calculation error: {e}")
            return {
                'macd_line': 0, 'macd_signal': 0, 'macd_histogram': 0,
                'macd_trend': 'neutral', 'macd_crossed': 'none'
            }
    
    def _calculate_moving_averages(self, data: pd.DataFrame) -> Dict:
        """Calculate moving averages"""
        close = data['Close']
        current_price = close.iloc[-1]
        
        try:
            sma_20 = close.rolling(20).mean()
            sma_50 = close.rolling(50).mean() 
            sma_200 = close.rolling(200).mean()
            
            ema_12 = talib.EMA(close, timeperiod=12)
            ema_26 = talib.EMA(close, timeperiod=26)
            
            sma_20_val = float(sma_20.iloc[-1]) if not pd.isna(sma_20.iloc[-1]) else current_price
            sma_50_val = float(sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else current_price
            sma_200_val = float(sma_200.iloc[-1]) if not pd.isna(sma_200.iloc[-1]) else current_price
            
            price_vs_sma_20 = float((current_price - sma_20_val) / sma_20_val * 100) if sma_20_val > 0 else 0
            
            return {
                'sma_20': sma_20_val,
                'sma_50': sma_50_val,
                'sma_200': sma_200_val,
                'ema_12': float(ema_12.iloc[-1]) if not pd.isna(ema_12.iloc[-1]) else current_price,
                'ema_26': float(ema_26.iloc[-1]) if not pd.isna(ema_26.iloc[-1]) else current_price,
                'price_vs_sma_20': price_vs_sma_20,
                'golden_cross': sma_50_val > sma_200_val and sma_50.iloc[-2] <= sma_200.iloc[-2] if len(sma_50) > 1 else False,
                'death_cross': sma_50_val < sma_200_val and sma_50.iloc[-2] >= sma_200.iloc[-2] if len(sma_50) > 1 else False
            }
        except Exception as e:
            print(f"❌ Moving averages calculation error: {e}")
            return {
                'sma_20': current_price, 'sma_50': current_price, 'sma_200': current_price,
                'ema_12': current_price, 'ema_26': current_price, 'price_vs_sma_20': 0,
                'golden_cross': False, 'death_cross': False
            }
    
    def _calculate_bollinger_bands(self, data: pd.DataFrame) -> Dict:
        """Calculate Bollinger Bands"""
        close = data['Close']
        current_price = close.iloc[-1]
        
        try:
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                close, 
                timeperiod=20, 
                nbdevup=2, 
                nbdevdn=2, 
                matype=0
            )
            
            bb_upper_val = float(bb_upper.iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else current_price
            bb_middle_val = float(bb_middle.iloc[-1]) if not pd.isna(bb_middle.iloc[-1]) else current_price
            bb_lower_val = float(bb_lower.iloc[-1]) if not pd.isna(bb_lower.iloc[-1]) else current_price
            
            bb_position = (current_price - bb_lower_val) / (bb_upper_val - bb_lower_val) * 100 if (bb_upper_val - bb_lower_val) > 0 else 50
            
            return {
                'bb_upper': bb_upper_val,
                'bb_middle': bb_middle_val,
                'bb_lower': bb_lower_val,
                'bb_width': float((bb_upper_val - bb_lower_val) / bb_middle_val * 100) if bb_middle_val > 0 else 0,
                'bb_position': float(bb_position),
                'bb_squeeze': (bb_upper_val - bb_lower_val) / bb_middle_val < 0.1 if bb_middle_val > 0 else False
            }
        except Exception as e:
            print(f"❌ Bollinger Bands calculation error: {e}")
            return {
                'bb_upper': current_price, 'bb_middle': current_price, 'bb_lower': current_price,
                'bb_width': 0, 'bb_position': 50, 'bb_squeeze': False
            }
    
    def _calculate_volatility(self, data: pd.DataFrame) -> Dict:
        """Calculate volatility metrics"""
        close = data['Close']
        
        try:
            returns = close.pct_change().dropna()
            
            volatility_20d = float(returns.tail(20).std() * np.sqrt(252) * 100) if len(returns) >= 20 else 0
            volatility_60d = float(returns.tail(60).std() * np.sqrt(252) * 100) if len(returns) >= 60 else 0
            
            return {
                'volatility_20d': volatility_20d,
                'volatility_60d': volatility_60d,
                'atr_14': float(self._calculate_atr(data, 14)),
                'max_drawdown_1y': float(self._calculate_max_drawdown(close.tail(252))) if len(close) >= 252 else 0
            }
        except Exception as e:
            print(f"❌ Volatility calculation error: {e}")
            return {
                'volatility_20d': 0, 'volatility_60d': 0, 'atr_14': 0, 'max_drawdown_1y': 0
            }
    
    def _calculate_atr(self, data: pd.DataFrame, period: int) -> float:
        """Average True Range"""
        try:
            high = data['High']
            low = data['Low']
            close = data['Close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(period).mean()
            
            return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0
        except:
            return 0
    
    def _calculate_max_drawdown(self, prices: pd.Series) -> float:
        """Maximum drawdown"""
        try:
            cumulative = (1 + prices.pct_change()).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return drawdown.min() * 100
        except:
            return 0
    
    def _calculate_volume_indicators(self, data: pd.DataFrame) -> Dict:
        """Volume indicators"""
        volume = data['Volume']
        close = data['Close']
        
        try:
            # On-Balance Volume
            obv = talib.OBV(close, volume)
            
            # Volume SMA
            volume_sma_20 = volume.rolling(20).mean()
            
            volume_val = float(volume.iloc[-1])
            volume_avg_20d = float(volume_sma_20.iloc[-1]) if not pd.isna(volume_sma_20.iloc[-1]) else volume_val
            volume_ratio = volume_val / volume_avg_20d if volume_avg_20d > 0 else 1
            
            return {
                'volume': volume_val,
                'volume_avg_20d': volume_avg_20d,
                'volume_ratio': float(volume_ratio),
                'obv': float(obv.iloc[-1]) if not pd.isna(obv.iloc[-1]) else 0,
                'obv_trend': 'rising' if obv.iloc[-1] > obv.iloc[-5] else 'falling'
            }
        except Exception as e:
            print(f"❌ Volume indicators calculation error: {e}")
            return {
                'volume': 0, 'volume_avg_20d': 0, 'volume_ratio': 1, 'obv': 0, 'obv_trend': 'neutral'
            }
    
    def _calculate_technical_score(self, indicators: Dict) -> Dict:
        """Combined technical score (0-100)"""
        try:
            score = 50  # Base score
            
            # RSI scoring (30%)
            rsi_score = 0
            if 30 <= indicators['rsi_14'] <= 70:
                rsi_score = 80  # Neutral is good
            elif 40 <= indicators['rsi_14'] <= 60:
                rsi_score = 100  # Perfect range
            else:
                rsi_score = 30  # Overbought/oversold
            
            # Trend scoring (30%)
            trend_score = 0
            if indicators['price_vs_sma_20'] > 0:
                trend_score = 80
            if indicators.get('golden_cross', False):
                trend_score = 100
            elif indicators.get('death_cross', False):
                trend_score = 20
            else:
                trend_score = 60
            
            # MACD scoring (20%)
            macd_score = 80 if indicators.get('macd_trend') == 'bullish' else 40
            
            # Volatility scoring (20%)
            vol_score = 100 - min(indicators.get('volatility_20d', 25), 50) * 2  # Lower volatility better
            
            # Combine scores
            total_score = (
                rsi_score * 0.3 +
                trend_score * 0.3 + 
                macd_score * 0.2 +
                vol_score * 0.2
            )
            
            return {
                'technical_score': round(total_score, 1),
                'technical_trend': 'bullish' if total_score > 60 else 'bearish' if total_score < 40 else 'neutral'
            }
        except Exception as e:
            print(f"❌ Technical score calculation error: {e}")
            return {
                'technical_score': 50,
                'technical_trend': 'neutral'
            }
    
    def _get_empty_indicators(self) -> Dict:
        """Empty indicators for error cases"""
        return {
            'technical_score': 0,
            'technical_trend': 'neutral',
            'current_price': 0,
            'error': True
        }

    def create_sample_data(self) -> pd.DataFrame:
        """Create realistic sample price data for testing when real data is unavailable"""
        print("📊 Generating realistic sample data...")
        
        # Create 6 months of trading days
        dates = pd.date_range(start='2024-01-01', end='2024-06-30', freq='D')
        # Filter to weekdays only (trading days)
        dates = dates[dates.dayofweek < 5]
        
        np.random.seed(42)  # For reproducible results
        
        # Generate realistic price data with upward trend and volatility
        base_price = 150.0
        returns = np.random.normal(0.0005, 0.015, len(dates))  # Small daily drift + volatility
        prices = base_price * np.cumprod(1 + returns)
        
        # Generate OHLC data with realistic patterns
        data = pd.DataFrame(index=dates)
        data['Close'] = prices
        
        # Generate Open, High, Low with realistic relationships
        data['Open'] = data['Close'].shift(1) * (1 + np.random.normal(0, 0.005, len(dates)))
        data['High'] = data[['Open', 'Close']].max(axis=1) * (1 + np.abs(np.random.normal(0.005, 0.003, len(dates))))
        data['Low'] = data[['Open', 'Close']].min(axis=1) * (1 - np.abs(np.random.normal(0.005, 0.003, len(dates))))
        
        # Ensure High is highest, Low is lowest
        data['High'] = data[['Open', 'High', 'Close']].max(axis=1)
        data['Low'] = data[['Open', 'Low', 'Close']].min(axis=1)
        
        # Realistic volume data (higher on volatile days)
        daily_volatility = (data['High'] - data['Low']) / data['Close']
        base_volume = 10000000  # 10 million shares
        data['Volume'] = (base_volume * (1 + daily_volatility * 10) * 
                         np.random.uniform(0.8, 1.2, len(dates))).astype(int)
        
        # Fill NaN values
        data = data.ffill().bfill()
        
        print(f"✅ Created {len(data)} days of realistic sample data")
        return data


def test_technical_analyzer():
    """Test the technical analyzer with robust error handling"""
    print("🧪 Testing Technical Analyzer...")
    
    analyzer = TechnicalAnalyzer()
    
    # Test with fewer tickers to avoid rate limiting
    test_cases = [
        {'ticker': 'AAPL', 'period': '3mo'},  # Shorter period
        {'ticker': 'MSFT', 'period': '3mo'},
    ]
    
    successful_test = False
    
    for test_case in test_cases:
        ticker = test_case['ticker']
        period = test_case['period']
        
        print(f"\n🔍 Testing {ticker} with {period} period...")
        
        try:
            # Use the new method to get data
            test_data = analyzer.get_stock_data(ticker, period)
            
            if test_data.empty:
                print(f"❌ No data for {ticker}")
                continue
                
            print(f"✅ Downloaded {len(test_data)} trading days")
            
            # Check if we have enough data
            if len(test_data) < 30:
                print(f"⚠️  Insufficient data: only {len(test_data)} days")
                continue
            
            # Ensure we have required columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing_columns = [col for col in required_columns if col not in test_data.columns]
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                continue
            
            # Calculate indicators
            print("📈 Calculating technical indicators...")
            indicators = analyzer.calculate_all_indicators(test_data)
            
            # Check if indicators were calculated successfully
            if indicators.get('error'):
                print("❌ Error in indicator calculation")
                continue
                
            # Display results
            print(f"\n🎯 {ticker} Technical Analysis:")
            print("=" * 50)
            
            # Key metrics to display
            display_metrics = {
                'Price': f"${indicators.get('current_price', 0):.2f}",
                'Daily Change': f"{indicators.get('price_change_1d', 0):+.2f}%",
                'Weekly Change': f"{indicators.get('price_change_1w', 0):+.2f}%",
                'RSI (14)': f"{indicators.get('rsi_14', 0):.1f}",
                'MACD Trend': indicators.get('macd_trend', 'N/A'),
                'SMA 20 vs Price': f"{indicators.get('price_vs_sma_20', 0):+.1f}%",
                'Volatility (20d)': f"{indicators.get('volatility_20d', 0):.1f}%",
                'Volume Ratio': f"{indicators.get('volume_ratio', 0):.1f}x",
                'Technical Score': f"{indicators.get('technical_score', 0):.1f}/100",
                'Overall Trend': indicators.get('technical_trend', 'N/A').upper()
            }
            
            for metric, value in display_metrics.items():
                print(f"  {metric:<18}: {value}")
            
            # Additional indicators
            print(f"\n  RSI Status: {'🔴 Overbought' if indicators.get('rsi_overbought') else '🟢 Oversold' if indicators.get('rsi_oversold') else '⚪ Neutral'}")
            print(f"  Golden Cross: {'✅ Yes' if indicators.get('golden_cross') else '❌ No'}")
            print(f"  Death Cross: {'✅ Yes' if indicators.get('death_cross') else '❌ No'}")
            
            # Success - we found working data
            print(f"\n✅ Successfully tested with {ticker}!")
            successful_test = True
            break
            
        except Exception as e:
            print(f"❌ Error testing {ticker}: {str(e)}")
            continue
    
    # If all tickers fail, use sample data
    if not successful_test:
        print("\n📊 All real data failed, creating sample data for testing...")
        try:
            sample_data = analyzer.create_sample_data()
            indicators = analyzer.calculate_all_indicators(sample_data)
            
            print("\n✅ Sample data analysis successful!")
            print("=" * 40)
            print(f"🎯 Technical Score: {indicators.get('technical_score', 0):.1f}/100")
            print(f"📈 Trend: {indicators.get('technical_trend', 'N/A').upper()}")
            print(f"💰 Price: ${indicators.get('current_price', 0):.2f}")
            print(f"📊 RSI: {indicators.get('rsi_14', 0):.1f}")
            print(f"📉 MACD Trend: {indicators.get('macd_trend', 'N/A')}")
            print(f"📊 Volatility: {indicators.get('volatility_20d', 0):.1f}%")
            
        except Exception as e:
            print(f"❌ Even sample data failed: {e}")


# Simple test without Yahoo Finance
def simple_test():
    """Simple test using only sample data"""
    print("🧪 Simple Technical Analyzer Test")
    print("=" * 40)
    
    analyzer = TechnicalAnalyzer()
    
    # Use sample data
    sample_data = analyzer.create_sample_data()
    indicators = analyzer.calculate_all_indicators(sample_data)
    
    print("\n📊 Technical Analysis Results:")
    print("=" * 40)
    
    key_metrics = {
        'Technical Score': f"{indicators.get('technical_score', 0):.1f}/100",
        'Trend': indicators.get('technical_trend', 'N/A').upper(),
        'Current Price': f"${indicators.get('current_price', 0):.2f}",
        'RSI (14)': f"{indicators.get('rsi_14', 0):.1f}",
        'MACD Trend': indicators.get('macd_trend', 'N/A'),
        'Price vs SMA 20': f"{indicators.get('price_vs_sma_20', 0):+.1f}%",
        'Volatility (20d)': f"{indicators.get('volatility_20d', 0):.1f}%",
        'Volume Ratio': f"{indicators.get('volume_ratio', 0):.1f}x"
    }
    
    for metric, value in key_metrics.items():
        print(f"  {metric:<18}: {value}")
    
    # Signal interpretation
    score = indicators.get('technical_score', 50)
    if score > 70:
        print(f"\n🎯 Interpretation: STRONG BULLISH")
    elif score > 60:
        print(f"\n🎯 Interpretation: BULLISH") 
    elif score > 40:
        print(f"\n🎯 Interpretation: NEUTRAL")
    elif score > 30:
        print(f"\n🎯 Interpretation: BEARISH")
    else:
        print(f"\n🎯 Interpretation: STRONG BEARISH")

if __name__ == "__main__":
    # Use simple test to avoid Yahoo Finance issues
    simple_test()