from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import BarData
import threading
import time
from typing import Dict, Optional, Tuple, Union, List
import pandas as pd
import yfinance as yf
import logging
import requests
import random
from .price_cache import price_cache
import os
import json

# Reduce IBKR API debug logging noise
logging.getLogger('ibapi').setLevel(logging.WARNING)
# Also reduce yfinance debug logging
logging.getLogger('yfinance').setLevel(logging.WARNING)

# Alpha Vantage API key - replace with your actual key
ALPHA_VANTAGE_API_KEY = "HSRASDHSORA26WRU"  # HSRASDHSORA26WRU HP5WVUCIHY2VF27E  Get free key from https://www.alphavantage.co/support/#api-key

# Finnhub API key - replace with your actual key
FINNHUB_API_KEY = "d0tba7hr01qid5qdtbe0d0tba7hr01qid5qdtbeg"  # Get free key from https://finnhub.io/register

"""
To set up your Finnhub API key:
1. Visit https://finnhub.io/register to create a free account
2. After registration, go to your dashboard at https://finnhub.io/dashboard
3. Copy your API key from the dashboard
4. Replace "YOUR_FINNHUB_API_KEY" above with your actual key

Free tier limitations:
- 60 API calls per minute
- US fundamentals & filings
- US stocks basic financials
- US market data

This implementation uses the Quote endpoint: https://finnhub.io/docs/api/quote
"""

# Function to get stock price from Alpha Vantage
def get_alpha_vantage_price(symbol: str, refresh: bool = False) -> Optional[float]:
    """Get current price from Alpha Vantage API with cache support"""
    symbol = symbol.upper()
    
    # Check cache first if not refreshing
    if not refresh:
        cached_price = price_cache.get_price(symbol)
        if cached_price is not None:
            print(f"Using cached price for {symbol}: ${cached_price}")
            return cached_price
    
    # If refreshing or no cache, fetch from API
    try:
        print(f"Trying Alpha Vantage for {symbol}...")
        
        # Global quote endpoint gives current price
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if "Global Quote" in data and "05. price" in data["Global Quote"]:
            price = float(data["Global Quote"]["05. price"])
            print(f"SUCCESS: Got Alpha Vantage price for {symbol}: ${price}")
            
            # If successful, cache the result
            if price is not None:
                price_cache.set_price(symbol, price, source="Alpha Vantage")
            
            return price
        else:
            print(f"Alpha Vantage returned unexpected data format for {symbol}")
            return None
    except Exception as e:
        print(f"Alpha Vantage API error for {symbol}: {str(e)}")
        return None

# Function to get stock price from Finnhub
def get_finnhub_price(symbol: str, refresh: bool = False) -> Optional[float]:
    """Get current price from Finnhub API with cache support"""
    symbol = symbol.upper()
    
    # Check cache first if not refreshing
    if not refresh:
        cached_price = price_cache.get_price(symbol)
        if cached_price is not None:
            print(f"Using cached price for {symbol}: ${cached_price}")
            return cached_price
    
    # If refreshing or no cache, fetch from API
    try:
        print(f"Trying Finnhub for {symbol}...")
        
        # Quote endpoint gives current price
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        if "c" in data and data["c"] > 0:
            price = float(data["c"])  # Current price
            print(f"SUCCESS: Got Finnhub price for {symbol}: ${price}")
            
            # If successful, cache the result
            if price is not None:
                price_cache.set_price(symbol, price, source="Finnhub")
            
            return price
        else:
            print(f"Finnhub returned unexpected data format for {symbol}")
            return None
    except Exception as e:
        print(f"Finnhub API error for {symbol}: {str(e)}")
        return None

