import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import random

class TickerLists:
    def __init__(self):
        self.tech_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'AVGO', 
            'COST', 'ADBE', 'CRM', 'NFLX', 'AMD', 'INTC', 'CSCO', 'QCOM', 
            'TXN', 'AMAT', 'MU', 'ORCL', 'IBM', 'NOW', 'SNPS', 'ADP', 'INTU',
            'UBER', 'LYFT', 'SHOP', 'SQ', 'PYPL', 'ZM', 'DOCU', 'CRWD', 'OKTA',
            'NET', 'DDOG', 'MDB', 'TWLO', 'FSLY', 'PLTR', 'SNOW', 'DASH',
            'ABNB', 'RBLX', 'SPOT', 'PINS', 'SNAP', 'TTD', 'TTWO', 'EA'
        ]
        
        self.etf_list = [
            'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO', 'VUG', 'VOOG',
            'BND', 'AGG', 'LQD', 'HYG', 'TIP', 'GLD', 'SLV', 'USO', 'VNQ',
            'XLF', 'XLK', 'XLV', 'XLE', 'XLI', 'XLP', 'XLY', 'XLU', 'XLB',
            'IWF', 'IWD', 'IWB', 'IVV', 'IJR', 'IVE', 'IJH', 'IWR', 'IWS'
        ]

    def get_sp500_tickers(self, count=50):
        """Получает список акций S&P 500 (альтернативные методы)"""
        try:
            # Метод 1: Используем Wikipedia с другим URL
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', {'id': 'constituents'})
            
            tickers = []
            for row in table.find_all('tr')[1:]:  # Пропускаем заголовок
                cells = row.find_all('td')
                if len(cells) > 0:
                    ticker = cells[0].text.strip()
                    if ticker:
                        tickers.append(ticker)
            
            print(f"✅ Получено {len(tickers)} тикеров S&P 500 из Wikipedia")
            return tickers[:count]
            
        except Exception as e:
            print(f"❌ Ошибка получения S&P 500: {e}")
            # Возвращаем запасной список крупных компаний
            fallback_sp500 = [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 
                'JNJ', 'V', 'PG', 'UNH', 'HD', 'DIS', 'PYPL', 'NFLX', 'ADBE',
                'CRM', 'INTC', 'CSCO', 'PEP', 'T', 'ABT', 'TMO', 'COST', 'AVGO',
                'LLY', 'WMT', 'XOM', 'CVX', 'MRK', 'PFE', 'ABBV', 'KO', 'BAC',
                'WFC', 'C', 'GS', 'MS', 'AMGN', 'TXN', 'HON', 'IBM', 'ORCL',
                'QCOM', 'AMD', 'SBUX', 'MDT', 'UNP', 'LOW'
            ]
            print("✅ Используем резервный список S&P 500")
            return fallback_sp500[:count]

    def get_nasdaq_tickers(self, count=50):
        """Получает технологические акции Nasdaq"""
        try:
            # Для Nasdaq используем наш предопределенный список технологических компаний
            print(f"✅ Используем {count} технологических тикеров Nasdaq")
            return self.tech_tickers[:count]
        except Exception as e:
            print(f"❌ Ошибка получения Nasdaq: {e}")
            return self.tech_tickers[:count]

    def get_etf_list(self):
        """Возвращает список популярных ETF"""
        try:
            print(f"✅ Используем список из {len(self.etf_list)} ETF")
            return self.etf_list
        except Exception as e:
            print(f"❌ Ошибка получения ETF: {e}")
            return self.etf_list

    def categorize_ticker(self, ticker):
        """Категоризирует тикер по типу и сектору"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Определяем тип актива
            if ticker in self.etf_list:
                asset_type = 'etf'
            else:
                asset_type = 'stock'
            
            # Определяем сектор
            sector = info.get('sector', 'Unknown')
            if not sector or sector == 'Unknown':
                # Для ETF определяем по названию
                long_name = info.get('longName', '').lower()
                if any(word in long_name for word in ['technology', 'tech']):
                    sector = 'technology'
                elif any(word in long_name for word in ['bond', 'fixed income']):
                    sector = 'bonds'
                elif any(word in long_name for word in ['gold', 'precious']):
                    sector = 'commodities'
                elif any(word in long_name for word in ['real estate', 'reit']):
                    sector = 'real_estate'
                else:
                    sector = 'broad_market'
            
            # Определяем риск на основе бета-коэффициента
            beta = info.get('beta', 1.0)
            if beta < 0.8:
                risk = 'low'
            elif beta < 1.2:
                risk = 'medium'
            else:
                risk = 'high'
            
            return {
                'type': asset_type,
                'sector': sector,
                'risk': risk,
                'name': info.get('longName', ticker)
            }
            
        except Exception as e:
            print(f"❌ Ошибка категоризации {ticker}: {e}")
            # Возвращаем значения по умолчанию
            return {
                'type': 'stock',
                'sector': 'unknown',
                'risk': 'medium',
                'name': ticker
            }

    def get_ticker_metadata(self, ticker):
        """Получает метаданные для тикера (совместимость со старым кодом)"""
        return self.categorize_ticker(ticker)

# Создаем экземпляр класса
ticker_lists = TickerLists()