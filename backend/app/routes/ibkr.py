from fastapi import APIRouter, HTTPException, Body
from ..services.ibkr_connection import (
    connect_to_ibkr,
    get_alpha_vantage_price,
    get_finnhub_price,
    ALPHA_VANTAGE_API_KEY,
)
import logging
import time
import json
import os
from typing import Optional, Dict, Any, List
from ..services.price_cache import CACHE_FILE, price_cache
from datetime import datetime
from pydantic import BaseModel


# Define the OrderReasonData model
class OrderReasonData(BaseModel):
    buyReason: Optional[str] = None
    catalysts: Optional[str] = None
    sector: Optional[str] = None
    timeframe: Optional[str] = None
    strategy: Optional[str] = None
    marketTrend: Optional[str] = None
    marketSentiment: Optional[str] = None
    entryBasis: Optional[str] = None
    stopLoss: Optional[str] = None
    riskRewardRatio: Optional[str] = None
    onWatchlist: Optional[bool] = None
    positionSizing: Optional[str] = None
    positionSize: Optional[str] = None
    maxDrawdown: Optional[str] = None
    riskAcceptable: Optional[bool] = None
    checkFomo: Optional[bool] = None
    checkLossFear: Optional[bool] = None
    checkPriceBottom: Optional[bool] = None
    checkProveRight: Optional[bool] = None
    checkFollowingStrategy: Optional[bool] = None
    checkEmotionalTrading: Optional[bool] = None
    checkOvertrading: Optional[bool] = None
    checkStopLossSet: Optional[bool] = None
    checkMentalState: Optional[bool] = None
    checkAcceptLoss: Optional[bool] = None


logger = logging.getLogger(__name__)
router = APIRouter()

# Flag to control whether to capture real data to dummy files
# Set this to True to capture real IBKR data to dummy files, False to disable capturing
CAPTURE_REAL_DATA_TO_DUMMY = False

# Path to store order reason data
REASON_DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "order_reasons.json"
)

# Path to store real IBKR data for dummy use
DUMMY_POSITIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "dummy_positions.json"
)
DUMMY_OPEN_ORDERS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "dummy_open_orders.json"
)
DUMMY_ACCOUNT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "dummy_account.json"
)

# Ensure the data directory exists
os.makedirs(os.path.dirname(REASON_DATA_FILE), exist_ok=True)

# Initialize the order reason data file if it doesn't exist
if not os.path.exists(REASON_DATA_FILE):
    with open(REASON_DATA_FILE, "w") as f:
        json.dump({}, f)

# Initialize the dummy data files if they don't exist
if not os.path.exists(DUMMY_POSITIONS_FILE):
    with open(DUMMY_POSITIONS_FILE, "w") as f:
        json.dump([], f)

if not os.path.exists(DUMMY_OPEN_ORDERS_FILE):
    with open(DUMMY_OPEN_ORDERS_FILE, "w") as f:
        json.dump([], f)
        
if not os.path.exists(DUMMY_ACCOUNT_FILE):
    with open(DUMMY_ACCOUNT_FILE, "w") as f:
        json.dump({"name": "Demo Account", "balance": 100000.00}, f)


