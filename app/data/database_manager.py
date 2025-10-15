import pandas as pd
import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class FinancialDataManager:
    def __init__(self, db_path: str = "financial_data.db"):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for company fundamentals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS company_fundamentals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                metric TEXT NOT NULL,
                year INTEGER NOT NULL,
                value REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, metric, year)
            )
        ''')
        
        # Table for company info
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS company_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                company_name TEXT,
                sector TEXT,
                industry TEXT,
                market_cap REAL,
                country TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for price data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database setup completed")
    
    def store_fundamentals(self, symbol: str, data: Dict):
        """Store company fundamental data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for metric, years_data in data.items():
                for year, value in years_data.items():
                    if value is not None:
                        cursor.execute('''
                            INSERT OR REPLACE INTO company_fundamentals 
                            (symbol, metric, year, value) 
                            VALUES (?, ?, ?, ?)
                        ''', (symbol, metric, int(year), float(value)))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Stored fundamentals for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error storing fundamentals for {symbol}: {e}")
    
    def store_company_info(self, symbol: str, info: Dict):
        """Store company information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO company_info 
                (symbol, company_name, sector, industry, market_cap, country)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                info.get('company_name'),
                info.get('sector'),
                info.get('industry'),
                info.get('market_cap'),
                info.get('country')
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Stored company info for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error storing company info for {symbol}: {e}")
    
    def get_company_data(self, symbol: str, metrics: List[str] = None) -> pd.DataFrame:
        """Retrieve company data from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            if metrics:
                metrics_placeholders = ','.join(['?'] * len(metrics))
                query = f'''
                    SELECT symbol, metric, year, value 
                    FROM company_fundamentals 
                    WHERE symbol = ? AND metric IN ({metrics_placeholders})
                    ORDER BY year DESC
                '''
                params = [symbol] + metrics
            else:
                query = '''
                    SELECT symbol, metric, year, value 
                    FROM company_fundamentals 
                    WHERE symbol = ?
                    ORDER BY metric, year DESC
                '''
                params = [symbol]
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error retrieving data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_all_symbols(self) -> List[str]:
        """Get list of all symbols in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT symbol FROM company_fundamentals")
        symbols = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return symbols