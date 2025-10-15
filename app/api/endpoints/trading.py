from fastapi import APIRouter, HTTPException, Depends
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/test-connection")
async def test_alpaca_connection():
    """
    Test connection to Alpaca API with current .env credentials
    """
    try:
        logger.info("Testing Alpaca connection...")
        
        # Initialize Alpaca client
        trading_client = TradingClient(
            os.getenv('ALPACA_API_KEY'), 
            os.getenv('ALPACA_SECRET_KEY'),
            paper=True
        )
        
        # Get account information
        account = trading_client.get_account()
        
        logger.info(f"Alpaca connection successful - Account: {account.id}")
        
        return {
            "status": "success",
            "message": "Alpaca connection successful",
            "account": {
                "id": account.id,
                "account_number": account.account_number,
                "status": account.status,
                "currency": account.currency,
                "buying_power": float(account.buying_power),
                "regt_buying_power": float(account.regt_buying_power),
                "daytrading_buying_power": float(account.daytrading_buying_power),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "transfers_blocked": account.transfers_blocked,
                "account_blocked": account.account_blocked,
                "created_at": account.created_at.isoformat() if account.created_at else None,
                "trade_suspended_by_user": account.trade_suspended_by_user,
                "multiplier": account.multiplier
            }
        }
        
    except Exception as e:
        logger.error(f"Alpaca connection failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Alpaca connection failed: {str(e)}"
        }

