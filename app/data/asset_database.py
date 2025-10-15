# app/data/asset_database.py
import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session
from app.models.asset_models import Asset

class AssetDatabase:
    def __init__(self, db: Session):
        self.db = db
    
    def update_asset_database(self):
        """Update asset database with current market data"""
        # S&P 500 tickers (example - in production use comprehensive list)
        sp500_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
            'JPM', 'V', 'PG', 'XOM', 'HD', 'CVX', 'MA', 'BAC', 'ABBV', 'PFE',
            'AVGO', 'LLY', 'KO', 'WMT', 'TMO', 'DIS', 'PEP', 'NFLX', 'CSCO', 'ABT'
        ]
        
        # Nasdaq tickers (example)
        nasdaq_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'PYPL', 'ADBE', 'NFLX',
            'CMCSA', 'INTC', 'CSCO', 'PEP', 'AVGO', 'TXN', 'QCOM', 'COST', 'TMUS', 'AMGN'
        ]
        
        # Popular ETFs
        etf_tickers = [
            'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'IVV', 'DIA', 'XLK', 'XLF', 'XLV',
            'XLE', 'XLY', 'XLP', 'XLI', 'XLB', 'XLU', 'XLRE', 'VOOG', 'VOOV', 'VUG'
        ]
        
        all_tickers = list(set(sp500_tickers + nasdaq_tickers + etf_tickers))
        
        for ticker in all_tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                asset = Asset(
                    ticker=ticker,
                    name=info.get('longName', ticker),
                    asset_type='ETF' if 'ETF' in info.get('longName', '') else 'Stock',
                    sector=info.get('sector', 'Unknown'),
                    industry=info.get('industry', 'Unknown'),
                    market_cap=info.get('marketCap', 0) / 1e9,  # Convert to billions
                    exchange=info.get('exchange', 'Unknown')
                )
                
                # Add or update in database
                self.db.merge(asset)
                
            except Exception as e:
                print(f"Failed to update {ticker}: {e}")
        
        self.db.commit()