import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session
import time
from .database import Price
from .ticker_lists import ticker_lists  # Import new module

class DataCollector:
    """Class for collecting stock and ETF price data"""
    
    def __init__(self):
        # Use dynamic lists instead of hardcoding
        self.tickers = {
            'etf': ticker_lists.get_etf_list(),
            'stocks_sp500': ticker_lists.get_sp500_tickers()[:50],  # Take top 50 from S&P 500
            'stocks_nasdaq': ticker_lists.get_nasdaq_tickers(50)    # Take top 50 from Nasdaq
        }
    
    def get_all_tickers(self, profile: dict = None) -> list:
        """Gets list of tickers based on user profile"""
        if profile is None:
            # All tickers by default
            all_tickers = (self.tickers['etf'] + 
                          self.tickers['stocks_sp500'] + 
                          self.tickers['stocks_nasdaq'])
            return list(set(all_tickers))  # Remove duplicates
        
        # Filter by user preferences
        markets = profile.get('preferred_markets', 'sp500')
        risk = profile.get('risk_tolerance', 'medium')
        
        selected_tickers = []
        
        # Add ETFs
        selected_tickers.extend(self.tickers['etf'][:10])  # Top 10 ETFs
        
        # Add stocks by markets
        if markets == 'sp500':
            selected_tickers.extend(self.tickers['stocks_sp500'][:30])
        elif markets == 'nasdaq':
            selected_tickers.extend(self.tickers['stocks_nasdaq'][:30])
        elif markets == 'microcap':
            # For microcap take more risky stocks
            selected_tickers.extend(self.tickers['stocks_nasdaq'][20:40])
        
        return list(set(selected_tickers))
    
    def download_ticker_data(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """Downloads data for ticker"""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period=period)
            return data
        except Exception as e:
            print(f"Error loading data for {ticker}: {e}")
            return pd.DataFrame()
    
    def save_price_data(self, db: Session, ticker: str, data: pd.DataFrame):
        """Saves price data to database"""
        try:
            for index, row in data.iterrows():
                # Check if record already exists
                existing = db.query(Price).filter(
                    Price.ticker == ticker,
                    Price.date == index.date()
                ).first()
                
                if not existing:
                    price_record = Price(
                        ticker=ticker,
                        date=index.date(),
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        adj_close=float(row['Close']),  # For simplicity use Close
                        volume=int(row['Volume']) if pd.notna(row['Volume']) else 0
                    )
                    db.add(price_record)
            
            db.commit()
            print(f"✅ Data for {ticker} saved")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error saving data for {ticker}: {e}")
    
    def update_all_data(self, db: Session, profile: dict = None):
        """Updates data for all tickers"""
        all_tickers = self.get_all_tickers(profile)
        
        print(f"📥 Starting data download for {len(all_tickers)} tickers")
        
        for i, ticker in enumerate(all_tickers, 1):
            print(f"📥 Downloading data for {ticker} ({i}/{len(all_tickers)})")
            
            data = self.download_ticker_data(ticker)
            if not data.empty:
                self.save_price_data(db, ticker, data)
            else:
                print(f"⚠️ No data for {ticker}")
            
            # Pause to avoid being blocked
            time.sleep(0.3)
    
    def get_current_price(self, ticker: str) -> float:
        """Gets current price of ticker"""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="1d")
            if not data.empty:
                return float(data['Close'].iloc[-1])
            return 0.0
        except Exception as e:
            print(f"Error getting price for {ticker}: {e}")
            return 0.0
    
    def calculate_returns(self, ticker: str, days: int = 30) -> float:
        """Calculates returns for specified period"""
        try:
            # Add +10 days for reliable data retrieval
            period_days = days + 10
            stock = yf.Ticker(ticker)
            data = stock.history(period=f"{period_days}d")
            
            if len(data) < 2:
                return 0.0
            
            start_price = data['Close'].iloc[0]
            end_price = data['Close'].iloc[-1]
            
            return (end_price - start_price) / start_price * 100
            
        except Exception as e:
            print(f"Error calculating returns for {ticker}: {e}")
            return 0.0
    
    def get_ticker_metadata(self, ticker: str) -> dict:
        """Gets ticker metadata"""
        return ticker_lists.categorize_ticker(ticker)

# Create collector instance
data_collector = DataCollector()