@router.get("/account-info")
async def get_account_info():
    """
    Get detailed Alpaca account information
    """
    try:
        trading_client = TradingClient(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            paper=True
        )
        
        account = trading_client.get_account()
        
        return {
            "status": "success",
            "account": {
                "id": account.id,
                "buying_power": f"${float(account.buying_power):,.2f}",
                "portfolio_value": f"${float(account.portfolio_value):,.2f}",
                "cash": f"${float(account.cash):,.2f}",
                "status": account.status,
                "currency": account.currency
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get account info: {str(e)}")

@router.get("/positions")
async def get_positions():
    """Get current positions in Alpaca account"""
    try:
        trading_client = TradingClient(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            paper=True
        )
        
        positions = trading_client.get_all_positions()
        
        # Если позиций нет - вернуть пустой массив
        if not positions:
            return {
                "status": "success", 
                "positions": [],
                "count": 0,
                "message": "No positions found"
            }
        
        positions_data = []
        for position in positions:
            positions_data.append({
                "symbol": position.symbol,
                "qty": float(position.qty),
                "market_value": float(position.market_value),
                "unrealized_pl": float(position.unrealized_pl),
                "current_price": float(position.current_price),
                "avg_entry_price": float(position.avg_entry_price)
            })
        
        return {
            "status": "success",
            "positions": positions_data,
            "count": len(positions_data)
        }
        
    except Exception as e:
        logger.error(f"Failed to get positions: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get positions: {str(e)}",
            "positions": []
        }

@router.get("/orders")
async def get_orders():
    """Get all orders from Alpaca account"""
    try:
        trading_client = TradingClient(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            paper=True
        )
        
        orders = trading_client.get_orders()
        
        orders_data = []
        for order in orders:
            orders_data.append({
                "id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "side": order.side,
                "type": order.order_type,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None
            })
        
        return {
            "status": "success",
            "orders": orders_data,
            "count": len(orders_data)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get orders: {str(e)}",
            "orders": []
        }

@router.post("/execute-portfolio")
async def execute_portfolio(portfolio_data: dict):
    """
    Execute portfolio orders in Alpaca
    """
    try:
        trading_client = TradingClient(
            os.getenv('ALPACA_API_KEY'), 
            os.getenv('ALPACA_SECRET_KEY'),
            paper=True
        )
        
        # Get current prices for quantity calculation
        data_client = StockHistoricalDataClient(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY')
        )
        
        orders = []
        total_investment = portfolio_data.get('investment_amount', 1000)
        
        for asset in portfolio_data['assets']:
            symbol = asset['ticker']
            weight = asset['weight'] / 100  # Convert percentage to decimal
            amount = total_investment * weight
            
            # Get current price
            try:
                request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol)
                latest_quote = data_client.get_stock_latest_quote(request_params)
                current_price = float(latest_quote[symbol].ask_price)
                
                # Calculate quantity (round down)
                qty = int(amount / current_price)
                
                if qty > 0:
                    market_order_data = MarketOrderRequest(
                        symbol=symbol,
                        qty=qty,
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.DAY
                    )
                    
                    order = trading_client.submit_order(market_order_data)
                    orders.append({
                        'ticker': symbol,
                        'quantity': qty,
                        'price': current_price,
                        'amount': amount,
                        'order_id': order.id,
                        'status': order.status
                    })
                    logger.info(f"Order submitted: {symbol} {qty} shares")
                else:
                    logger.warning(f"Quantity too small for {symbol}: {qty}")
                    orders.append({
                        'ticker': symbol,
                        'error': f'Quantity too small: {qty} shares',
                        'status': 'skipped'
                    })
                    
            except Exception as e:
                logger.error(f"Failed to process {symbol}: {str(e)}")
                orders.append({
                    'ticker': symbol,
                    'error': str(e),
                    'status': 'failed'
                })
        
        successful_orders = [o for o in orders if 'order_id' in o]
        
        return {
            "status": "success", 
            "message": f"Submitted {len(successful_orders)} orders successfully",
            "orders": orders,
            "total_investment": total_investment,
            "successful_count": len(successful_orders),
            "failed_count": len(orders) - len(successful_orders)
        }
        
    except Exception as e:
        logger.error(f"Portfolio execution failed: {str(e)}")
        return {
            "status": "error", 
            "message": f"Portfolio execution failed: {str(e)}",
            "orders": []
        }

@router.post("/execute-single-order")
async def execute_single_order(order_data: dict):
    """
    Execute single stock order
    """
    try:
        trading_client = TradingClient(
            os.getenv('ALPACA_API_KEY'), 
            os.getenv('ALPACA_SECRET_KEY'),
            paper=True
        )
        
        symbol = order_data.get('symbol')
        quantity = order_data.get('quantity')
        side = order_data.get('side', 'buy')
        
        if not symbol or not quantity:
            raise HTTPException(
                status_code=400, 
                detail="Symbol and quantity are required"
            )
        
        market_order_data = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL,
            time_in_force=TimeInForce.DAY
        )
        
        order = trading_client.submit_order(market_order_data)
        
        return {
            "status": "success",
            "message": f"Order submitted successfully",
            "order": {
                "id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side,
                "type": order.order_type,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None
            }
        }
        
    except Exception as e:
        logger.error(f"Single order execution failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Order execution failed: {str(e)}"
        )

@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    """
    Cancel specific order
    """
    try:
        trading_client = TradingClient(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            paper=True
        )
        
        trading_client.cancel_order_by_id(order_id)
        
        return {
            "status": "success",
            "message": f"Order {order_id} cancelled successfully"
        }
        
    except Exception as e:
        logger.error(f"Order cancellation failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Order cancellation failed: {str(e)}"
        )

@router.get("/market-status")
async def get_market_status():
    """
    Get current market status (open/closed)
    """
    try:
        trading_client = TradingClient(
            os.getenv('ALPACA_API_KEY'),
            os.getenv('ALPACA_SECRET_KEY'),
            paper=True
        )
        
        clock = trading_client.get_clock()
        
        return {
            "status": "success",
            "market": {
                "is_open": clock.is_open,
                "next_open": clock.next_open.isoformat() if clock.next_open else None,
                "next_close": clock.next_close.isoformat() if clock.next_close else None,
                "timestamp": clock.timestamp.isoformat() if clock.timestamp else None
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get market status: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to get market status: {str(e)}"
        }