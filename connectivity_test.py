# connectivity_test.py - разместите этот файл в D:\investment-chatbot\
import yfinance as yf
import pandas as pd

print("🔍 Testing yfinance connectivity...")

# Test basic download
test_tickers = ['MSFT', 'GOOGL', 'SPY', 'QQQ', 'TSLA', 'AAPL']

for ticker in test_tickers:
    try:
        print(f"\n📊 Testing {ticker}...")
        data = yf.download(ticker, period="1mo", progress=False)
        
        if not data.empty:
            print(f"✅ {ticker}: {len(data)} rows, Close: ${data['Close'].iloc[-1]:.2f}")
        else:
            print(f"❌ {ticker}: No data")
            
    except Exception as e:
        print(f"❌ {ticker}: Error - {e}")

print("\n🎯 Testing different periods...")
try:
    data_1wk = yf.download("MSFT", period="1wk", progress=False)
    data_1mo = yf.download("MSFT", period="1mo", progress=False) 
    data_6mo = yf.download("MSFT", period="6mo", progress=False)
    
    print(f"✅ 1 week: {len(data_1wk)} rows")
    print(f"✅ 1 month: {len(data_1mo)} rows")
    print(f"✅ 6 months: {len(data_6mo)} rows")
    
except Exception as e:
    print(f"❌ Period test failed: {e}")

print("\n🔧 Testing Ticker object...")
try:
    msft = yf.Ticker("MSFT")
    info = msft.info
    print(f"✅ MSFT info: {info.get('longName', 'Unknown')}")
    print(f"💰 Current price: {info.get('currentPrice', 'N/A')}")
    print(f"📈 Market cap: {info.get('marketCap', 'N/A')}")
except Exception as e:
    print(f"❌ Ticker object failed: {e}")