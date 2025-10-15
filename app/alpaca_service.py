import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.common.exceptions import APIError

load_dotenv()

class AlpacaService:
    """Modern Alpaca service using official alpaca-py SDK"""
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY', 'PKTXKEARM25NUVJMYAFX')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY', 'HPnBM0ik0CahERzdrHnL7URyctlkoR7fdab5XHby')
        self.trading_client = None
        self.connected = False
        self._connect()
    
    def _connect(self) -> bool:
        """Connect to Alpaca trading API"""
        try:
            self.trading_client = TradingClient(
                self.api_key,
                self.secret_key,
                paper=True  # Use paper trading
            )
            
            # Test connection by getting account info
            account = self.trading_client.get_account()
            print(f"✅ Alpaca-py connected! Account status: {account.status}")
            print(f"💰 Buying power: ${account.buying_power}")
            print(f"📊 Portfolio value: ${account.portfolio_value}")
            self.connected = True
            return True
            
        except Exception as e:
            print(f"❌ Alpaca connection failed: {e}")
            self.connected = False
            return False
    
    def get_account_info(self) -> Dict:
        """Get Alpaca account information"""
        try:
            if not self.trading_client:
                self._connect()
            
            account = self.trading_client.get_account()
            
            # Исправленная структура для новой версии SDK
            account_info = {
                'status': account.status.value if hasattr(account.status, 'value') else str(account.status),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'cash': float(account.cash),
                'currency': account.currency,
                'account_number': account.account_number,
            }
            
            # Добавляем опциональные поля если они существуют
            if hasattr(account, 'daytrade_count'):
                account_info['day_trade_count'] = account.daytrade_count
            if hasattr(account, 'regt_buying_power'):
                account_info['regt_buying_power'] = float(account.regt_buying_power)
            if hasattr(account, 'non_marginable_buying_power'):
                account_info['non_marginable_buying_power'] = float(account.non_marginable_buying_power)
                
            return account_info
            
        except Exception as e:
            return {'error': f'Failed to get account info: {str(e)}'}
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            # Используем данные из нашего portfolio_service
            from .portfolio_service import portfolio_service
            
            symbol_upper = symbol.upper()
            
            # Проверяем ETF
            if symbol_upper in portfolio_service.ASSETS['etf']:
                return portfolio_service.ASSETS['etf'][symbol_upper].get('current_price', 0)
            
            # Проверяем акции
            if symbol_upper in portfolio_service.ASSETS['stocks']:
                return portfolio_service.ASSETS['stocks'][symbol_upper].get('current_price', 0)
            
            print(f"⚠️  Price not found for {symbol}, using default $100")
            return 100.0  # Default price
            
        except Exception as e:
            print(f"❌ Price error for {symbol}: {e}")
            return 100.0  # Fallback price
    
    def execute_portfolio(self, portfolio: List[Dict], total_amount: float = 10000) -> Dict:
        """Execute portfolio by placing market orders for each instrument"""
        try:
            if not self.connected or not self.trading_client:
                if not self._connect():
                    return {'success': False, 'message': 'Failed to connect to Alpaca'}
            
            orders = []
            successful_orders = 0
            total_portfolio_weight = sum(item.get('weight', 0) for item in portfolio)
            
            # Validate portfolio weights
            if total_portfolio_weight <= 0:
                return {'success': False, 'message': 'Invalid portfolio weights'}
            
            print(f"🔄 Executing portfolio with ${total_amount:,} total amount")
            print(f"📊 Processing {len(portfolio)} instruments")
            
            for instrument in portfolio:
                ticker = instrument.get('ticker', '').upper()
                weight = instrument.get('weight', 0)
                
                if not ticker or weight <= 0:
                    continue
                
                # Calculate amount to invest in this instrument
                amount_to_invest = (weight / total_portfolio_weight) * total_amount
                
                try:
                    # Get current market price
                    current_price = self.get_current_price(ticker)
                    if not current_price or current_price <= 0:
                        print(f"❌ Could not get valid price for {ticker}")
                        orders.append({
                            'ticker': ticker,
                            'error': 'Could not get current price',
                            'status': 'failed'
                        })
                        continue
                    
                    # Calculate quantity (whole shares for simplicity)
                    quantity = int(amount_to_invest / current_price)
                    
                    if quantity == 0:
                        print(f"⚠️  Amount too small for {ticker}: ${amount_to_invest:.2f}")
                        orders.append({
                            'ticker': ticker,
                            'error': f'Amount too small: ${amount_to_invest:.2f}',
                            'status': 'skipped'
                        })
                        continue
                    
                    print(f"📈 Ordering {ticker}: {quantity} shares @ ${current_price:.2f} = ${quantity * current_price:.2f}")
                    
                    # Create market order
                    market_order_data = MarketOrderRequest(
                        symbol=ticker,
                        qty=quantity,
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.DAY
                    )
                    
                    # Submit order
                    order = self.trading_client.submit_order(market_order_data)
                    
                    order_info = {
                        'ticker': ticker,
                        'quantity': quantity,
                        'calculated_price': round(current_price, 2),
                        'amount_invested': round(quantity * current_price, 2),
                        'order_id': order.id,
                        'status': order.status.value if hasattr(order.status, 'value') else str(order.status),
                        'weight_percent': weight
                    }
                    
                    orders.append(order_info)
                    successful_orders += 1
                    
                    print(f"✅ Order placed: {ticker} x {quantity} @ ${current_price:.2f} (${quantity * current_price:.2f})")
                    
                except APIError as e:
                    error_msg = f"Alpaca API error for {ticker}: {str(e)}"
                    print(f"❌ {error_msg}")
                    orders.append({
                        'ticker': ticker,
                        'error': error_msg,
                        'status': 'failed'
                    })
                except Exception as e:
                    error_msg = f"Failed to order {ticker}: {str(e)}"
                    print(f"❌ {error_msg}")
                    orders.append({
                        'ticker': ticker,
                        'error': error_msg,
                        'status': 'failed'
                    })
            
            return {
                'success': successful_orders > 0,
                'message': f'Successfully placed {successful_orders} out of {len(portfolio)} orders',
                'total_orders_attempted': len(portfolio),
                'successful_orders': successful_orders,
                'orders': orders,
                'total_invested': sum(order.get('amount_invested', 0) for order in orders if order.get('amount_invested'))
            }
            
        except Exception as e:
            error_msg = f'Alpaca execution error: {str(e)}'
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'message': error_msg,
                'orders': []
            }
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Check status of a specific order"""
        try:
            order = self.trading_client.get_order_by_id(order_id)
            
            return {
                'order_id': order.id,
                'symbol': order.symbol,
                'quantity': float(order.qty),
                'filled_quantity': float(order.filled_qty) if order.filled_qty else 0,
                'status': order.status.value if hasattr(order.status, 'value') else str(order.status),
                'side': order.side.value if hasattr(order.side, 'value') else str(order.side),
                'type': order.order_type.value if hasattr(order.order_type, 'value') else str(order.order_type),
                'submitted_at': order.submitted_at.isoformat() if order.submitted_at else None
            }
        except Exception as e:
            print(f"❌ Order status error: {e}")
            return None

# Create global service instance
alpaca_service = AlpacaService()