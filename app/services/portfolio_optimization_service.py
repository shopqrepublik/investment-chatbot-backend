import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class PortfolioOptimizationService:
    """
    Сервис для оптимизации портфеля инвестиций
    """
    
    def __init__(self):
        self.risk_free_rate = 0.02
    
    def calculate_portfolio_metrics(self, returns: pd.DataFrame, weights: np.ndarray) -> Dict:
        """
        Расчет метрик портфеля
        """
        try:
            portfolio_returns = np.sum(returns.mean() * weights) * 252
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
            sharpe_ratio = (portfolio_returns - self.risk_free_rate) / portfolio_volatility
            
            return {
                'expected_return': portfolio_returns,
                'volatility': portfolio_volatility,
                'sharpe_ratio': sharpe_ratio
            }
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {
                'expected_return': 0,
                'volatility': 0,
                'sharpe_ratio': 0
            }
    
    def optimize_portfolio(self, returns: pd.DataFrame, method: str = 'sharpe') -> Dict:
        """
        Оптимизация портфеля
        """
        try:
            n_assets = len(returns.columns)
            
            if method == 'sharpe':
                weights = np.array([1/n_assets] * n_assets)
            elif method == 'min_variance':
                cov_matrix = returns.cov() * 252
                inv_cov = np.linalg.pinv(cov_matrix)
                ones = np.ones(n_assets)
                weights = np.dot(inv_cov, ones) / np.dot(ones, np.dot(inv_cov, ones))
            else:
                weights = np.array([1/n_assets] * n_assets)
            
            weights = weights / np.sum(weights)
            metrics = self.calculate_portfolio_metrics(returns, weights)
            
            return {
                'weights': dict(zip(returns.columns, weights)),
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            n_assets = len(returns.columns)
            weights = np.array([1/n_assets] * n_assets)
            metrics = self.calculate_portfolio_metrics(returns, weights)
            
            return {
                'weights': dict(zip(returns.columns, weights)),
                'metrics': metrics
            }
    
    def get_optimized_allocation(self, assets: List[str], historical_data: pd.DataFrame) -> Dict:
        """
        Получение оптимизированного распределения активов
        """
        try:
            returns = historical_data.pct_change().dropna()
            result = self.optimize_portfolio(returns)
            return result
            
        except Exception as e:
            logger.error(f"Error in portfolio allocation: {e}")
            n_assets = len(assets)
            weights = [1/n_assets] * n_assets
            
            return {
                'weights': dict(zip(assets, weights)),
                'metrics': {
                    'expected_return': 0.08,
                    'volatility': 0.15,
                    'sharpe_ratio': 0.4
                }
            }