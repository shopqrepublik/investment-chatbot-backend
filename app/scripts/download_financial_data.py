import sys
import os
from pathlib import Path
import time
from tqdm import tqdm
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.data.quickfs_client import QuickFSClient
from app.data.database_manager import FinancialDataManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_download.log')
    ]
)
logger = logging.getLogger(__name__)

class FinancialDataDownloader:
    def __init__(self):
        self.client = QuickFSClient()
        self.db_manager = FinancialDataManager()
        self.metrics = [
            "revenue", "gross_profit", "operating_income", "net_income",
            "eps_basic", "eps_diluted", "ebitda", "free_cash_flow",
            "total_assets", "total_liabilities", "total_equity",
            "cash_and_equivalents", "long_term_debt", "short_term_debt",
            "operating_cash_flow", "investing_cash_flow", "financing_cash_flow",
            "price_to_earnings", "price_to_sales", "price_to_book",
            "debt_to_equity", "return_on_equity", "return_on_assets",
            "gross_margin", "operating_margin", "net_margin"
        ]
    
    def download_all_data(self, batch_size: int = 10, delay: float = 1.0):
        """Download data for all tickers with rate limiting"""
        tickers = self.client.get_all_tickers()
        logger.info(f"🚀 Starting download for {len(tickers)} tickers")
        
        successful_downloads = 0
        failed_downloads = []
        
        for i in tqdm(range(0, len(tickers), batch_size), desc="Downloading batches"):
            batch = tickers[i:i + batch_size]
            
            for symbol in batch:
                try:
                    logger.info(f"📥 Downloading data for {symbol}")
                    
                    # Get financial data
                    data = self.client.get_company_data(symbol, self.metrics, "FY-10:FY")
                    
                    if data and 'data' in data:
                        # Transform data for storage
                        fundamentals = self._transform_fundamentals_data(data['data'])
                        self.db_manager.store_fundamentals(symbol, fundamentals)
                        successful_downloads += 1
                    
                    # Respect rate limits
                    time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to download {symbol}: {e}")
                    failed_downloads.append(symbol)
                    continue
            
            logger.info(f"✅ Completed batch {i//batch_size + 1}")
        
        logger.info(f"🎉 Download completed! Successful: {successful_downloads}, Failed: {len(failed_downloads)}")
        if failed_downloads:
            logger.info(f"❌ Failed tickers: {failed_downloads}")
    
    def _transform_fundamentals_data(self, raw_data: Dict) -> Dict:
        """Transform API response to database format"""
        fundamentals = {}
        
        for metric_data in raw_data:
            metric_name = metric_data.get('metric')
            values = metric_data.get('values', {})
            
            fundamentals[metric_name] = values
        
        return fundamentals

def main():
    downloader = FinancialDataDownloader()
    
    print("🚀 Starting financial data download...")
    print("📊 This may take a while due to API rate limits...")
    
    # Download all data
    downloader.download_all_data(batch_size=5, delay=1.5)
    
    print("✅ Download completed!")
    print("💾 Data stored in financial_data.db")

if __name__ == "__main__":
    main()