class IBKRConnection(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        # Connection tracking
        self.connected = False
        self.nextOrderId = None
        
        # Account data
        self.account_summary = {}
        self.account_summary_event = threading.Event()
        
        # Position data
        self.positions = []
        self.positions_event = threading.Event()
        self.position_market_data = {}  # Store current market prices
        
        # Market data
        self.data = {}
        self.market_data_event = threading.Event()
        
        # Order data
        self.open_orders = []
        self.open_orders_event = threading.Event()
        
    def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        """Handle errors from API"""
        # Some error codes are actually just warnings or connection status
        if errorCode in [2104, 2106, 2158]:  # Connection status codes
            print(f"Connection status: {errorString}")
        else:
            print(f"Error: {reqId}, {errorCode}, {errorString}")
    
    def connectAck(self):
        """Callback when connection is acknowledged"""
        print("Connection acknowledged")
        
    def nextValidId(self, orderId: int):
        
        """Callback for the next valid order ID
        You initially connect without any valid order ID
        TWS/IB Gateway accepts your connection
        IBKR automatically calls your nextValidId callback, providing your first valid ID
        This ID gets stored in self.nextOrderId and self.connected is set to True
        Only then can you make requests like getting account information:
        """
        super().nextValidId(orderId)
        self.nextOrderId = orderId
        self.connected = True
        print("Connected to IBKR API successfully")
    
    # Account data methods
    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Callback for account summary data"""
        print(f"Account Summary received - Account: {account}, Tag: {tag}, Value: {value}, Currency: {currency}")
        
        # Initialize account data if not exists
        if account not in self.account_summary:
            self.account_summary[account] = {}
            
        # Store the value with currency suffix if present
        key = f"{tag}_{currency}" if currency else tag
        self.account_summary[account][key] = value
        
    def accountSummaryEnd(self, reqId: int):
        """Callback when account summary data is complete"""
        print("Account summary data received")
        self.account_summary_event.set()
    
    def get_account_summary(self, timeout: int = 10) -> Dict:
        """
        Request and retrieve account summary information
        
        Args:
            timeout (int): Maximum time to wait for account data in seconds
            
        Returns:
            Dict: Account summary information with:
            {
                "name": str,  # Account name (e.g., "U18034687")
                "balance": float  # TotalCashValue in USD
            }
        """
        if not self.connected or self.nextOrderId is None:
            print("Cannot request account summary: not connected")
            return {}
            
        # Clear previous data and reset event
        self.account_summary = {}
        self.account_summary_event.clear()
        
        # Request account summary
        req_id = self.nextOrderId
        self.nextOrderId += 1
        
        # Define the tags we want to retrieve
        tags = "TotalCashValue"
        
        # Request the account summary
        print("Requesting account summary...")
        self.reqAccountSummary(req_id, "All", tags)
        
        # Wait for the data to arrive
        received = self.account_summary_event.wait(timeout=timeout)
        if not received:
            print(f"Account summary request timed out after {timeout} seconds")
            return {}
        
        # Cancel the request
        self.cancelAccountSummary(req_id)
        
        # Print all account summary data for debugging
        print("\n=== Account Summary Debug ===")
        print("Raw account_summary data:", self.account_summary)
        for account_id, account_data in self.account_summary.items():
            print(f"Account ID: {account_id}")
            print(f"Account Data: {account_data}")
        print("=====================\n")
        
        # The data structure is: {account_id: {'TotalCashValue_USD': value}}
        for account_id, account_data in self.account_summary.items():
            if 'TotalCashValue_USD' in account_data:
                balance = float(account_data['TotalCashValue_USD'])
                print(f"Found account data - ID: {account_id}, Balance: {balance}")
                return {
                    "name": account_id,
                    "balance": balance
                }
        
        print("No account data found with TotalCashValue_USD")
        return {
            "name": "IBKR Account",
            "balance": -1.0
        }
    
    # Position methods (overrides the default position method from EWrapper)
    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Callback for position data"""
        pos_data = {
            'account': account,
            'symbol': contract.symbol,
            'name': contract.localSymbol,  # Usually contains the company name
            'shares': position,
            'entryPrice': avgCost,
            'currentPrice': None,  # Will be updated with market data
            'value': None,  # Will be calculated after getting current price
            'allocation': None,  # Will be calculated after getting total portfolio value
            'profitLoss': None,  # Will be calculated after getting current price
            'profitLossPercent': None,  # Will be calculated after getting current price
            'secType': contract.secType,
            'exchange': contract.exchange,
            'currency': contract.currency
        }
        self.positions.append(pos_data)
        
        # Request current market data for this position
        req_id = self.nextOrderId
        self.nextOrderId += 1
        self.reqMktData(req_id, contract, "", False, False, [])
        self.position_market_data[req_id] = pos_data
        
    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """Callback for market data updates"""
        # Market data tick types:
        # 1 = Bid
        # 2 = Ask
        # 4 = Last
        # 6 = High
        # 7 = Low
        # 9 = Close
        
        if reqId in self.position_market_data:
            pos_data = self.position_market_data[reqId]
            symbol = pos_data['symbol']
            
            print(f"Received tick for {symbol}: Type={tickType}, Price=${price}")
            
            # Last price is best, but use others if available
            if tickType == 4:  # Last price
                pos_data['currentPrice'] = price
                print(f"Updated {symbol} with last price: ${price}")
            elif tickType == 9 and pos_data['currentPrice'] is None:  # Close price as fallback
                pos_data['currentPrice'] = price
                print(f"Updated {symbol} with close price: ${price}")
            elif (tickType == 1 or tickType == 2) and pos_data['currentPrice'] is None:  # Bid/Ask as fallback
                pos_data['currentPrice'] = price
                print(f"Updated {symbol} with bid/ask price: ${price}")
            
            # Calculate derived values if we have a price
            if pos_data['currentPrice'] is not None:
                pos_data['value'] = pos_data['currentPrice'] * pos_data['shares']
                pos_data['profitLoss'] = (pos_data['currentPrice'] - pos_data['entryPrice']) * pos_data['shares']
                # Avoid division by zero
                if pos_data['entryPrice'] > 0:
                    pos_data['profitLossPercent'] = ((pos_data['currentPrice'] - pos_data['entryPrice']) / pos_data['entryPrice']) * 100
                else:
                    pos_data['profitLossPercent'] = 0
                    print(f"Warning: Entry price for {pos_data['symbol']} is zero or negative, cannot calculate percentage")
                print(f"Calculated values for {symbol}: Value=${pos_data['value']}, P/L=${pos_data['profitLoss']}")
        elif reqId in self.data:
            # This is for historical data requests
            pass
        else:
            print(f"Received tick for unknown reqId {reqId}: Type={tickType}, Price=${price}")
    
    def positionEnd(self):
        """Callback when position data is complete"""
        print(f"Position data received: {len(self.positions)} positions")
        self.positions_event.set()
    
    def get_positions(self, timeout: int = 10, refresh: bool = False, alpha_vantage_key: str = ALPHA_VANTAGE_API_KEY, finnhub_key: str = FINNHUB_API_KEY) -> List[Dict]:
        """
        Request and retrieve positions for the account with full risk management data
        
        Args:
            timeout (int): Maximum time to wait for position data in seconds
            refresh (bool): Whether to force refresh prices from APIs
            alpha_vantage_key (str): Alpha Vantage API key for price fallback
            finnhub_key (str): Finnhub API key for price fallback
            
        Returns:
            List[Dict]: List of positions with details including:
                - symbol
                - name
                - shares
                - entryPrice
                - currentPrice
                - value
                - allocation
                - profitLoss
                - profitLossPercent
        """
        global ALPHA_VANTAGE_API_KEY, FINNHUB_API_KEY
        if alpha_vantage_key != ALPHA_VANTAGE_API_KEY:
            ALPHA_VANTAGE_API_KEY = alpha_vantage_key
            
        if finnhub_key != FINNHUB_API_KEY:
            FINNHUB_API_KEY = finnhub_key
            
        if not self.connected or self.nextOrderId is None:
            print("Cannot request positions: not connected")
            return []
            
        # Clear previous data and reset event
        self.positions = []
        self.positions_event.clear()
        
        # Request positions from IBKR
        print("Requesting positions from IBKR...")
        self.reqPositions()
        
        # Wait for the position data to arrive
        received = self.positions_event.wait(timeout=timeout)
        if not received:
            print(f"Positions request timed out after {timeout} seconds")
            return []
            
        print(f"Received {len(self.positions)} positions from IBKR, looking for price data...")
        
        # Cache for prices to avoid redundant API calls
        price_cache_local = {}
        
        # Try to fill in market data for positions
        for pos in self.positions:
            symbol = pos['symbol']
            
            # Skip if market data already available from IBKR API
            if pos['currentPrice'] is not None:
                continue
            
            # First check our local session cache to avoid redundant lookups
            if symbol in price_cache_local:
                pos['currentPrice'] = price_cache_local[symbol]
                print(f"Using local session cached price for {symbol}: ${pos['currentPrice']}")
                continue
                
            # Try the file cache regardless of refresh setting
            cached_price = price_cache.get_price(symbol)
            if cached_price is not None:
                pos['currentPrice'] = cached_price
                price_cache_local[symbol] = cached_price
                print(f"Using file cached price for {symbol}: ${cached_price}")
                continue
            
            # If not refreshing, just leave price as None
            if not refresh:
                print(f"No cached price available for {symbol} and refresh=false, leaving price as None")
                continue
            
            # Only fetch new prices if refresh=true
            if refresh:
                # Try Finnhub first
                print(f"Refresh=true, fetching fresh price for {symbol}")
                current_price = get_finnhub_price(symbol, refresh=refresh)
                
                if current_price is not None:
                    pos['currentPrice'] = current_price
                    price_cache_local[symbol] = current_price
                    continue
                    
                print(f"Finnhub failed for {symbol}, trying Alpha Vantage...")
                
                # Try Alpha Vantage as second source
                current_price = get_alpha_vantage_price(symbol, refresh=refresh)
                
                if current_price is not None:
                    pos['currentPrice'] = current_price
                    price_cache_local[symbol] = current_price
                    continue
                
                print(f"Alpha Vantage failed for {symbol}, trying Yahoo Finance as last resort...")
                
                # Add small delay before Yahoo Finance to avoid rate limits
                delay = random.uniform(2, 5)
                print(f"Adding {delay:.2f}s delay to avoid Yahoo rate limits...")
                time.sleep(delay)
                
                # Try to get price from Yahoo Finance as last resort
                try:
                    ticker = yf.Ticker(symbol)
                    
                    # Print full exception if debug info is needed
                    try:
                        info = ticker.info
                        print(f"Yahoo Finance info contains {len(info.keys())} keys")
                    except Exception as e:
                        print(f"Error getting ticker.info: {str(e)}")
                        # Try to get just historical data instead
                        info = {}
                    
                    # Try to get price from ticker.info
                    post_market_price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose') or info.get('postMarketPrice')
                    if post_market_price is not None:
                        pos['currentPrice'] = post_market_price
                        print(f"SUCCESS: Using Yahoo Finance info price for {symbol}: ${post_market_price}")
                        price_cache.set_price(symbol, post_market_price, source="Yahoo Finance")
                        price_cache_local[symbol] = post_market_price
                    else:
                        # Try historical data approach
                        try:
                            print(f"Trying historical data for {symbol}...")
                            hist = ticker.history(period='1d')
                            if not hist.empty:
                                current_price = hist['Close'][-1]
                                pos['currentPrice'] = current_price
                                print(f"SUCCESS: Using Yahoo Finance historical price for {symbol}: ${current_price}")
                                price_cache.set_price(symbol, current_price, source="Yahoo Finance Historical")
                                price_cache_local[symbol] = current_price
                            else:
                                print(f"No historical data available for {symbol}")
                                # Use entry price as last resort
                                pos['currentPrice'] = pos['entryPrice']
                                print(f"Using entry price as fallback for {symbol}: ${pos['entryPrice']}")
                        except Exception as e:
                            print(f"Error getting historical data: {str(e)}")
                            # Use entry price as last resort
                            pos['currentPrice'] = pos['entryPrice']
                            print(f"Using entry price as fallback for {symbol}: ${pos['entryPrice']}")
                except Exception as e:
                    print(f"All price sources failed for {symbol}: {str(e)}")
                    # Use entry price as last resort
                    pos['currentPrice'] = pos['entryPrice']
                    print(f"Using entry price as fallback for {symbol}: ${pos['entryPrice']}")
        
        # Now calculate derived values for all positions
        # Only calculate values if we have prices
        for pos in self.positions:
            if pos['currentPrice'] is not None:
                pos['value'] = pos['currentPrice'] * pos['shares']
                pos['profitLoss'] = (pos['currentPrice'] - pos['entryPrice']) * pos['shares']
                # Avoid division by zero
                if pos['entryPrice'] > 0:
                    pos['profitLossPercent'] = ((pos['currentPrice'] - pos['entryPrice']) / pos['entryPrice']) * 100
                else:
                    pos['profitLossPercent'] = 0
                    print(f"Warning: Entry price for {pos['symbol']} is zero or negative, cannot calculate percentage")
            else:
                # If price is None, set derived values to None as well
                pos['value'] = None
                pos['profitLoss'] = None
                pos['profitLossPercent'] = None
                print(f"No price available for {pos['symbol']}, derived values will be None")
        
        # Calculate portfolio allocation (only for positions with values)
        positions_with_values = [pos for pos in self.positions if pos['value'] is not None]
        total_value = sum(pos['value'] for pos in positions_with_values)
        
        for pos in self.positions:
            if pos['value'] is not None and total_value > 0:
                pos['allocation'] = (pos['value'] / total_value) * 100
            else:
                pos['allocation'] = None
        
        # Cancel the request
        self.cancelPositions()
        
        return self.positions
    
    # Market data methods
    def historicalData(self, reqId: int, bar: BarData):
        """Callback for historical data"""
        if reqId not in self.data:
            self.data[reqId] = []
            
        self.data[reqId].append({
            'date': bar.date,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume
        })
    
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Callback when historical data is complete"""
        print(f"Historical data received for request {reqId}")
    
    # Order methods
    def openOrder(self, orderId: int, contract: Contract, order: Order, orderState):
        """Callback for open orders"""
        # Create order data with only essential fields
        order_data = {
            'orderId': orderId,
            'symbol': contract.symbol,
            'name': contract.localSymbol,
            'action': order.action,
            'orderType': order.orderType,
            'totalQuantity': order.totalQuantity,
            'limitPrice': order.lmtPrice,
            'stopPrice': order.auxPrice,
            'status': orderState.status,
            'filled': 0,  # Will be updated by orderStatus
            'remaining': order.totalQuantity  # Will be updated by orderStatus
        }
        self.open_orders.append(order_data)
        
    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
        """Callback for order status updates"""
        # Update the order status in open_orders list
        for order in self.open_orders:
            if order['orderId'] == orderId:
                order['status'] = status
                order['filled'] = filled
                order['remaining'] = remaining
                order['avgFillPrice'] = avgFillPrice
                order['whyHeld'] = whyHeld
                break
                
    def openOrderEnd(self):
        """Callback when all open orders have been received"""
        self.open_orders_event.set()
        
    def get_open_orders(self, timeout: int = 15) -> List[Dict]:
        """
        Request and retrieve open orders with their target prices and stop losses
        
        Args:
            timeout (int): Maximum time to wait for order data in seconds
            
        Returns:
            List[Dict]: List of open orders with details including:
                - symbol
                - name
                - action (BUY/SELL)
                - orderType
                - totalQuantity
                - limitPrice (target price for limit orders)
                - stopPrice (stop loss for stop orders)
                - status
                - filled
                - remaining
                - avgFillPrice
                - whyHeld
                - timeInForce
                - and many more order parameters
        """
        if not self.connected or self.nextOrderId is None:
            print("Cannot request open orders: not connected")
            return []
            
        # Clear previous data and reset event
        print("Clearing existing open orders data")
        self.open_orders = []
        self.open_orders_event.clear()
        
        # Request open orders
        print("Requesting open orders from IBKR...")
        
        # Set up a flag to track if we got orders
        got_orders = False
        
        try:
            # Step 1: First try reqOpenOrders
            print("Step 1: Requesting open orders for current client...")
            self.reqOpenOrders()
            
            # Wait briefly for initial response
            initial_timeout = 3
            print(f"Waiting up to {initial_timeout} seconds for initial response...")
            got_orders = self.open_orders_event.wait(timeout=initial_timeout)
            
            # Step 2: If no orders yet, try binding to manual orders
            if not got_orders or len(self.open_orders) == 0:
                print("No orders yet, trying to bind to manual orders...")
                self.open_orders_event.clear()  # Reset the event
                
                # Try binding to manual orders
                print("Step 2: Binding to manual orders with reqAutoOpenOrders...")
                self.reqAutoOpenOrders(True)
                
                # Wait for response
                print(f"Waiting up to {initial_timeout} seconds for manual orders...")
                got_orders = self.open_orders_event.wait(timeout=initial_timeout)
            
            # Step 3: Try reqAllOpenOrders as a last resort
            if not got_orders or len(self.open_orders) == 0:
                print("Still no orders, trying reqAllOpenOrders...")
                self.open_orders_event.clear()  # Reset the event
                
                # Request all orders from all clients
                print("Step 3: Requesting all open orders across all clients...")
                self.reqAllOpenOrders()
                
                # Wait for the data to arrive with remaining timeout
                remaining_timeout = timeout - (2 * initial_timeout)
                if remaining_timeout < 5:
                    remaining_timeout = 5  # Ensure at least 5 seconds
                    
                print(f"Waiting up to {remaining_timeout} seconds for all open orders...")
                got_orders = self.open_orders_event.wait(timeout=remaining_timeout)
            
            print(f"Order retrieval complete. Found {len(self.open_orders)} orders.")
            
            # For each order, try to get current market price
            for order in self.open_orders:
                try:
                    # Try to get price from cache first
                    cached_price = price_cache.get_price(order['symbol'])
                    if cached_price is not None:
                        order['currentPrice'] = cached_price
                        print(f"Using cached price for order {order['symbol']}: ${cached_price}")
                        
                        # If it's a limit order, calculate potential profit/loss
                        if order['limitPrice'] and order['action'] == 'BUY':
                            order['potentialProfit'] = (order['limitPrice'] - order['currentPrice']) * order['remaining']
                            order['potentialProfitPercent'] = ((order['limitPrice'] - order['currentPrice']) / order['currentPrice']) * 100
                        elif order['limitPrice'] and order['action'] == 'SELL':
                            order['potentialProfit'] = (order['currentPrice'] - order['limitPrice']) * order['remaining']
                            order['potentialProfitPercent'] = ((order['currentPrice'] - order['limitPrice']) / order['limitPrice']) * 100
                    else:
                        # No cached price available
                        order['currentPrice'] = None
                        order['potentialProfit'] = None
                        order['potentialProfitPercent'] = None
                        
                except Exception as e:
                    print(f"Error getting price data for order {order['symbol']}: {str(e)}")
                    order['currentPrice'] = None
                    order['potentialProfit'] = None
                    order['potentialProfitPercent'] = None
            
            # If we got no orders, check if we need to have permissions
            if len(self.open_orders) == 0:
                print("No open orders found. If you believe this is incorrect, check:")
                print("1. You have active orders in your IBKR account")
                print("2. Your TWS/IB Gateway has permission to retrieve open orders")
                print("3. API settings in TWS/IB Gateway > Global Configuration > API > Settings")
                print("4. Make sure 'Read-Only API' is NOT checked in TWS/IB Gateway API settings")
                print("5. Make sure you are using client ID 0 to access all orders")
                
            return self.open_orders
            
        except Exception as e:
            print(f"Exception in get_open_orders: {str(e)}")
            return []
    
    def check_has_orders(self) -> dict:
        """
        Utility method to check if we can retrieve open orders from IBKR
        
        Returns:
            dict: Diagnostic information about the order retrieval process
        """
        if not self.connected or self.nextOrderId is None:
            return {
                "success": False,
                "message": "Not connected to IBKR API",
                "connected": self.connected,
                "nextOrderId": self.nextOrderId
            }
            
        # Reset to start fresh
        self.open_orders = []
        self.open_orders_event.clear()
        
        # Record timing
        start_time = time.time()
        
        try:
            # If we're client ID 0, we can also bind manual orders
            if self.clientId == 0:
                print("Client ID 0 detected - binding manual orders...")
                self.reqAutoOpenOrders(True)
            
            # Request orders for this client
            print("Requesting open orders for current client...")
            self.reqOpenOrders()
            
            # Also request all orders from all clients
            print("Requesting all open orders across all clients...")
            self.reqAllOpenOrders()
            
            # Wait for the data to arrive - use a longer timeout for diagnostic purposes
            timeout = 30
            print(f"Waiting up to {timeout} seconds for open orders data...")
            received = self.open_orders_event.wait(timeout=timeout)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            if not received:
                print(f"Open orders request timed out after {timeout} seconds")
                return {
                    "success": False,
                    "message": f"Order retrieval timed out after {timeout} seconds",
                    "elapsed_seconds": elapsed,
                    "order_count": 0
                }
                
            order_count = len(self.open_orders)
            print(f"Received {order_count} open orders from IBKR")
            
            # Return diagnostic info
            return {
                "success": True,
                "message": f"Retrieved {order_count} orders in {elapsed:.2f} seconds",
                "elapsed_seconds": elapsed,
                "order_count": order_count,
                "sample_symbols": [order.get('symbol') for order in self.open_orders[:3]] if order_count > 0 else []
            }
            
        except Exception as e:
            print(f"Exception in check_has_orders: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "error": str(e)
            }
    
    # Helper methods
    @staticmethod
    def create_contract(symbol: str, sec_type: str = "STK", exchange: str = "SMART", currency: str = "USD"):
        """Create a contract object"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.exchange = exchange
        contract.currency = currency
        return contract


def connect_to_ibkr(ip='127.0.0.1', port=7496, client_id=0) -> Tuple[Union[IBKRConnection, None], Union[threading.Thread, None]]:
    """
    Establishes connection to Interactive Brokers API
    
    Args:
        ip (str): IP address for TWS/IB Gateway (default: 127.0.0.1)
        port (int): Socket port number (7496 for TWS, 7497 for paper trading)
        client_id (int): Unique client ID (Using 0 for master client to access all orders)
        
    Returns:
        tuple: (IBKRConnection instance, api thread)
    """
    try:
        print(f"Attempting to connect to IBKR at {ip}:{port} with client ID {client_id}...")
        app = IBKRConnection()
        app.connect(ip, port, client_id)
        
        # Start the socket in a thread
        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()
        
        # Wait for connection to complete (nextValidId will be called)
        timeout = 20  # Increased from 15 seconds
        start_time = time.time()
        
        # Display connection status while waiting
        while not app.connected and time.time() - start_time < timeout:
            time.sleep(1)
            elapsed = time.time() - start_time
            print(f"Waiting for connection... {elapsed:.1f}s elapsed")
        
        if not app.connected:
            print("Failed to connect to IBKR API within timeout period")
            print("Make sure TWS/IB Gateway is running and configured to accept API connections")
            print("Check TWS/IB Gateway settings > API > Settings:")
            print("- Enable ActiveX and Socket Clients should be checked")
            print("- Allow connections from localhost should be checked")
            print("- Socket port should match the port parameter")
            print("- Trusted IPs should include 127.0.0.1")
            print("- Read-Only API access must be UNCHECKED to see orders")
            return None, None
        
        print(f"Successfully connected to IBKR API (IP: {ip}, Port: {port}, Client ID: {client_id})")
        
        # Store client ID
        app.clientId = client_id
        
        # Check market data permissions
        print("Checking market data connectivity...")
        # Create a test contract for a major stock
        test_contract = Contract()
        test_contract.symbol = "AAPL"
        test_contract.secType = "STK"
        test_contract.exchange = "SMART"
        test_contract.currency = "USD"
        
        # Request market data to test
        test_req_id = app.nextOrderId
        app.nextOrderId += 1
        print(f"Requesting test market data for AAPL (reqId: {test_req_id})...")
        app.reqMktData(test_req_id, test_contract, "", False, False, [])
        
        # Wait briefly to see if we get any errors
        time.sleep(3)
        print("Market data test completed, continuing with initialization")
        
        # Test order data permissions explicitly
        print("Testing order data permissions...")
        try:
            # Clear any existing order data
            app.open_orders = []
            app.open_orders_event.clear()
            
            # Request orders
            print("Requesting open orders with reqOpenOrders...")
            app.reqOpenOrders()
            
            # Also try to bind to manual orders
            print("Requesting manual orders with reqAutoOpenOrders...")
            app.reqAutoOpenOrders(True)
            
            # Wait briefly for order data
            orders_timeout = 5
            print(f"Waiting up to {orders_timeout} seconds for initial order data...")
            app.open_orders_event.wait(timeout=orders_timeout)
            
            print(f"Initial orders check complete. Found {len(app.open_orders)} orders.")
        except Exception as e:
            print(f"Error during order permissions test: {str(e)}")
        
        # Fetch account summary
        account_summary = app.get_account_summary(timeout=20)
        
        print(f"Connected to IBKR API (IP: {ip}, Port: {port}, Client ID: {client_id})")
        return app, api_thread
    
    except Exception as e:
        print(f"Exception during IBKR connection: {str(e)}")
        print("Make sure TWS/IB Gateway is running and accepting connections")
        return None, None


# Example usage
if __name__ == "__main__":
    try:
        # For local TWS/IB Gateway
        ibkr_app, thread = connect_to_ibkr()
        
        if ibkr_app is not None:
            # Get positions with full risk management data
            print("\nRetrieving positions...")
            positions = ibkr_app.get_positions()
        
            print("\nPositions:")
            for pos in positions:
                print(f"Symbol: {pos['symbol']}")
                print(f"Name: {pos['name']}")
                print(f"Shares: {pos['shares']}")
                print(f"Entry Price: ${pos['entryPrice']:.2f}")
                print(f"Current Price: ${pos['currentPrice']:.2f}")
                print(f"Value: ${pos['value']:.2f}")
                print(f"Allocation: {pos['allocation']:.2f}%")
                print(f"P/L: ${pos['profitLoss']:.2f} ({pos['profitLossPercent']:.2f}%)")
                print("-------------------")
            
            # Keep the main thread running to allow API to work
            time.sleep(5)
    except Exception as e:
        print(f"Error in main: {e}")
