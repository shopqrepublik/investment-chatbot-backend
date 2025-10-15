import requests
import pandas as pd
import json
import time
from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class QuickFSClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('QUICKFS_API_KEY', 'c6fc36020c3d904fde9589b44a1d614497969f77')
        self.base_url = "https://public-api.quickfs.net/v1"
        self.headers = {
            "X-QFS-API-Key": self.api_key
        }
        
    def get_company_data(self, symbol: str, metrics: List[str], period: str = "FY-10:FY") -> Dict:
        """
        Get company financial data
        
        Args:
            symbol: Stock ticker symbol
            metrics: List of metrics to retrieve
            period: Period range (e.g., "FY-10:FY" for last 10 years)
        """
        try:
            url = f"{self.base_url}/data"
            params = {
                "symbol": symbol,
                "metrics": ",".join(metrics),
                "period": period
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"✅ Retrieved data for {symbol}: {len(data.get('data', []))} periods")
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching data for {symbol}: {e}")
            return None
    
    def get_available_metrics(self) -> List[str]:
        """Get list of all available metrics"""
        try:
            url = f"{self.base_url}/metrics"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            metrics = response.json()
            logger.info(f"✅ Available metrics: {len(metrics)}")
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error fetching metrics: {e}")
            return []
    
    def get_sp500_tickers(self) -> List[str]:
        """Get S&P 500 tickers list"""
        # You can get this from various sources, here's a static list
        # In production, you might want to fetch this dynamically
        sp500_tickers = [
            "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "TSLA", "BRK.B", "UNH", "JNJ", "XOM",
            "JPM", "V", "PG", "NVDA", "HD", "CVX", "MA", "BAC", "ABBV", "PFE",
            "AVGO", "LLY", "KO", "WMT", "DIS", "NFLX", "ADBE", "CRM", "CSCO", "PEP",
            # Add more S&P 500 tickers...
        ]
        return sp500_tickers
    
    def get_nasdaq_tickers(self) -> List[str]:
        """Get NASDAQ 100 tickers list"""
        nasdaq_tickers = [
            "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "TSLA", "META", "NVDA", "AVGO", "PEP",
            "COST", "ADBE", "CSCO", "TMUS", "CMCSA", "NFLX", "HON", "TXN", "QCOM", "INTU",
            "AMGN", "INTC", "AMD", "SBUX", "GILD", "MDLZ", "ADP", "ISRG", "REGN", "VRTX",
            # Add more NASDAQ tickers...
        ]
        return nasdaq_tickers

    def get_all_tickers(self) -> List[str]:
        """Combine S&P 500 and NASDAQ tickers"""
        sp500 = self.get_sp500_tickers()
        nasdaq = self.get_nasdaq_tickers()
        all_tickers = list(set(sp500 + nasdaq))
        logger.info(f"📊 Total unique tickers: {len(all_tickers)}")
        return all_tickers