def load_reason_data():
    """Load order reason data from file"""
    try:
        with open(REASON_DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading order reason data: {str(e)}")
        return {}


def save_reason_data(data):
    """Save order reason data to file"""
    try:
        with open(REASON_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving order reason data: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to save order reason data: {str(e)}"
        )


def load_dummy_positions():
    """Load dummy positions from file"""
    try:
        with open(DUMMY_POSITIONS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading dummy positions: {str(e)}")
        return []


def save_dummy_positions(positions):
    """Save positions to dummy file"""
    if not CAPTURE_REAL_DATA_TO_DUMMY:
        logger.info("Skipping saving positions to dummy file (CAPTURE_REAL_DATA_TO_DUMMY is False)")
        return
        
    try:
        with open(DUMMY_POSITIONS_FILE, "w") as f:
            json.dump(positions, f, indent=2)
        logger.info(f"Saved {len(positions)} positions to dummy file")
    except Exception as e:
        logger.error(f"Error saving dummy positions: {str(e)}")


def load_dummy_open_orders():
    """Load dummy open orders from file"""
    try:
        with open(DUMMY_OPEN_ORDERS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading dummy open orders: {str(e)}")
        return []


def save_dummy_open_orders(orders):
    """Save open orders to dummy file"""
    if not CAPTURE_REAL_DATA_TO_DUMMY:
        logger.info("Skipping saving open orders to dummy file (CAPTURE_REAL_DATA_TO_DUMMY is False)")
        return
        
    try:
        with open(DUMMY_OPEN_ORDERS_FILE, "w") as f:
            json.dump(orders, f, indent=2)
        logger.info(f"Saved {len(orders)} open orders to dummy file")
    except Exception as e:
        logger.error(f"Error saving dummy open orders: {str(e)}")


def load_dummy_account():
    """Load dummy account from file"""
    try:
        with open(DUMMY_ACCOUNT_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading dummy account: {str(e)}")
        return {"name": "Demo Account", "balance": 100000.00}


def save_dummy_account(account):
    """Save account to dummy file"""
    if not CAPTURE_REAL_DATA_TO_DUMMY:
        logger.info("Skipping saving account to dummy file (CAPTURE_REAL_DATA_TO_DUMMY is False)")
        return
        
    try:
        with open(DUMMY_ACCOUNT_FILE, "w") as f:
            json.dump(account, f, indent=2)
        logger.info("Saved account data to dummy file")
    except Exception as e:
        logger.error(f"Error saving dummy account: {str(e)}")


# Cache for IBKR connection
_ibkr_cache: Dict[str, Any] = {
    "connection": None,
    "thread": None,
    "last_connect_time": 0,
    "last_positions": [],
    "last_positions_time": 0,
    "last_account_summary": None,
    "last_open_orders": [],
}

# Load dummy data from files instead of hardcoded values
DUMMY_POSITIONS = load_dummy_positions()
DUMMY_OPEN_ORDERS = load_dummy_open_orders()
DUMMY_ACCOUNT = load_dummy_account()


def get_cached_connection() -> tuple[Optional[Any], Optional[Any]]:
    """Get cached connection or create new one"""
    current_time = time.time()

    # If we have a recent connection, return it
    if (
        _ibkr_cache["connection"] is not None
        and _ibkr_cache["thread"] is not None
        and current_time - _ibkr_cache["last_connect_time"] < 300
    ):  # 5 minute cache
        return _ibkr_cache["connection"], _ibkr_cache["thread"]

    # Clean up old connection if it exists
    if _ibkr_cache["connection"] is not None:
        try:
            _ibkr_cache["connection"].disconnect()
        except:
            pass

    # Create new connection
    try:
        ibkr_conn, ibkr_thread = connect_to_ibkr()
        _ibkr_cache["connection"] = ibkr_conn
        _ibkr_cache["thread"] = ibkr_thread
        _ibkr_cache["last_connect_time"] = current_time
        return ibkr_conn, ibkr_thread
    except Exception as e:
        logger.error(f"Failed to connect to IBKR: {str(e)}")
        return None, None


@router.get("/positions")
async def get_positions(
    use_dummy: bool = False, use_fallback: bool = True, refresh: bool = False
):
    """
    Get positions from IBKR
    
    Parameters:
    - use_dummy: If true, returns dummy data
    - use_fallback: If true, falls back to dummy data if IBKR connection fails
    - refresh: If true, forces refresh from IBKR instead of using cached data
    """
    logger.info("API: Get positions from IBKR")
    
    try:
        # If we're forcing dummy data, return it right away
        if use_dummy:
            logger.info("Using dummy positions data")
            return {"account": DUMMY_ACCOUNT, "positions": DUMMY_POSITIONS, "openOrders": DUMMY_OPEN_ORDERS}
            
        # Check if we have recent cached data
        current_time = time.time()
        if (
            not refresh
            and _ibkr_cache["last_positions"]
            and _ibkr_cache["last_account_summary"]
            and current_time - _ibkr_cache["last_positions_time"] < 30  # 30 second cache
        ):
            logger.info("Using cached positions data")
            return {
                "account": _ibkr_cache["last_account_summary"],
                "positions": _ibkr_cache["last_positions"],
                "openOrders": _ibkr_cache["last_open_orders"],
            }
            
        # Get IBKR connection
        ibkr_conn, ibkr_thread = get_cached_connection()
        if not ibkr_conn or not ibkr_thread:
            if use_fallback:
                logger.warning("Failed to connect to IBKR, using dummy positions data")
                return {"account": DUMMY_ACCOUNT, "positions": DUMMY_POSITIONS, "openOrders": DUMMY_OPEN_ORDERS}
            else:
                raise HTTPException(status_code=500, detail="Failed to connect to IBKR")
                
        # Get positions from IBKR
        positions = ibkr_conn.get_positions(refresh=refresh)

        # If refreshing prices, iterate through positions and update them
        if refresh:
            logger.info("Manual price refresh triggered for positions.")
            for pos in positions:
                symbol = pos.get("symbol")
                if not symbol:
                    continue

                # Fetch fresh price
                new_price = get_finnhub_price(symbol, refresh=True)
                if new_price is None:
                    new_price = get_alpha_vantage_price(symbol, refresh=True)

                if new_price is not None:
                    logger.info(f"Updating price for {symbol} from {pos.get('currentPrice')} to {new_price}")
                    pos["currentPrice"] = new_price
                    # Also update the 'value' of the position
                    if "shares" in pos:
                        pos["value"] = pos["shares"] * new_price
                else:
                    logger.warning(f"Could not refresh price for {symbol}")

        if not positions and use_fallback:
            logger.warning("No positions returned from IBKR, using dummy data")
            return {"account": DUMMY_ACCOUNT, "positions": DUMMY_POSITIONS, "openOrders": DUMMY_OPEN_ORDERS}
        
        # Get account summary from IBKR
        account_summary = ibkr_conn.get_account_summary()
        
        # Get open orders from IBKR
        open_orders = ibkr_conn.get_open_orders()
        
        # Calculate total portfolio value
        total_value = sum(pos.get("value", 0) for pos in positions)
        
        # Calculate allocation percentages
        for pos in positions:
            if total_value > 0 and pos.get("value", 0) > 0:
                pos["allocation"] = (pos["value"] / total_value) * 100
            else:
                pos["allocation"] = 0
                
        # Format positions
        formatted_positions = []
        
        # Load reason data to add to positions
        reason_data = load_reason_data()
        
        # Try to match positions with open orders for target prices and stop losses
        for pos in positions:
            # Skip positions missing critical data
            if "symbol" not in pos or "currentPrice" not in pos or not pos["currentPrice"]:
                logger.warning(f"Skipping position missing data: {pos}")
                continue
                
            # Default values if we can't find any orders
            target_price = None
            stop_loss = None
            risk_reward_ratio = None
            
            # Find orders for this position
            position_orders = []
            for order in open_orders:
                if order.get("symbol") == pos["symbol"]:
                    position_orders.append(order)
                    
                    # Check if this is a target price order (limit sell)
                    if (
                        order.get("action") == "SELL" and 
                        order.get("orderType") == "LMT" and 
                        order.get("limitPrice") and 
                        (target_price is None or 
                         (pos.get("shares", 0) > 0 and order.get("limitPrice") > target_price) or
                         (pos.get("shares", 0) < 0 and order.get("limitPrice") < target_price))
                    ):
                        target_price = order.get("limitPrice")
                        
                    # Check if this is a stop loss order (stop sell)
                    if (
                        order.get("action") == "SELL" and 
                        (order.get("orderType") == "STP" or order.get("orderType") == "STP LMT") and
                        order.get("stopPrice") and
                        (stop_loss is None or 
                         (pos.get("shares", 0) > 0 and order.get("stopPrice") < stop_loss) or
                         (pos.get("shares", 0) < 0 and order.get("stopPrice") > stop_loss))
                    ):
                        stop_loss = order.get("stopPrice")
                        
            # Try to find position in reason data for expected stop loss
            expected_stop_loss = None
            order_id_str = str(pos["symbol"])
            if order_id_str in reason_data and reason_data[order_id_str].get("stopLoss"):
                try:
                    expected_stop_loss = float(reason_data[order_id_str]["stopLoss"])
                except:
                    pass
                    
            # Calculate risk/reward ratio if we have target price and stop loss
            if target_price and stop_loss and pos["currentPrice"]:
                if pos.get("shares", 0) > 0:  # Long position
                    potential_reward = target_price - pos["currentPrice"]
                    potential_risk = pos["currentPrice"] - stop_loss
                else:  # Short position
                    potential_reward = pos["currentPrice"] - target_price
                    potential_risk = stop_loss - pos["currentPrice"]
                    
                if potential_risk > 0:
                    risk_reward_ratio = potential_reward / potential_risk
                    
            # Get position type (long/short)
            is_long_position = pos.get("shares", 0) > 0
                    
            # Format the position data
            formatted_position = {
                "symbol": pos["symbol"],
                "name": pos.get("name", pos["symbol"]),
                "shares": pos.get("shares", 0),
                "entryPrice": pos.get("entryPrice", 0),
                "currentPrice": pos.get("currentPrice", 0),
                "value": pos.get("value", 0),
                "allocation": pos.get("allocation", 0),
                "profitLoss": pos.get("profitLoss", 0),
                "profitLossPercent": pos.get("profitLossPercent", 0),
                "targetPrice": target_price,
                "stopLoss": stop_loss,
                "expectedStopLoss": expected_stop_loss,
                "riskRewardRatio": risk_reward_ratio,
                "isShort": not is_long_position,
                "openOrders": position_orders,
                "priceSource": price_cache.get_price_with_timestamp(
                    pos["symbol"]
                ).get("source", "Unknown"),
            }
            
            formatted_positions.append(formatted_position)
                
        # If no positions returned and we should fall back, return dummy data
        if not formatted_positions and use_fallback:
            logger.warning("No valid positions from IBKR, using dummy data")
            return {"account": DUMMY_ACCOUNT, "positions": DUMMY_POSITIONS, "openOrders": DUMMY_OPEN_ORDERS}
            
        # Cache the data for future use
        _ibkr_cache["last_positions"] = formatted_positions
        _ibkr_cache["last_account_summary"] = account_summary
        _ibkr_cache["last_open_orders"] = open_orders
        _ibkr_cache["last_positions_time"] = time.time()
        
        # Save the real data to our dummy files for future use
        save_dummy_positions(formatted_positions)
        save_dummy_open_orders(open_orders)
        save_dummy_account(account_summary)
        
        # Return the data
        return {
            "account": account_summary,
            "positions": formatted_positions,
            "openOrders": open_orders,
        }
        
    except Exception as e:
        logger.error(f"Error getting positions: {str(e)}")
        if use_fallback:
            logger.warning("Error getting positions, using dummy data")
            return {"account": DUMMY_ACCOUNT, "positions": DUMMY_POSITIONS, "openOrders": DUMMY_OPEN_ORDERS}
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to get positions: {str(e)}"
            )


@router.get("/open-orders")
async def get_open_orders(use_dummy: bool = False, use_fallback: bool = True, refresh: bool = False):
    """
    Get open orders from IBKR
    
    Parameters:
    - use_dummy: If true, returns dummy data
    - use_fallback: If true, falls back to dummy data if IBKR connection fails
    - refresh: If true, forces refresh of current prices for symbols in open orders
    """
    logger.info("API: Get open orders from IBKR")
    
    try:
        # If we're forcing dummy data, return it right away
        if use_dummy:
            logger.info("Using dummy open orders data")
            return DUMMY_OPEN_ORDERS
            
        # Get IBKR connection
        ibkr_conn, ibkr_thread = get_cached_connection()
        if not ibkr_conn or not ibkr_thread:
            if use_fallback:
                logger.warning("Failed to connect to IBKR, using dummy open orders data")
                return DUMMY_OPEN_ORDERS
            else:
                raise HTTPException(status_code=500, detail="Failed to connect to IBKR")
                
        # Get open orders from IBKR
        open_orders = ibkr_conn.get_open_orders()

        # If refreshing prices, iterate through orders and update current prices
        if refresh:
            logger.info("Manual price refresh triggered for open orders.")
            for order in open_orders:
                symbol = order.get("symbol")
                if not symbol:
                    continue

                # Fetch fresh price
                new_price = get_finnhub_price(symbol, refresh=True)
                if new_price is None:
                    new_price = get_alpha_vantage_price(symbol, refresh=True)

                if new_price is not None:
                    logger.info(f"Updating price for {symbol} in order {order.get('orderId')} to {new_price}")
                    order["currentPrice"] = new_price
                else:
                    logger.warning(f"Could not refresh price for {symbol} in order {order.get('orderId')}")
        
        # If no orders returned and we should fall back, return dummy data
        if not open_orders and use_fallback:
            logger.warning("No orders returned from IBKR, using dummy data")
            return DUMMY_OPEN_ORDERS
            
        # Cache the orders for future use
        _ibkr_cache["last_open_orders"] = open_orders
        
        # Save the real orders to our dummy file for future use
        save_dummy_open_orders(open_orders)
        
        # Return the orders
        return open_orders
        
    except Exception as e:
        logger.error(f"Error getting open orders: {str(e)}")
        if use_fallback:
            logger.warning("Error getting open orders, using dummy data")
            return DUMMY_OPEN_ORDERS
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to get open orders: {str(e)}"
            )


# Add the new endpoint to get current prices
@router.get("/prices")
async def get_current_prices(symbols: str, refresh: bool = False):
    """
    Get current prices for one or more stock symbols from various price sources

    Args:
        symbols: Comma-separated list of stock symbols
        refresh: Whether to force refresh from API instead of using cache

    Returns:
        Dictionary mapping symbols to their current prices and metadata
    """
    try:
        symbol_list = symbols.split(",")
        result = {}

        for symbol in symbol_list:
            # Clean up the symbol
            clean_symbol = symbol.strip().upper()
            if not clean_symbol:
                continue

            # If not refreshing, try to get from cache first
            if not refresh:
                cached_data = price_cache.get_price_with_timestamp(clean_symbol)
                if cached_data.get("price") is not None:
                    result[clean_symbol] = {
                        "price": cached_data["price"],
                        "cached": True,
                        "timestamp": cached_data.get("timestamp_formatted", "Unknown"),
                        "source": cached_data.get("source", "Unknown"),
                    }
                    logger.info(
                        f"Using cached price for {clean_symbol}: ${cached_data['price']}"
                    )
                    continue

            # Try Finnhub first
            logger.info(f"Trying Finnhub for {clean_symbol}...")
            price = get_finnhub_price(clean_symbol, refresh=refresh)

            if price is not None:
                # The price is already cached by get_finnhub_price
                cached_data = price_cache.get_price_with_timestamp(clean_symbol)
                result[clean_symbol] = {
                    "price": price,
                    "cached": False,
                    "timestamp": cached_data.get("timestamp_formatted", "Unknown"),
                    "source": "Finnhub",
                }
                continue

            # If Finnhub fails, try Alpha Vantage
            logger.info(f"Finnhub failed for {clean_symbol}, trying Alpha Vantage...")
            price = get_alpha_vantage_price(clean_symbol, refresh=refresh)

            if price is not None:
                # The price is already cached by get_alpha_vantage_price
                cached_data = price_cache.get_price_with_timestamp(clean_symbol)
                result[clean_symbol] = {
                    "price": price,
                    "cached": False,
                    "timestamp": cached_data.get("timestamp_formatted", "Unknown"),
                    "source": "Alpha Vantage",
                }
            else:
                logger.warning(
                    f"Failed to get price for {clean_symbol} from all sources"
                )
                result[clean_symbol] = {
                    "price": None,
                    "cached": False,
                    "error": "Price data not available",
                }

        return result
    except Exception as e:
        logger.error(f"Error getting prices: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get prices: {str(e)}")


@router.get("/cache/status")
async def get_cache_status():
    """
    Get the current status of the price cache

    Returns:
        Dictionary with cache statistics
    """
    try:
        all_cached_prices = price_cache.get_all_cached_prices()

        # Calculate stats
        total_symbols = len(all_cached_prices)

        if total_symbols == 0:
            return {
                "status": "empty",
                "total_symbols": 0,
                "cache_file": CACHE_FILE,
                "message": "No prices in cache",
            }

        # Get latest and oldest timestamps
        timestamps = [
            data.get("timestamp", 0)
            for data in all_cached_prices.values()
            if data.get("timestamp")
        ]

        if timestamps:
            latest_timestamp = max(timestamps)
            oldest_timestamp = min(timestamps)

            # Format for display
            latest_time = datetime.fromtimestamp(latest_timestamp).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            oldest_time = datetime.fromtimestamp(oldest_timestamp).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # Calculate age in hours
            latest_age_hours = (time.time() - latest_timestamp) / 3600
            oldest_age_hours = (time.time() - oldest_timestamp) / 3600
        else:
            latest_time = "Unknown"
            oldest_time = "Unknown"
            latest_age_hours = 0
            oldest_age_hours = 0

        # Group by source
        sources = {}
        for symbol, data in all_cached_prices.items():
            source = data.get("source", "Unknown")
            if source not in sources:
                sources[source] = 0
            sources[source] += 1

        return {
            "status": "active",
            "total_symbols": total_symbols,
            "cache_file": CACHE_FILE,
            "latest_price": latest_time,
            "latest_age_hours": round(latest_age_hours, 2),
            "oldest_price": oldest_time,
            "oldest_age_hours": round(oldest_age_hours, 2),
            "sources": sources,
            "symbols": list(all_cached_prices.keys()),
        }

    except Exception as e:
        logger.error(f"Error getting cache status: {str(e)}")
        return {"status": "error", "error": str(e)}


@router.delete("/cache/clear")
async def clear_cache():
    """
    Clear the price cache

    Returns:
        Status message
    """
    try:
        price_cache.clear_cache()
        return {"status": "success", "message": "Price cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


# Add diagnostic endpoints
@router.get("/diagnostics/connection")
async def check_connection():
    """Check IBKR connection status"""
    try:
        logger.info("Testing IBKR connection...")
        ibkr_app, thread = get_cached_connection()

        if ibkr_app is None:
            return {
                "status": "disconnected",
                "message": "Could not connect to IBKR API",
            }

        if not ibkr_app.connected or ibkr_app.nextOrderId is None:
            return {
                "status": "partial",
                "message": "Connected but not fully initialized",
                "connected": ibkr_app.connected,
                "nextOrderId": ibkr_app.nextOrderId,
            }

        return {
            "status": "connected",
            "message": "Successfully connected to IBKR API",
            "clientId": ibkr_app.clientId,
            "nextOrderId": ibkr_app.nextOrderId,
        }

    except Exception as e:
        logger.error(f"Error checking connection: {str(e)}")
        return {"status": "error", "message": f"Error checking connection: {str(e)}"}


@router.get("/diagnostics/orders")
async def diagnose_orders():
    """Diagnose issues with order retrieval"""
    try:
        logger.info("Testing order retrieval...")
        ibkr_app, thread = get_cached_connection()

        if ibkr_app is None:
            return {
                "status": "disconnected",
                "message": "Could not connect to IBKR API",
            }

        # Get open orders
        logger.info("Fetching open orders from IBKR...")

        # Reset the open orders flag to make sure we get fresh data
        ibkr_app.open_orders = []
        ibkr_app.open_orders_event.clear()

        # Try to get client ID
        client_id = getattr(ibkr_app, "clientId", None)

        # Record timing
        start_time = time.time()

        # Request orders
        if client_id == 0:
            logger.info("Binding manual orders with reqAutoOpenOrders...")
            ibkr_app.reqAutoOpenOrders(True)

        logger.info("Requesting open orders for current client...")
        ibkr_app.reqOpenOrders()

        logger.info("Requesting all open orders across all clients...")
        ibkr_app.reqAllOpenOrders()

        # Wait for response with longer timeout
        timeout = 30
        logger.info(f"Waiting up to {timeout} seconds for open orders data...")
        received = ibkr_app.open_orders_event.wait(timeout=timeout)

        end_time = time.time()
        elapsed = end_time - start_time

        if not received:
            logger.warning(f"Open orders request timed out after {timeout} seconds")
            return {
                "status": "timeout",
                "message": f"Order retrieval timed out after {timeout} seconds",
                "elapsed_seconds": elapsed,
                "orders_received": 0,
            }

        order_count = len(ibkr_app.open_orders)
        logger.info(f"Received {order_count} open orders from IBKR")

        # Return diagnostic info
        return {
            "status": "success",
            "message": f"Retrieved {order_count} orders in {elapsed:.2f} seconds",
            "elapsed_seconds": elapsed,
            "orders_received": order_count,
            "client_id": client_id,
            "orders": (
                ibkr_app.open_orders if order_count < 10 else "too many to display"
            ),
        }

    except Exception as e:
        logger.error(f"Error diagnosing orders: {str(e)}")
        return {"status": "error", "message": f"Error diagnosing orders: {str(e)}"}


@router.get("/diagnostics/check-orders")
async def check_has_orders():
    """Use the specialized check_has_orders method to diagnose IBKR order issues"""
    try:
        logger.info("Running check_has_orders diagnostic...")
        ibkr_app, thread = get_cached_connection()

        if ibkr_app is None:
            return {
                "status": "disconnected",
                "message": "Could not connect to IBKR API",
            }

        # Run the dedicated diagnostic method
        result = ibkr_app.check_has_orders()

        # Update the cached open orders if successful
        if result.get("success", False) and result.get("order_count", 0) > 0:
            _ibkr_cache["last_open_orders"] = ibkr_app.open_orders

        return {
            "status": "success" if result.get("success", False) else "error",
            "diagnosis": result,
        }

    except Exception as e:
        logger.error(f"Error in check_has_orders: {str(e)}")
        return {"status": "error", "message": f"Error in check_has_orders: {str(e)}"}


@router.get("/diagnostics/ibkr-settings")
async def check_ibkr_settings():
    """Check IBKR settings that might affect order retrieval"""
    try:
        # Check connection first
        ibkr_app, thread = get_cached_connection()

        if ibkr_app is None:
            return {
                "status": "error",
                "message": "Could not connect to IBKR API",
                "recommendations": [
                    "Make sure TWS or IB Gateway is running",
                    "Check that API connections are enabled in TWS/Gateway",
                    "Verify the port number in your connection settings",
                ],
            }

        # Check if we have a valid client ID
        client_id = getattr(ibkr_app, "clientId", None)

        # Try to request open orders with different methods
        settings_check = {
            "connection": {
                "status": "connected" if ibkr_app.connected else "disconnected",
                "client_id": client_id,
                "next_order_id": ibkr_app.nextOrderId,
            },
            "permissions": {},
        }

        # Test reqOpenOrders
        logger.info("Testing reqOpenOrders...")
        ibkr_app.open_orders = []
        ibkr_app.open_orders_event.clear()
        ibkr_app.reqOpenOrders()
        got_orders_1 = ibkr_app.open_orders_event.wait(timeout=3)
        order_count_1 = len(ibkr_app.open_orders)
        settings_check["permissions"]["reqOpenOrders"] = {
            "status": "success" if got_orders_1 else "timeout",
            "orders_found": order_count_1,
        }

        # Test reqAutoOpenOrders
        logger.info("Testing reqAutoOpenOrders...")
        ibkr_app.open_orders = []
        ibkr_app.open_orders_event.clear()
        ibkr_app.reqAutoOpenOrders(True)
        got_orders_2 = ibkr_app.open_orders_event.wait(timeout=3)
        order_count_2 = len(ibkr_app.open_orders)
        settings_check["permissions"]["reqAutoOpenOrders"] = {
            "status": "success" if got_orders_2 else "timeout",
            "orders_found": order_count_2,
        }

        # Test reqAllOpenOrders
        logger.info("Testing reqAllOpenOrders...")
        ibkr_app.open_orders = []
        ibkr_app.open_orders_event.clear()
        ibkr_app.reqAllOpenOrders()
        got_orders_3 = ibkr_app.open_orders_event.wait(timeout=5)
        order_count_3 = len(ibkr_app.open_orders)
        settings_check["permissions"]["reqAllOpenOrders"] = {
            "status": "success" if got_orders_3 else "timeout",
            "orders_found": order_count_3,
        }

        # Generate recommendations
        recommendations = []

        if client_id != 0:
            recommendations.append("Change client ID to 0 to access all orders")

        if not got_orders_1 and not got_orders_2 and not got_orders_3:
            recommendations.extend(
                [
                    "Check 'Read-Only API' is NOT checked in TWS/IB Gateway API settings",
                    "Make sure 'Enable ActiveX and Socket Clients' is checked",
                    "Verify that you have active orders in your IBKR account",
                    "Try restarting TWS/IB Gateway",
                    "In TWS/Gateway, go to Global Configuration > API > Settings and verify permissions",
                ]
            )

        settings_check["recommendations"] = recommendations

        return {
            "status": "success",
            "message": "IBKR settings check complete",
            "results": settings_check,
            "total_orders_found": max(order_count_1, order_count_2, order_count_3),
        }

    except Exception as e:
        logger.error(f"Error checking IBKR settings: {str(e)}")
        return {"status": "error", "message": f"Error checking IBKR settings: {str(e)}"}


@router.post("/reconnect")
async def reconnect_to_ibkr(client_id: int = 0, port: int = 7496):
    """Force reconnection to IBKR API"""
    global _ibkr_cache

    # Clean up old connection if it exists
    if _ibkr_cache["connection"] is not None:
        try:
            _ibkr_cache["connection"].disconnect()
        except:
            pass
    if _ibkr_cache["thread"] is not None:
        try:
            _ibkr_cache["thread"].join(timeout=1)
        except:
            pass

    # Reset cache
    _ibkr_cache = {
        "connection": None,
        "thread": None,
        "last_connect_time": 0,
        "last_positions": [],
        "last_positions_time": 0,
        "last_account_summary": None,
        "last_open_orders": [],
    }

    # Create new connection
    connection, thread = connect_to_ibkr(client_id=client_id, port=port)
    if connection is not None:
        _ibkr_cache["connection"] = connection
        _ibkr_cache["thread"] = thread
        _ibkr_cache["last_connect_time"] = time.time()
        return {"success": True, "message": "Successfully reconnected to IBKR"}
    else:
        raise HTTPException(status_code=503, detail="Failed to reconnect to IBKR")


# Order reason endpoints
@router.post("/orders/{order_id}/reason")
async def save_order_reason(order_id: int, reason_data: OrderReasonData):
    """Save order reason data"""
    try:
        # Load existing data
        all_reasons = load_reason_data()

        # Convert order_id to string for JSON keys
        order_id_str = str(order_id)

        # Save the new reason data
        all_reasons[order_id_str] = reason_data.dict()

        # Save back to file
        save_reason_data(all_reasons)

        logger.info(f"Saved reason data for order {order_id}")
        return {"success": True, "message": f"Reason data saved for order {order_id}"}
    except Exception as e:
        logger.error(f"Error saving reason data for order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/reasons")
async def get_order_reasons(ids: Optional[str] = None):
    """Get reason data for orders

    Parameters:
    - ids: Comma-separated list of order IDs to get reasons for. If not provided, returns all reasons.
    """
    try:
        # Load all reason data
        all_reasons = load_reason_data()

        # If IDs are specified, filter to only those orders
        if ids:
            order_ids = [str(id) for id in ids.split(",")]
            filtered_reasons = {
                id: all_reasons.get(id, {}) for id in order_ids if id in all_reasons
            }
            return filtered_reasons

        # Otherwise return all reasons
        return all_reasons
    except Exception as e:
        logger.error(f"Error getting order reasons: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}/reason")
async def get_order_reason(order_id: int):
    """Get reason data for a specific order"""
    try:
        # Load all reason data
        all_reasons = load_reason_data()

        # Convert order_id to string for JSON keys
        order_id_str = str(order_id)

        # Return the reason data if it exists
        if order_id_str in all_reasons:
            return all_reasons[order_id_str]
        else:
            raise HTTPException(
                status_code=404, detail=f"No reason data found for order {order_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reason data for order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/orders/{order_id}/reason")
async def delete_order_reason(order_id: int):
    """Delete reason data for a specific order"""
    try:
        # Load all reason data
        all_reasons = load_reason_data()

        # Convert order_id to string for JSON keys
        order_id_str = str(order_id)

        # Remove the reason data if it exists
        if order_id_str in all_reasons:
            del all_reasons[order_id_str]

            # Save back to file
            save_reason_data(all_reasons)

            logger.info(f"Deleted reason data for order {order_id}")
            return {
                "success": True,
                "message": f"Reason data deleted for order {order_id}",
            }
        else:
            raise HTTPException(
                status_code=404, detail=f"No reason data found for order {order_id}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting reason data for order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account")
async def get_account(use_dummy: bool = False, use_fallback: bool = True):
    """
    Get account info from IBKR
    
    Parameters:
    - use_dummy: If true, returns dummy data
    - use_fallback: If true, falls back to dummy data if IBKR connection fails
    """
    logger.info("API: Get account info from IBKR")
    
    try:
        # If we're forcing dummy data, return it right away
        if use_dummy:
            logger.info("Using dummy account data")
            return DUMMY_ACCOUNT
            
        # Check if we have recent cached data
        current_time = time.time()
        if (
            _ibkr_cache["last_account_summary"] and
            current_time - _ibkr_cache["last_positions_time"] < 60  # 1 minute cache
        ):
            logger.info("Using cached account data")
            return _ibkr_cache["last_account_summary"]
            
        # Get IBKR connection
        ibkr_conn, ibkr_thread = get_cached_connection()
        if not ibkr_conn or not ibkr_thread:
            if use_fallback:
                logger.warning("Failed to connect to IBKR, using dummy account data")
                return DUMMY_ACCOUNT
            else:
                raise HTTPException(status_code=500, detail="Failed to connect to IBKR")
                
        # Get account summary from IBKR
        account_summary = ibkr_conn.get_account_summary()
        
        # If no account summary and we should fall back, return dummy data
        if not account_summary and use_fallback:
            logger.warning("No account summary returned from IBKR, using dummy data")
            return DUMMY_ACCOUNT
            
        # Cache the account summary for future use
        _ibkr_cache["last_account_summary"] = account_summary
        _ibkr_cache["last_positions_time"] = time.time()  # Update the timestamp
        
        # Save the real account summary to our dummy file for future use
        save_dummy_account(account_summary)
        
        # Return the account summary
        return account_summary
        
    except Exception as e:
        logger.error(f"Error getting account: {str(e)}")
        if use_fallback:
            logger.warning("Error getting account, using dummy data")
            return DUMMY_ACCOUNT
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to get account: {str(e)}"
            )


@router.get("/toggle-capture")
async def toggle_capture_data(enable: bool = None):
    """
    Toggle or get the status of capturing real data to dummy files
    
    Parameters:
    - enable: If provided, sets the capture flag to this value. If not provided, returns the current status.
    """
    global CAPTURE_REAL_DATA_TO_DUMMY
    
    # If enable parameter is provided, set the flag
    if enable is not None:
        CAPTURE_REAL_DATA_TO_DUMMY = enable
        status = "enabled" if enable else "disabled"
        logger.info(f"Capturing real data to dummy files {status}")
        return {"status": "success", "capturing": CAPTURE_REAL_DATA_TO_DUMMY}
    
    # Otherwise just return the current status
    return {"status": "success", "capturing": CAPTURE_REAL_DATA_TO_DUMMY}
