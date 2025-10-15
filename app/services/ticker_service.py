# D:\investment-chatbot\app\services\ticker_service.py
import pandas as pd
import requests
import yfinance as yf
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class TickerService:
    def __init__(self):
        self.sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        self.nasdaq_url = "https://en.wikipedia.org/wiki/NASDAQ-100"
    
    def get_sp500_tickers(self) -> List[str]:
        """Get current S&P500 tickers from Wikipedia"""
        try:
            logger.info("Fetching S&P500 tickers...")
            tables = pd.read_html(self.sp500_url)
            sp500_table = tables[0]
            tickers = sp500_table['Symbol'].tolist()
            logger.info(f"Found {len(tickers)} S&P500 tickers")
            return tickers
        except Exception as e:
            logger.error(f"Failed to fetch S&P500 tickers: {e}")
            # Fallback to major S&P500 stocks
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'JNJ', 'V', 
                   'PG', 'DIS', 'NFLX', 'AMD', 'INTC', 'CSCO', 'PEP', 'ADBE', 'CRM', 'T']
    
    def get_nasdaq_tickers(self) -> List[str]:
        """Get Nasdaq-100 tickers from Wikipedia"""
        try:
            logger.info("Fetching Nasdaq-100 tickers...")
            tables = pd.read_html(self.nasdaq_url)
            # Try different table indices
            for i, table in enumerate(tables):
                if 'Ticker' in table.columns:
                    nasdaq_table = table
                    break
            else:
                nasdaq_table = tables[3]  # Fallback to typical index
            
            tickers = nasdaq_table['Ticker'].tolist()
            logger.info(f"Found {len(tickers)} Nasdaq tickers")
            return tickers
        except Exception as e:
            logger.error(f"Failed to fetch Nasdaq tickers: {e}")
            # Fallback to major Nasdaq stocks
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD', 'INTC', 'ADBE',
                   'CSCO', 'CMCSA', 'COST', 'AVGO', 'TXN', 'CHTR', 'SBUX', 'TMUS', 'MRNA', 'GILD']
    
    def get_stock_info(self, ticker: str) -> Dict:
        """Get basic stock information"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                'ticker': ticker,
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'current_price': info.get('currentPrice', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get info for {ticker}: {e}")
            return {'ticker': ticker, 'error': str(e)}