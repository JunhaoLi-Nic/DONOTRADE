from fastapi import APIRouter, HTTPException, Query, Body, Depends
from typing import Optional, List, Dict, Any, Tuple, Union
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from ..database import db
from ..stock_analysis_tools import consecutive_analysis, hurst_exponent, volatility, next_day_stats, probability_distribution
from ..stock_analysis_tools.data_utils import read_and_prepare_data
from ..services.yfinance_sync import YFinanceSync
import re
import traceback
import json
import random
import yfinance as yf  # Make sure we import yfinance directly
import requests  # Add requests for Finnhub API calls
from ..services.ibkr_connection import FINNHUB_API_KEY  # Import Finnhub API key
from ..auth import get_current_user
from pydantic import BaseModel
from ..stock_analysis_tools.correlation_coefficient import compute_correlation_matrix

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/stock-analysis")

def replace_nan_with_none(obj):
    """Replace NaN values with None for JSON serialization"""
    if isinstance(obj, dict):
        return {k: replace_nan_with_none(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nan_with_none(x) for x in obj]
    elif isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    else:
        return obj

async def get_mongodb_data(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_direction: int = 1,
    limit: Optional[int] = None,
    most_recent_only: bool = False
) -> Tuple[Union[pd.DataFrame, dict, None], str]:
    """
    Utility function to get data from MongoDB as a fallback.
    
    Parameters:
        ticker: Stock ticker symbol
        start_date: Optional start date in format YYYY-MM-DD
        end_date: Optional end date in format YYYY-MM-DD
        sort_direction: 1 for ascending (oldest first), -1 for descending (newest first)
        limit: Optional limit on number of records to return
        most_recent_only: If True, return only the most recent price point
        
    Returns:
        Tuple of (data, message) where data can be DataFrame, dict or None
        depending on the request parameters and available data
    """
    try:
        logger.info(f"Fetching data from MongoDB for ticker: {ticker}")
        
        # Build MongoDB query
        query = {"ticker": ticker.upper()}
        
        # Add date filtering if provided
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                query["date"] = {"$gte": start_datetime}
            except ValueError:
                return None, f"Invalid start_date format: {start_date}"
                
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                if "date" in query:
                    query["date"]["$lte"] = end_datetime
                else:
                    query["date"] = {"$lte": end_datetime}
            except ValueError:
                return None, f"Invalid end_date format: {end_date}"
        
        # Execute query on prices collection
        market_db = db.client["market"]
        
        if most_recent_only:
            # Get only the most recent price point
            price_data = market_db["prices"].find_one(query, sort=[("date", -1)])
            
            if not price_data:
                return None, f"No price data found for ticker: {ticker}"
                
            # Try to get previous day's close for comparison
            prev_date = price_data.get("date") - timedelta(days=1)
            prev_price = market_db["prices"].find_one(
                {"ticker": ticker.upper(), "date": {"$lte": prev_date}},
                sort=[("date", -1)]
            )
            
            # Calculate price changes if we have previous data
            current_price = price_data.get("close")
            prev_close = prev_price.get("close") if prev_price else None
            
            if prev_close:
                price_change = current_price - prev_close
                percent_change = (price_change / prev_close) * 100
            else:
                price_change = 0
                percent_change = 0
            
            # Format the response
            result = {
                "ticker": ticker,
                "current_price": float(current_price),
                "market_price": float(current_price),
                "previous_close": float(prev_close) if prev_close else None,
                "change": float(price_change),
                "percent_change": float(percent_change),
                "timestamp": price_data.get("date").isoformat(),
                "source": "mongodb"
            }
            
            return result, "Successfully fetched current price from MongoDB"
        else:
            # For historical data, get multiple data points
            cursor = market_db["prices"].find(query).sort("date", sort_direction)
            
            if limit:
                cursor = cursor.limit(limit)
                
            price_data = list(cursor)
            
            if not price_data:
                return None, f"No price data found for ticker: {ticker}"
                
            # Convert to pandas DataFrame for easier analysis
            df = pd.DataFrame(price_data)
            
            logger.info(f"Found {len(df)} records for ticker: {ticker}")
            return df, "Successfully fetched historical data from MongoDB"
            
    except Exception as e:
        logger.error(f"Error fetching data from MongoDB: {str(e)}")
        return None, f"Error fetching data from MongoDB: {str(e)}"

@router.get("/ticker-data/{ticker}")
async def get_ticker_data(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(5000000, ge=1, le=5000000),
    skip: int = Query(0, ge=0)
):
    """
    Get price data for a ticker from MongoDB.
    
    Parameters:
        ticker: Stock ticker symbol
        start_date: Optional start date in format YYYY-MM-DD
        end_date: Optional end date in format YYYY-MM-DD
        limit: Maximum number of results to return
        skip: Number of results to skip
    
    Returns:
        Price data for the ticker
    """
    try:
        logger.info(f"Fetching price data for ticker: {ticker}")
        
        # Build MongoDB query
        query = {"ticker": ticker.upper()}
        
        # Add date filtering if provided
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                query["date"] = {"$gte": start_datetime}
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
                
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                if "date" in query:
                    query["date"]["$lte"] = end_datetime
                else:
                    query["date"] = {"$lte": end_datetime}
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        # Execute query on prices collection
        market_db = db.client["market"]
        cursor = market_db["prices"].find(query).sort("date", 1).skip(skip).limit(limit)
        
        # Convert to list and process
        price_data = list(cursor)
        
        if not price_data:
            logger.warning(f"No price data found for ticker: {ticker}")
            return {"message": f"No data found for {ticker}", "data": []}
        
        # Convert ObjectId to string for JSON serialization
        for item in price_data:
            if "_id" in item:
                item["_id"] = str(item["_id"])
            if "date" in item and isinstance(item["date"], datetime):
                item["date"] = item["date"].strftime("%Y-%m-%d")
                
        logger.info(f"Found {len(price_data)} records for ticker: {ticker}")
        return {"data": price_data}
        
    except Exception as e:
        logger.error(f"Error fetching ticker data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

@router.get("/tickers")
async def get_available_tickers(
    limit: int = Query(100, ge=1, le=1000),
    page: int = Query(1, ge=1)
):
    """
    Get a list of available tickers in the database with pagination support.
    
    Parameters:
        limit: Number of tickers to return per page (max 1000)
        page: Page number (starting from 1)
    
    Returns:
        List of ticker symbols with pagination info
    """
    try:
        market_db = db.client["market"]
        
        # Get distinct ticker values
        all_tickers = market_db["prices"].distinct("ticker", {})
        total_tickers = len(all_tickers)
        
        # Sort tickers alphabetically
        all_tickers.sort()
        
        # Calculate pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        # Get the requested page of tickers
        paged_tickers = all_tickers[start_idx:end_idx]
        
        logger.info(f"Returning {len(paged_tickers)} tickers (page {page}, limit {limit}, total {total_tickers})")
        
        return {
            "page": page,
            "limit": limit,
            "count": len(paged_tickers),
            "total": total_tickers,
            "tickers": paged_tickers,
            "has_more": end_idx < total_tickers
        }
        
    except Exception as e:
        logger.error(f"Error fetching tickers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching tickers: {str(e)}")

@router.get("/tickers/search")
async def search_tickers(
    query: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
    exact_match: bool = Query(False)
):
    """
    Search for tickers by prefix or pattern.
    
    Parameters:
        query: Search string to match against ticker symbols
        limit: Maximum number of results to return
        exact_match: If true, only return exact matches; otherwise, use pattern matching
    
    Returns:
        List of matching ticker symbols
    """
    try:
        market_db = db.client["market"]
        all_tickers = market_db["prices"].distinct("ticker", {})
        
        # Convert query to uppercase for case-insensitive matching
        search_query = query.upper()
        
        # Filter tickers based on the search query
        if exact_match:
            # Return only exact matches
            matching_tickers = [ticker for ticker in all_tickers if ticker == search_query]
        else:
            # Return tickers that start with or contain the query
            if len(search_query) <= 2:
                # For short queries, only match the beginning of the ticker
                matching_tickers = [ticker for ticker in all_tickers if ticker.startswith(search_query)]
            else:
                # For longer queries, match anywhere in the ticker
                matching_tickers = [ticker for ticker in all_tickers if search_query in ticker]
        
        # Sort results
        matching_tickers.sort()
        
        # Limit the number of results
        limited_results = matching_tickers[:limit]
        
        logger.info(f"Found {len(limited_results)} tickers matching '{query}' (total matches: {len(matching_tickers)})")
        
        return {
            "query": query,
            "count": len(limited_results),
            "total_matches": len(matching_tickers),
            "tickers": limited_results
        }
        
    except Exception as e:
        logger.error(f"Error searching tickers: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching tickers: {str(e)}")

@router.get("/dataframe/{ticker}")
async def get_ticker_dataframe(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    auto_sync: bool = True
):
    """
    Get price data for a ticker as pandas DataFrame format (in JSON).
    This is meant for integration with the stock analysis tools.
    
    Parameters:
        ticker: Stock ticker symbol
        start_date: Optional start date in format YYYY-MM-DD
        end_date: Optional end date in format YYYY-MM-DD
        auto_sync: If True, automatically sync with yfinance if data is available
    
    Returns:
        Price data in a format suitable for pandas DataFrame conversion
    """
    try:
        logger.info(f"Getting dataframe for ticker {ticker} with auto_sync={auto_sync}")
        
        # If auto_sync is enabled, try to sync with yfinance first
        if auto_sync:
            try:
                sync_result = await YFinanceSync.sync_ticker_data(ticker, start_date, end_date)
                logger.info(f"Sync result for {ticker}: {sync_result}")
                
                # If sync found differences and updated MongoDB, we'll use the updated data
                # Otherwise, continue with the regular flow to fetch from MongoDB
            except Exception as sync_error:
                logger.warning(f"Error during auto-sync for {ticker}: {str(sync_error)}")
                # Continue with MongoDB data if sync fails
        
        # Use the existing endpoint to get the data from MongoDB
        response = await get_ticker_data(ticker, start_date, end_date, 5000000, 0)
        
        if not response.get("data"):
            logger.warning(f"No data found in MongoDB for {ticker}, trying yfinance directly")
            
            # Try yfinance directly if no data in MongoDB
            if auto_sync:
                yf_df = await YFinanceSync.get_yfinance_data(ticker, start_date, end_date)
                
                if not yf_df.empty:
                    logger.info(f"Found data in yfinance for {ticker}, updating MongoDB")
                    # Update MongoDB with this data for future use
                    await YFinanceSync.update_mongodb(ticker, yf_df)
                    
                    # Format yfinance data for response
                    df_data = {
                        "date": [d.strftime("%Y-%m-%d") for d in yf_df["date"].tolist()],
                        "open": yf_df["open"].tolist(),
                        "high": yf_df["high"].tolist(),
                        "low": yf_df["low"].tolist(),
                        "close": yf_df["close"].tolist(),
                        "volume": yf_df["volume"].tolist()
                    }
                    
                    return {
                        "success": True,
                        "ticker": ticker,
                        "data": df_data,
                        "source": "yfinance"
                    }
            
            return {"success": False, "message": f"No data found for {ticker}"}
        
        # Format the data as needed for DataFrame compatibility
        df_data = {
            "date": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": []
        }
        
        for item in response["data"]:
            df_data["date"].append(item.get("date"))
            df_data["open"].append(item.get("open"))
            df_data["high"].append(item.get("high"))
            df_data["low"].append(item.get("low"))
            df_data["close"].append(item.get("close"))
            df_data["volume"].append(item.get("volume"))
        
        return {
            "success": True,
            "ticker": ticker,
            "data": df_data,
            "source": "mongodb"
        }
        
    except Exception as e:
        logger.error(f"Error creating dataframe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating dataframe: {str(e)}")

@router.get("/consecutive/{ticker}")
async def get_consecutive_analysis(
    ticker: str,
    direction: str = "down",
    min_days: int = 2,
    max_days: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sync_yfinance: bool = True
):
    """
    Analyze consecutive price movements and their continuation probability.
    
    Parameters:
        ticker: Stock ticker symbol
        direction: "up" for price increases, "down" for price drops
        min_days: Minimum number of consecutive days to analyze
        max_days: Maximum number of consecutive days to analyze
        start_date: Optional start date in format YYYY-MM-DD
        end_date: Optional end date in format YYYY-MM-DD
        sync_yfinance: Whether to sync with yfinance before analysis
    
    Returns:
        Analysis of consecutive price movements
    """
    try:
        logger.info(f"Analyzing consecutive {direction} movements for ticker: {ticker}")
        
        # Validate dates if provided
        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                
                # Check if dates are in the future
                today = datetime.now()
                if start_dt > today:
                    logger.warning(f"Start date {start_date} is in the future, using today instead")
                    start_date = today.strftime("%Y-%m-%d")
                    start_dt = today
                
                if end_dt > today:
                    logger.warning(f"End date {end_date} is in the future, using today instead")
                    end_date = today.strftime("%Y-%m-%d")
                    end_dt = today
                
                if start_dt > end_dt:
                    logger.warning(f"Start date {start_date} is after end date {end_date}, swapping")
                    start_date, end_date = end_date, start_date
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
        
        # Replace future dates with reasonable defaults
        today = datetime.now()
        one_year_ago = (today - timedelta(days=365)).strftime("%Y-%m-%d")
        today_str = today.strftime("%Y-%m-%d")
        
        if not start_date:
            start_date = one_year_ago
            logger.info(f"No start date provided, using default: {start_date}")
        
        if not end_date:
            end_date = today_str
            logger.info(f"No end date provided, using default: {end_date}")
            
        # Sync with yfinance if requested
        sync_result = None
        if sync_yfinance:
            logger.info(f"Syncing {ticker} data with yfinance before consecutive analysis")
            try:
                sync_result = await YFinanceSync.sync_ticker_data(ticker, start_date, end_date)
                logger.info(f"YFinance sync result: {sync_result}")
                
                if sync_result.get("mongodb_updated", False):
                    logger.info(f"MongoDB data updated from yfinance for {ticker}")
            except Exception as sync_error:
                logger.warning(f"Error during yfinance sync: {str(sync_error)}. Proceeding with existing data.")
        
        # Try to get data directly from MongoDB first
        mongodb_df, message = await get_mongodb_data(ticker, start_date, end_date)
        
        # Check if we have enough data
        if mongodb_df is None or len(mongodb_df) < min_days + 5:
            logger.warning(f"Insufficient MongoDB data for {ticker} ({len(mongodb_df) if mongodb_df is not None else 0} rows). Trying standard analysis.")
        else:
            logger.info(f"Found {len(mongodb_df)} MongoDB records for {ticker}. Preparing for analysis.")
            
            # Prepare the data for consecutive analysis
            try:
                # Convert close prices to numeric and clean
                mongodb_df["close"] = pd.to_numeric(mongodb_df["close"], errors='coerce')
                mongodb_df = mongodb_df.dropna(subset=["close"])
                
                # Check if we still have enough data
                if len(mongodb_df) < min_days + 5:
                    logger.warning(f"Insufficient clean data points ({len(mongodb_df)}) after removing NaN values")
                else:
                    # Add required columns for analysis
                    if direction.lower() == "up":
                        mongodb_df["is_target_day"] = mongodb_df["close"] > mongodb_df["close"].shift(1)
                    else:
                        mongodb_df["is_target_day"] = mongodb_df["close"] < mongodb_df["close"].shift(1)
                        
                    mongodb_df["daily_return"] = mongodb_df["close"].pct_change()
                    mongodb_df = mongodb_df.dropna()
                    
                    # Add date column if needed
                    if 'date' in mongodb_df.columns and not isinstance(mongodb_df.index, pd.DatetimeIndex):
                        # Convert date column to string format if it's not already
                        mongodb_df["date"] = mongodb_df["date"].apply(
                            lambda d: d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d)
                        )
                    elif isinstance(mongodb_df.index, pd.DatetimeIndex):
                        mongodb_df["date"] = mongodb_df.index.strftime("%Y-%m-%d")
                    else:
                        # Create a dummy date column if needed
                        mongodb_df["date"] = [f"Day {i+1}" for i in range(len(mongodb_df))]
                    
                    # Run analysis directly on the MongoDB data
                    consecutive_moves = consecutive_analysis.analyze_consecutive_patterns(mongodb_df, min_days, max_days)
                    
                    # If we found patterns, calculate probabilities and return
                    if consecutive_moves and len(consecutive_moves) > 0:
                        # Calculate continuation probabilities
                        probabilities = consecutive_analysis.calculate_continuation_probabilities(consecutive_moves)
                        
                        # Check if we have valid probabilities
                        if probabilities and len(probabilities) > 0:
                            # Convert probabilities to a JSON-serializable format
                            result = {}
                            for n_days, stats in probabilities.items():
                                result[str(n_days)] = {
                                    "count": stats["count"],
                                    "next_day_probability": stats["next_day_probability"],
                                    "avg_next_day_return": float(stats["avg_next_day_return"]),
                                    "next_days_probabilities": [
                                        {"day": day_prob["day"], "probability": day_prob["probability"]}
                                        for day_prob in stats["next_days_probabilities"]
                                    ]
                                }
                            
                            logger.info(f"Successfully analyzed consecutive moves using MongoDB data directly")
                            return {
                                "ticker": ticker,
                                "direction": direction,
                                "probabilities": result,
                                "data_source": "MongoDB"
                            }
            except Exception as prep_error:
                logger.error(f"Error preparing MongoDB data: {str(prep_error)}")
                logger.info("Falling back to standard analysis flow")
        
        # If direct MongoDB approach didn't work, try the standard flow
        try:
            logger.info(f"Using standard analysis flow for {ticker}")
            df, consecutive_moves, probabilities = consecutive_analysis.analyze_consecutive_moves(
                ticker, direction, min_days, max_days, start_date, end_date, visualize=False
            )
            
            # Check if we got valid results
            if df is None or consecutive_moves is None or probabilities is None:
                raise ValueError("No valid consecutive analysis data returned")
                
            if not consecutive_moves or len(consecutive_moves) == 0:
                raise ValueError("No consecutive patterns found in the data")
                
            # Convert probabilities to a JSON-serializable format
            result = {}
            for n_days, stats in probabilities.items():
                result[str(n_days)] = {
                    "count": stats["count"],
                    "next_day_probability": stats["next_day_probability"],
                    "avg_next_day_return": float(stats["avg_next_day_return"]),
                    "next_days_probabilities": [
                        {"day": day_prob["day"], "probability": day_prob["probability"]}
                        for day_prob in stats["next_days_probabilities"]
                    ]
                }
            
            return {
                "ticker": ticker,
                "direction": direction,
                "probabilities": result,
                "data_source": "Standard Analysis"
            }
                
        except Exception as analysis_error:
            logger.error(f"Standard analysis failed: {str(analysis_error)}")
            
            # If we already tried MongoDB directly and it failed, we don't have many options left
            # Create a minimal set of results with empty data
            min_result = {
                "ticker": ticker,
                "direction": direction,
                "probabilities": {},
                "error": f"No consecutive patterns found. Try a different date range, direction, or ticker."
            }
            
            # For each day count, add placeholder values
            for n_days in range(min_days, max_days + 1):
                min_result["probabilities"][str(n_days)] = {
                    "count": 0,
                    "next_day_probability": 0,
                    "avg_next_day_return": 0,
                    "next_days_probabilities": [
                        {"day": day, "probability": 0}
                        for day in range(1, 6)
                    ]
                }
            
            # Return this minimal result set instead of an error to prevent frontend crashes
            return min_result
        
    except ValueError as ve:
        # Handle specific value errors with a 400 status code
        logger.error(f"Value error in consecutive analysis: {str(ve)}")
        
        # Return a minimal response instead of an error
        return {
            "ticker": ticker,
            "direction": direction,
            "probabilities": {},
            "error": str(ve)
        }
        
    except Exception as e:
        # Handle other unexpected errors with a 500 status code
        logger.error(f"Error analyzing consecutive movements: {str(e)}")
        return {
            "ticker": ticker,
            "direction": direction,
            "probabilities": {},
            "error": f"An unexpected error occurred: {str(e)}"
        }

@router.get("/hurst/{ticker}")
async def get_hurst_exponent(
    ticker: str,
    window_size: int = 252,
    step: int = 63,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Calculate the Hurst exponent for a stock.
    
    Parameters:
        ticker: Stock ticker symbol
        window_size: Size of the rolling window in days
        step: Step size for rolling window
        start_date: Optional start date in format YYYY-MM-DD
        end_date: Optional end date in format YYYY-MM-DD
    
    Returns:
        Hurst exponent analysis
    """
    try:
        logger.info(f"Calculating Hurst exponent for ticker: {ticker}, window_size: {window_size}, step: {step}")
        
        # Validate inputs
        if window_size <= 0:
            raise HTTPException(status_code=400, detail="Window size must be positive")
        if step <= 0:
            raise HTTPException(status_code=400, detail="Step size must be positive")
            
        # Validate dates if provided
        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                if start_dt > end_dt:
                    logger.warning(f"Start date {start_date} is after end date {end_date}, swapping")
                    start_date, end_date = end_date, start_date
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
        
        # Call the analysis function without visualization
        try:
            df, hurst = hurst_exponent.analyze_hurst_exponent(
                ticker, window_size, step, start_date, end_date, visualize=False
            )
        except ValueError as ve:
            # Check for specific error about insufficient data points
            error_msg = str(ve)
            if "Insufficient data points" in error_msg:
                data_points_match = re.search(r"Insufficient data points \((\d+)\) for window size (\d+)", error_msg)
                if data_points_match:
                    available = int(data_points_match.group(1))
                    required = int(data_points_match.group(2))
                    
                    # Try with a smaller window size automatically
                    if available >= 63:  # If we have at least 63 data points, try with that
                        logger.info(f"Retrying with smaller window size: {available - 10} instead of {window_size}")
                        try:
                            # Use a slightly smaller window size than available data
                            adjusted_window = min(available - 10, 126)  # Don't go larger than 126
                            adjusted_step = min(step, adjusted_window // 4)  # Adjust step size proportionally
                            
                            df, hurst = hurst_exponent.analyze_hurst_exponent(
                                ticker, adjusted_window, adjusted_step, start_date, end_date, visualize=False
                            )
                            
                            # If we get here, the retry worked
                            logger.info(f"Successfully calculated Hurst with adjusted window size: {adjusted_window}")
                            window_size = adjusted_window
                            step = adjusted_step
                        except Exception as retry_error:
                            logger.error(f"Retry with smaller window size failed: {retry_error}")
                            
                            # Try one more time with even smaller window size as last resort
                            try:
                                logger.info(f"Last attempt with minimum window size")
                                min_window = max(20, available // 2)
                                min_step = max(5, min_window // 4)
                                
                                # Directly use MongoDB data instead of going through analyze_hurst_exponent
                                mongodb_df, message = await get_mongodb_data(ticker, start_date, end_date)
                                if mongodb_df is not None:
                                    # Directly calculate Hurst from close prices
                                    logger.info(f"Using {len(mongodb_df)} MongoDB data points directly")
                                    
                                    # Ensure close column is numeric and clean
                                    mongodb_df["close"] = pd.to_numeric(mongodb_df["close"], errors='coerce')
                                    clean_prices = mongodb_df["close"].dropna().values
                                    
                                    if len(clean_prices) >= min_window:
                                        hurst = hurst_exponent.calculate_hurst_exponent(clean_prices)
                                        logger.info(f"Successfully calculated direct Hurst: {hurst}")
                                        df = mongodb_df
                                    else:
                                        raise ValueError(f"Insufficient data points even after direct MongoDB access")
                                else:
                                    # If MongoDB access fails, raise the original error
                                    raise HTTPException(
                                        status_code=400,
                                        detail=f"Insufficient data points ({available}) for window size {required}. Try a smaller window size or extend the date range."
                                    )
                            except Exception as last_error:
                                logger.error(f"Final attempt failed: {last_error}")
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Insufficient data points ({available}) for Hurst calculation. Try extending the date range."
                                )
                    else:
                        # Not enough data even for a smaller window - try with raw MongoDB data
                        try:
                            mongodb_df, message = await get_mongodb_data(ticker, start_date, end_date)
                            if mongodb_df is not None:
                                # Directly calculate Hurst from close prices
                                logger.info(f"Using {len(mongodb_df)} MongoDB data points directly for small dataset")
                                
                                # Ensure close column is numeric and clean
                                mongodb_df["close"] = pd.to_numeric(mongodb_df["close"], errors='coerce')
                                clean_prices = mongodb_df["close"].dropna().values
                                
                                min_window = max(10, len(clean_prices) // 2)
                                if len(clean_prices) >= 20:  # Absolute minimum for meaningful calculation
                                    hurst = hurst_exponent.calculate_hurst_exponent(clean_prices)
                                    logger.info(f"Successfully calculated direct Hurst: {hurst}")
                                    df = mongodb_df
                                else:
                                    raise ValueError(f"Insufficient data points even after direct MongoDB access")
                            else:
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Insufficient data points ({available}) for window size {required}. Try a smaller window size or extend the date range."
                                )
                        except Exception as direct_error:
                            logger.error(f"Direct calculation failed: {direct_error}")
                            raise HTTPException(
                                status_code=400,
                                detail=f"Insufficient data points ({available}) for Hurst calculation. Try extending the date range."
                            )
            # For other value errors, pass through the original message
            else:
                raise HTTPException(status_code=400, detail=str(ve))
        
        # Check if calculation was successful
        if df is None or hurst is None:
            logger.error(f"Failed to calculate Hurst exponent for {ticker}")
            raise HTTPException(
                status_code=400, 
                detail=f"Could not calculate Hurst exponent for {ticker}. Check if sufficient price data exists."
            )
        
        # Calculate rolling Hurst values for chart
        try:
            # Check if we have log_returns
            if 'log_returns' in df.columns and not df['log_returns'].isna().all():
                logger.info("Using log_returns for rolling Hurst calculation")
                indices, hurst_values = hurst_exponent.calculate_hurst_by_window(
                    df["log_returns"].dropna(), window_size, step
                )
            else:
                # Use close prices if log_returns are not available or all NaN
                logger.info("Using close prices for rolling Hurst calculation")
                indices, hurst_values = hurst_exponent.calculate_hurst_by_window(
                    df["close"].dropna(), window_size, step
                )
            
            # Check if we got valid rolling Hurst values
            if not indices or not hurst_values or len(indices) == 0 or len(hurst_values) == 0:
                logger.warning(f"No rolling Hurst values calculated for {ticker}")
                raise ValueError("No rolling Hurst values calculated")
            
            # Convert indices to dates for the response
            dates = []
            if len(indices) > 0:
                if isinstance(df.index, pd.DatetimeIndex):
                    # Use DatetimeIndex if available
                    dates = [df.index[min(i, len(df.index)-1)].strftime("%Y-%m-%d") for i in indices]
                else:
                    # For DataFrame with date column but not as index
                    if 'date' in df.columns:
                        date_col = df['date']
                        dates = [date_col.iloc[min(i, len(date_col)-1)].strftime("%Y-%m-%d") 
                                if hasattr(date_col.iloc[min(i, len(date_col)-1)], 'strftime') 
                                else str(date_col.iloc[min(i, len(date_col)-1)]) 
                                for i in indices]
                    else:
                        # Fallback to using indices as-is
                        dates = [f"Point {i}" for i in indices]
            
            # Filter out NaN values
            filtered_dates = []
            filtered_values = []
            for i, h in enumerate(hurst_values):
                if i < len(dates) and not np.isnan(h):
                    filtered_dates.append(dates[i])
                    filtered_values.append(float(h))
            
            # Get interpretation
            interpretation = hurst_exponent.interpret_hurst(hurst)
            
            # Prepare price data for the response
            price_dates = []
            price_values = []
            
            if isinstance(df.index, pd.DatetimeIndex):
                # If the DataFrame has a DatetimeIndex
                price_dates = [date.strftime("%Y-%m-%d") for date in df.index]
                price_values = df["close"].tolist()
            elif 'date' in df.columns:
                # If the DataFrame has a date column
                price_dates = [date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date) 
                              for date in df["date"]]
                price_values = df["close"].tolist()
            
            return {
                "ticker": ticker,
                "hurst_exponent": float(hurst),
                "interpretation": interpretation,
                "window_size": window_size,  # Include the actual window size used
                "step": step,  # Include the actual step size used
                "rolling_hurst": {
                    "dates": filtered_dates,
                    "values": filtered_values
                },
                "price_data": {
                    "dates": price_dates,
                    "prices": price_values
                }
            }
        except Exception as chart_error:
            # If rolling calculation fails, still return the main Hurst value
            logger.error(f"Error calculating rolling Hurst values: {str(chart_error)}")
            interpretation = hurst_exponent.interpret_hurst(hurst)
            
            # Prepare price data for the response
            price_dates = []
            price_values = []
            
            if isinstance(df.index, pd.DatetimeIndex):
                # If the DataFrame has a DatetimeIndex
                price_dates = [date.strftime("%Y-%m-%d") for date in df.index]
                price_values = df["close"].tolist()
            elif 'date' in df.columns:
                # If the DataFrame has a date column
                price_dates = [date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date) 
                              for date in df["date"]]
                price_values = df["close"].tolist()
            
            return {
                "ticker": ticker,
                "hurst_exponent": float(hurst),
                "interpretation": interpretation,
                "window_size": window_size,  # Include the actual window size used
                "step": step,  # Include the actual step size used
                "rolling_hurst": {
                    "dates": [],
                    "values": []
                },
                "price_data": {
                    "dates": price_dates,
                    "prices": price_values
                }
            }
        
    except ValueError as e:
        # Handle specific value errors with a 400 status code
        logger.error(f"Value error calculating Hurst exponent: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail=f"Error calculating Hurst exponent: {str(e)}"
        )
    except Exception as e:
        # Handle other unexpected errors with a 500 status code
        logger.error(f"Unexpected error calculating Hurst exponent: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Server error calculating Hurst exponent: {str(e)}"
        )

@router.get("/volatility/{ticker}")
async def get_volatility(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bandwidth: float = 0.15,
    grid_size: int = 500,
    sync_yfinance: bool = True
):
    """
    Analyze stock price volatility.
    
    Parameters:
        ticker: Stock ticker symbol or cryptocurrency (e.g., BTC-USD)
        start_date: Optional start date in format YYYY-MM-DD
        end_date: Optional end date in format YYYY-MM-DD
        bandwidth: Bandwidth for KDE calculation (0.01-1.0)
        grid_size: Number of points in KDE grid (100-1000)
        sync_yfinance: Whether to sync with yfinance before analysis
    
    Returns:
        Volatility analysis
    """
    try:
        logger.info(f"Analyzing volatility for ticker: {ticker}, date range: {start_date} to {end_date}")
        
        # Check if it's a cryptocurrency (common formats: BTC-USD, ETH-USD, etc.)
        is_crypto = "-" in ticker or ticker.endswith("USDT") or ticker.endswith("USD")
        if is_crypto:
            logger.info(f"Detected cryptocurrency: {ticker}")
        
        # Validate and fix dates
        try:
            today = datetime.now()
            
            # End date validation
            if end_date:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                if end_date_obj > today:
                    logger.warning(f"End date {end_date} is in the future, using today's date instead")
                    end_date = today.strftime("%Y-%m-%d")
            else:
                # Default to today if not provided
                end_date = today.strftime("%Y-%m-%d")
            
            # Start date validation
            if start_date:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                # Check if start date is after end date
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                if start_date_obj > end_date_obj:
                    logger.warning(f"Start date {start_date} is after end date {end_date}, swapping")
                    start_date, end_date = end_date, start_date
            else:
                # Default to 1 year ago if not provided
                start_date = (today - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
                
            logger.info(f"Using adjusted date range: {start_date} to {end_date}")
                
        except ValueError as date_error:
            logger.error(f"Date format error: {str(date_error)}")
            raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD.")
            
        # For cryptocurrencies, always use yfinance
        if is_crypto:
            logger.info(f"Using YFinance directly for cryptocurrency: {ticker}")
            sync_yfinance = True
            
            try:
                import yfinance as yf
                
                # Get data from yfinance
                ticker_data = yf.Ticker(ticker)
                
                # Get historical data
                hist = ticker_data.history(start=start_date, end=end_date)
                
                if hist.empty:
                    raise ValueError(f"No historical data available for {ticker} in the specified date range")
                    
                # Convert to DataFrame format expected by volatility analysis
                df = pd.DataFrame({
                    'date': hist.index,
                    'open': hist['Open'],
                    'high': hist['High'],
                    'low': hist['Low'],
                    'close': hist['Close'],
                    'volume': hist['Volume']
                })
                
                logger.info(f"Successfully got {len(df)} historical data points for {ticker} from YFinance")
                
                # Directly call volatility analysis with the DataFrame
                returns = volatility.calculate_returns(df)
                
                # Calculate statistics
                avg = float(returns.mean())
                std = float(returns.std())
                
                # Prepare return distribution data for frontend chart
                returns_list = returns.tolist()
                
                return {
                    "ticker": ticker,
                    "avg_volatility": avg,
                    "std_volatility": std,
                    "returns_distribution": returns_list,
                    "price_data": {
                        "dates": [date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date) for date in df['date']],
                        "prices": df["close"].tolist()
                    },
                    "kde_params": {
                        "bandwidth": bandwidth,
                        "grid_size": grid_size
                    },
                    "date_range": {
                        "start": start_date,
                        "end": end_date,
                        "points": len(df)
                    },
                    "data_source": "YFinance"
                }
                
            except Exception as yf_error:
                logger.error(f"YFinance error for {ticker}: {str(yf_error)}")
                
                # Try MongoDB as fallback for cryptocurrency
                logger.info(f"YFinance failed for {ticker}, trying MongoDB as fallback")
                
                # Get data from MongoDB using the utility function
                df, message = await get_mongodb_data(ticker, start_date, end_date)
                
                if df is None:
                    logger.error(f"MongoDB fallback failed: {message}")
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to fetch data for {ticker} from any source: {str(yf_error)}. MongoDB: {message}"
                    )
                
                logger.info(f"Successfully fetched {len(df)} records from MongoDB for {ticker}")
                
                # Directly call volatility analysis with the DataFrame
                returns = volatility.calculate_returns(df)
                
                # Calculate statistics
                avg = float(returns.mean())
                std = float(returns.std())
                
                # Prepare return distribution data for frontend chart
                returns_list = returns.tolist()
                
                return {
                    "ticker": ticker,
                    "avg_volatility": avg,
                    "std_volatility": std,
                    "returns_distribution": returns_list,
                    "price_data": {
                        "dates": [date.strftime("%Y-%m-%d") for date in df["date"]],
                        "prices": df["close"].tolist()
                    },
                    "kde_params": {
                        "bandwidth": bandwidth,
                        "grid_size": grid_size
                    },
                    "date_range": {
                        "start": start_date,
                        "end": end_date,
                        "points": len(df)
                    },
                    "data_source": "MongoDB"
                }
        else:
            # For regular stocks, proceed with MongoDB/YFinance sync workflow
            # Sync with yfinance if requested
            sync_result = None
            if sync_yfinance:
                logger.info(f"Syncing {ticker} data with yfinance before volatility analysis")
                try:
                    sync_result = await YFinanceSync.sync_ticker_data(ticker, start_date, end_date)
                    logger.info(f"YFinance sync result: {sync_result}")
                    
                    # If sync updated data, we'll use the fresh data
                    if sync_result.get("mongodb_updated", False):
                        logger.info(f"MongoDB data updated from yfinance for {ticker}")
                except Exception as sync_error:
                    logger.warning(f"Error during yfinance sync: {str(sync_error)}. Proceeding with existing data.")
            
            # Call the analysis function without visualization
            try:
                df, returns = volatility.analyze_volatility(ticker, start_date, end_date)
                
                if df is None or returns is None:
                    raise ValueError("No data returned from volatility analysis")
                    
                logger.info(f"Volatility analysis complete, got {len(df)} data points")
            except Exception as analysis_error:
                # Try MongoDB directly if the analysis function failed
                logger.warning(f"Volatility analysis failed: {str(analysis_error)}. Trying MongoDB directly")
                mongodb_df, message = await get_mongodb_data(ticker, start_date, end_date)
                
                if mongodb_df is None:
                    logger.error(f"MongoDB fallback failed: {message}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to analyze volatility: {str(analysis_error)}. MongoDB fallback failed: {message}"
                    )
                    
                # Use MongoDB data for analysis
                logger.info(f"Using {len(mongodb_df)} MongoDB data points directly")
                df = mongodb_df
                returns = volatility.calculate_returns(df)
                
                if returns.empty:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to calculate returns from MongoDB data"
                    )
                    
                logger.info(f"Successfully analyzed volatility using MongoDB data for {ticker}")
            
            # Calculate statistics
            avg = float(returns.mean())
            std = float(returns.std())
            
            # Prepare return distribution data for frontend chart
            returns_list = returns.tolist()
            
            # Prepare price dates based on index type
            if isinstance(df.index, pd.DatetimeIndex):
                dates = [date.strftime("%Y-%m-%d") for date in df.index]
            elif 'date' in df.columns:
                dates = [date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date) 
                       for date in df["date"]]
            else:
                dates = [f"Point {i}" for i in range(len(df))]
            
            return {
                "ticker": ticker,
                "avg_volatility": avg,
                "std_volatility": std,
                "returns_distribution": returns_list,
                "price_data": {
                    "dates": dates,
                    "prices": df["close"].tolist()
                },
                "kde_params": {
                    "bandwidth": bandwidth,
                    "grid_size": grid_size
                },
                "date_range": {
                    "start": start_date,
                    "end": end_date,
                    "points": len(df)
                },
                "data_source": "MongoDB" if not sync_yfinance else 
                              "MongoDB+YFinance" if sync_result and sync_result.get("mongodb_updated", False) else 
                              "MongoDB (matched YFinance)"
            }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error analyzing volatility: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error analyzing volatility: {str(e)}")

@router.get("/next-day-stats/{ticker}")
async def get_next_day_stats(
    ticker: str,
    threshold: float = 0.10,
    look_ahead_days: int = 10,
    movement: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sync_yfinance: bool = True
):
    """
    Analyze next-day statistics after significant price moves.
    
    Parameters:
        ticker: Stock ticker symbol
        threshold: Price movement threshold (e.g., 0.10 for 10%)
        look_ahead_days: Number of days to look ahead
        movement: "up" for only up-moves, "down" for only down-moves, None for both
        start_date: Optional start date in format YYYY-MM-DD
        end_date: Optional end date in format YYYY-MM-DD
        sync_yfinance: If True, automatically sync with yfinance if data is available
    
    Returns:
        Next-day statistics analysis
    """
    try:
        # Validate threshold value
        if threshold <= 0:
            raise HTTPException(status_code=400, detail="Threshold must be greater than 0")
        
        # Cap very small thresholds to avoid potential calculation issues
        original_threshold = threshold
        if threshold < 0.005:  # Less than 0.5%
            logger.warning(f"Threshold {threshold} is very small, using minimum value of 0.005 (0.5%)")
            threshold = 0.005
            
        logger.info(f"Analyzing next-day stats for ticker: {ticker} with threshold={threshold}, sync_yfinance={sync_yfinance}")
        logger.info(f"Original date range: from {start_date or 'beginning'} to {end_date or 'end'}")
        
        # Validate and adjust date range
        if end_date:
            try:
                from datetime import datetime
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                today = datetime.now()
                if end_date_obj > today:
                    logger.warning(f"End date {end_date} is in the future, using today's date instead")
                    end_date = today.strftime("%Y-%m-%d")
            except ValueError:
                logger.warning(f"Invalid end date format: {end_date}")
                # Use a safe default
                end_date = datetime.now().strftime("%Y-%m-%d")
        
        if start_date and end_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                
                if start_date_obj > end_date_obj:
                    logger.warning(f"Start date {start_date} is after end date {end_date}, swapping")
                    start_date, end_date = end_date, start_date
            except ValueError:
                logger.warning("Could not parse one of the date values")
                # Use safe defaults
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        
        logger.info(f"Adjusted date range: from {start_date or 'beginning'} to {end_date or 'end'}")
        
        # If sync_yfinance is enabled, try to sync with yfinance first
        if sync_yfinance:
            try:
                sync_result = await YFinanceSync.sync_ticker_data(ticker, start_date, end_date)
                logger.info(f"Sync result for {ticker}: {sync_result}")
            except Exception as sync_error:
                logger.warning(f"Error during yfinance sync for {ticker}: {str(sync_error)}")
                # Continue with the available data
        
        # Call the analysis function with the requested look_ahead_days
        try:
            df, up, down = next_day_stats.analyze_next_day_stats(
                ticker, threshold, look_ahead_days, start_date, end_date, movement
            )
        except Exception as analysis_error:
            logger.error(f"Error in analyze_next_day_stats: {str(analysis_error)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to analyze next day stats: {str(analysis_error)}"
            )
        
        # Check if we got valid results
        if df is None:
            logger.warning(f"No data returned from analyze_next_day_stats for {ticker}")
            return {
                "ticker": ticker,
                "threshold": original_threshold,
                "look_ahead_days": look_ahead_days,
                "message": "No significant price moves found matching the criteria",
                "data": []
            }
            
        # Prepare results
        result = {
            "ticker": ticker,
            "threshold": original_threshold,  # Return the original requested threshold
            "look_ahead_days": look_ahead_days
        }
        
        # Process up moves if available
        if up is not None and not up.empty:
            try:
                up_stats = up["Forward_Return"].describe(percentiles=[0.25, 0.5, 0.75])
                
                # Convert 'date' column to string format if it's a datetime
                up_data = up.copy()
                if 'date' in up_data.columns:
                    if pd.api.types.is_datetime64_any_dtype(up_data['date']) or isinstance(up_data['date'].iloc[0], datetime):
                        up_data['date'] = up_data['date'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x))
                
                # Handle NaN values in statistics
                result["up_moves"] = {
                    "count": int(up_stats["count"]),
                    "mean": float(up_stats["mean"]) if not pd.isna(up_stats["mean"]) else None,
                    "std": float(up_stats["std"]) if not pd.isna(up_stats["std"]) else None,
                    "min": float(up_stats["min"]) if not pd.isna(up_stats["min"]) else None,
                    "q1": float(up_stats["25%"]) if not pd.isna(up_stats["25%"]) else None,
                    "median": float(up_stats["50%"]) if not pd.isna(up_stats["50%"]) else None,
                    "q3": float(up_stats["75%"]) if not pd.isna(up_stats["75%"]) else None,
                    "max": float(up_stats["max"]) if not pd.isna(up_stats["max"]) else None,
                    "data": up_data.to_dict(orient="records")
                }
            except Exception as stats_error:
                logger.error(f"Error calculating up move statistics: {str(stats_error)}")
                result["up_moves"] = {
                    "count": len(up),
                    "data": []
                }
        
        # Process down moves if available
        if down is not None and not down.empty:
            try:
                down_stats = down["Forward_Return"].describe(percentiles=[0.25, 0.5, 0.75])
                
                # Convert 'date' column to string format if it's a datetime
                down_data = down.copy()
                if 'date' in down_data.columns:
                    if pd.api.types.is_datetime64_any_dtype(down_data['date']) or isinstance(down_data['date'].iloc[0], datetime):
                        down_data['date'] = down_data['date'].apply(lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else str(x))
                
                # Handle NaN values in statistics
                result["down_moves"] = {
                    "count": int(down_stats["count"]),
                    "mean": float(down_stats["mean"]) if not pd.isna(down_stats["mean"]) else None,
                    "std": float(down_stats["std"]) if not pd.isna(down_stats["std"]) else None,
                    "min": float(down_stats["min"]) if not pd.isna(down_stats["min"]) else None,
                    "q1": float(down_stats["25%"]) if not pd.isna(down_stats["25%"]) else None,
                    "median": float(down_stats["50%"]) if not pd.isna(down_stats["50%"]) else None,
                    "q3": float(down_stats["75%"]) if not pd.isna(down_stats["75%"]) else None,
                    "max": float(down_stats["max"]) if not pd.isna(down_stats["max"]) else None,
                    "data": down_data.to_dict(orient="records")
                }
            except Exception as stats_error:
                logger.error(f"Error calculating down move statistics: {str(stats_error)}")
                result["down_moves"] = {
                    "count": len(down),
                    "data": []
                }
        
        # Ensure no NaN values in response
        result = replace_nan_with_none(result)
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error analyzing next-day stats: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error analyzing next-day stats: {str(e)}")

@router.get("/price-distribution/{ticker}")
async def get_price_distribution(
    ticker: str,
    method: str = "kde",
    bin_size: int = 5,
    smooth_window: int = 3,
    simulations: int = 10000,
    horizon_days: int = 1,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    bw_method: float = 0.15,
    grid_size: int = 500,
    include_volume_indicators: bool = False
):
    """
    Calculate price distribution for a stock or cryptocurrency.
    
    Parameters:
        ticker: Stock ticker symbol or cryptocurrency (e.g., BTC-USD)
        method: "hist", "kde", or "mc_kde"
        bin_size: Bin size for histogram
        smooth_window: Smoothing window size
        simulations: Number of simulations for Monte Carlo
        horizon_days: Horizon days for Monte Carlo
        start_date: Optional start date in format YYYY-MM-DD
        end_date: Optional end date in format YYYY-MM-DD
        bw_method: Bandwidth for KDE (0.01-1.0)
        grid_size: Number of points in KDE grid (100-1000)
        include_volume_indicators: Whether to include volume indicators (TVC, VA, VV)
    
    Returns:
        Price distribution data
    """
    try:
        logger.info(f"Calculating price distribution for ticker: {ticker} using method: {method}")
        
        # Check if it's a cryptocurrency (common formats: BTC-USD, ETH-USD, etc.)
        is_crypto = "-" in ticker or ticker.endswith("USDT") or ticker.endswith("USD")
        if is_crypto:
            logger.info(f"Detected cryptocurrency: {ticker}")
        
        # Validate and fix dates
        try:
            today = datetime.now()
            
            # End date validation
            if end_date:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                if end_date_obj > today:
                    logger.warning(f"End date {end_date} is in the future, using today's date instead")
                    end_date = today.strftime("%Y-%m-%d")
            else:
                # Default to today if not provided
                end_date = today.strftime("%Y-%m-%d")
            
            # Start date validation
            if start_date:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                # Check if start date is after end date
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                if start_date_obj > end_date_obj:
                    logger.warning(f"Start date {start_date} is after end date {end_date}, swapping")
                    start_date, end_date = end_date, start_date
            else:
                # Default to 1 year ago if not provided
                start_date = (today - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
                
            logger.info(f"Using adjusted date range: {start_date} to {end_date}")
                
        except ValueError as date_error:
            logger.error(f"Date format error: {str(date_error)}")
            raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD.")
        
        # For cryptocurrencies, use yfinance directly
        if is_crypto:
            logger.info(f"Using YFinance directly for cryptocurrency price distribution: {ticker}")
            
            try:
                import yfinance as yf
                
                # Get data from yfinance
                ticker_data = yf.Ticker(ticker)
                
                # Get historical data
                hist = ticker_data.history(start=start_date, end=end_date)
                
                if hist.empty:
                    logger.warning(f"YFinance error for {ticker}: No historical data available")
                    logger.info(f"Trying MongoDB as fallback for cryptocurrency: {ticker}")
                    
                    # Try to get data from MongoDB
                    df, message = await get_mongodb_data(ticker, start_date, end_date)
                    
                    if df is None:
                        logger.error(f"MongoDB fallback failed: {message}")
                        raise HTTPException(
                            status_code=500, 
                            detail=f"Failed to fetch data for {ticker} from any source: {str(yf_error)}. MongoDB: {message}"
                        )
                    
                    logger.info(f"Successfully fetched data from MongoDB for {ticker}")
                    
                    # Extract closing prices for distribution analysis
                    prices = df["close"].values
                    
                    # Compute distribution
                    x, y = probability_distribution.compute_distribution(
                        prices, method, bin_size, smooth_window, simulations, horizon_days,
                        bw_method=bw_method, grid_size=grid_size
                    )
                    
                    result = {
                        "ticker": ticker,
                        "method": method,
                        "distribution": {
                            "x": x.tolist(),
                            "y": y.tolist()
                        },
                        "stats": {
                            "min": float(np.min(prices)),
                            "max": float(np.max(prices)),
                            "mean": float(np.mean(prices)),
                            "median": float(np.median(prices)),
                            "std": float(np.std(prices))
                        },
                        "data_source": "MongoDB"
                    }
                    
                    # If volume indicators requested, calculate and add them
                    if include_volume_indicators and 'volume' in df.columns:
                        # Calculate TVC (Total Volume Correlation)
                        tvc = df['volume'].corr(df['close']) if len(df) > 1 else 0
                        
                        # Calculate VA (Volume Analysis) - ratio of average volume to current volume
                        recent_volume = df['volume'].iloc[-20:].mean() if len(df) >= 20 else df['volume'].mean()
                        total_volume_avg = df['volume'].mean()
                        va = recent_volume / total_volume_avg if total_volume_avg > 0 else 1
                        
                        # Calculate VV (Volume Volatility) - coefficient of variation of volume
                        vv = df['volume'].std() / df['volume'].mean() if df['volume'].mean() > 0 else 0
                        
                        # Add to results
                        result["stats"]["tvc"] = float(tvc)
                        result["stats"]["va"] = float(va)
                        result["stats"]["vv"] = float(vv)
                    
                    return result
                    
                # Extract closing prices for distribution analysis
                prices = hist['Close'].values
                
                # Compute distribution using the same logic as the regular function
                x, y = probability_distribution.compute_distribution(
                    prices, method, bin_size, smooth_window, simulations, horizon_days,
                    bw_method=bw_method, grid_size=grid_size
                )
                
                result = {
                    "ticker": ticker,
                    "method": method,
                    "distribution": {
                        "x": x.tolist(),
                        "y": y.tolist()
                    },
                    "stats": {
                        "min": float(np.min(prices)),
                        "max": float(np.max(prices)),
                        "mean": float(np.mean(prices)),
                        "median": float(np.median(prices)),
                        "std": float(np.std(prices))
                    },
                    "data_source": "YFinance"
                }
                
                # If volume indicators requested, calculate and add them
                if include_volume_indicators and 'Volume' in hist.columns:
                    # Create DataFrame in format needed for calculations
                    df = pd.DataFrame({
                        'volume': hist['Volume'],
                        'close': hist['Close']
                    })
                    
                    # Calculate TVC (Total Volume Correlation)
                    tvc = df['volume'].corr(df['close']) if len(df) > 1 else 0
                    
                    # Calculate VA (Volume Analysis) - ratio of average volume to current volume
                    recent_volume = df['volume'].iloc[-20:].mean() if len(df) >= 20 else df['volume'].mean()
                    total_volume_avg = df['volume'].mean()
                    va = recent_volume / total_volume_avg if total_volume_avg > 0 else 1
                    
                    # Calculate VV (Volume Volatility) - coefficient of variation of volume
                    vv = df['volume'].std() / df['volume'].mean() if df['volume'].mean() > 0 else 0
                    
                    # Add to results
                    result["stats"]["tvc"] = float(tvc)
                    result["stats"]["va"] = float(va)
                    result["stats"]["vv"] = float(vv)
                
                return result
                
            except Exception as yf_error:
                logger.error(f"YFinance error for {ticker}: {str(yf_error)}")
                
                # Try MongoDB as a fallback
                logger.info(f"Trying MongoDB as fallback for {ticker}")
                df, message = await get_mongodb_data(ticker, start_date, end_date)
                
                if df is None:
                    logger.error(f"MongoDB fallback failed: {message}")
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to fetch data for {ticker} from any source: {str(yf_error)}. MongoDB: {message}"
                    )
                
                try:
                    # Extract closing prices for distribution analysis
                    logger.info(f"Processing {len(df)} MongoDB records for price distribution")
                    
                    # Ensure close column is numeric
                    df["close"] = pd.to_numeric(df["close"], errors='coerce')
                    df = df.dropna(subset=["close"])
                    
                    if len(df) == 0:
                        raise ValueError(f"No valid close prices in MongoDB data for {ticker}")
                        
                    # Get prices from the clean dataframe
                    prices = df["close"].values
                    
                    # Compute distribution
                    x, y = probability_distribution.compute_distribution(
                        prices, method, bin_size, smooth_window, simulations, horizon_days,
                        bw_method=bw_method, grid_size=grid_size
                    )
                    
                    result = {
                        "ticker": ticker,
                        "method": method,
                        "distribution": {
                            "x": x.tolist(),
                            "y": y.tolist()
                        },
                        "stats": {
                            "min": float(np.min(prices)),
                            "max": float(np.max(prices)),
                            "mean": float(np.mean(prices)),
                            "median": float(np.median(prices)),
                            "std": float(np.std(prices))
                        },
                        "data_source": "MongoDB"
                    }
                    
                    # Find latest price for current_price
                    latest_price = df["close"].iloc[-1] if len(df) > 0 else None
                    if latest_price:
                        result["current_price"] = float(latest_price)
                    
                    # If volume indicators requested, calculate and add them
                    if include_volume_indicators and 'volume' in df.columns:
                        # Calculate TVC (Total Volume Correlation)
                        tvc = df['volume'].corr(df['close']) if len(df) > 1 else 0
                        
                        # Calculate VA (Volume Analysis) - ratio of average volume to current volume
                        recent_volume = df['volume'].iloc[-20:].mean() if len(df) >= 20 else df['volume'].mean()
                        total_volume_avg = df['volume'].mean()
                        va = recent_volume / total_volume_avg if total_volume_avg > 0 else 1
                        
                        # Calculate VV (Volume Volatility) - coefficient of variation of volume
                        vv = df['volume'].std() / df['volume'].mean() if df['volume'].mean() > 0 else 0
                        
                        # Add to results
                        result["stats"]["tvc"] = float(tvc)
                        result["stats"]["va"] = float(va)
                        result["stats"]["vv"] = float(vv)
                    
                    return result
                    
                except Exception as processing_error:
                    logger.error(f"Error processing MongoDB data for {ticker}: {str(processing_error)}")
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Error processing MongoDB data: {str(processing_error)}"
                    )
        else:
            # For regular stocks, use the standard MongoDB approach
            # Load price data
            prices = probability_distribution.load_prices_from_db(ticker, start_date, end_date)
            
            # Compute distribution without plotting
            x, y = probability_distribution.compute_distribution(
                prices, method, bin_size, smooth_window, simulations, horizon_days,
                bw_method=bw_method, grid_size=grid_size
            )
            
            result = {
                "ticker": ticker,
                "method": method,
                "distribution": {
                    "x": x.tolist(),
                    "y": y.tolist()
                },
                "stats": {
                    "min": float(np.min(prices)),
                    "max": float(np.max(prices)),
                    "mean": float(np.mean(prices)),
                    "median": float(np.median(prices)),
                    "std": float(np.std(prices))
                }
            }
            
            # If volume indicators requested, calculate and add them
            if include_volume_indicators:
                # Get the DataFrame with volume data
                df = read_and_prepare_data(ticker, date_from=start_date, date_to=end_date, calc_returns=True)
                
                if df is not None and 'volume' in df.columns and 'close' in df.columns:
                    # Calculate TVC (Total Volume Correlation)
                    tvc = df['volume'].corr(df['close']) if len(df) > 1 else 0
                    
                    # Calculate VA (Volume Analysis) - ratio of average volume to current volume
                    recent_volume = df['volume'].iloc[-20:].mean() if len(df) >= 20 else df['volume'].mean()
                    total_volume_avg = df['volume'].mean()
                    va = recent_volume / total_volume_avg if total_volume_avg > 0 else 1
                    
                    # Calculate VV (Volume Volatility) - coefficient of variation of volume
                    vv = df['volume'].std() / df['volume'].mean() if df['volume'].mean() > 0 else 0
                    
                    # Add to results
                    result["stats"]["tvc"] = float(tvc)
                    result["stats"]["va"] = float(va)
                    result["stats"]["vv"] = float(vv)
            
            return result
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error calculating price distribution: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error calculating price distribution: {str(e)}") 

@router.get("/sync-yfinance/{ticker}")
async def sync_ticker_with_yfinance(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    force_update: bool = False
):
    """
    Sync ticker data between MongoDB and yfinance.
    If data is different or force_update is True, update MongoDB with yfinance data.
    
    Parameters:
        ticker: Stock ticker symbol
        start_date: Optional start date in format YYYY-MM-DD
        end_date: Optional end date in format YYYY-MM-DD
        force_update: If True, update MongoDB even if data matches
        
    Returns:
        Result of the sync operation
    """
    try:
        logger.info(f"Syncing {ticker} data with yfinance")
        
        # Perform the sync operation
        result = await YFinanceSync.sync_ticker_data(ticker, start_date, end_date)
        
        # If force update is set and we have yfinance data
        if force_update and not result.get("data_matched", True):
            # Re-fetch yfinance data and update MongoDB
            yf_df = await YFinanceSync.get_yfinance_data(ticker, start_date, end_date)
            if not yf_df.empty:
                updated = await YFinanceSync.update_mongodb(ticker, yf_df)
                result["force_updated"] = updated
                result["mongodb_updated"] = updated
        
        return result
        
    except Exception as e:
        logger.error(f"Error syncing ticker data with yfinance: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error syncing ticker data: {str(e)}") 

@router.post("/backtest-strategy")
async def backtest_strategy(
    backtest_params: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Run a backtest for a trading strategy with the specified parameters.
    
    Parameters:
        backtest_params: Dictionary containing backtest parameters
            - ticker: Stock ticker symbol
            - start_date: Start date in format YYYY-MM-DD
            - end_date: End date in format YYYY-MM-DD
            - strategy_type: Type of strategy to backtest
            - strategy_params: Strategy-specific parameters
            - initial_capital: Initial capital amount
            - position_size: Position size percentage
            - stop_loss: Stop loss percentage
            - take_profit: Take profit percentage
    
    Returns:
        Backtest results including performance metrics and trade list
    """
    try:
        logger.info(f"Backtesting strategy for user: {current_user.get('username')}")
        logger.info(f"Backtest parameters: {backtest_params}")
        
        # Validate required parameters
        required_fields = ['ticker', 'start_date', 'end_date', 'strategy_type']
        for field in required_fields:
            if field not in backtest_params:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Extract parameters
        ticker = backtest_params.get('ticker').upper()
        start_date = backtest_params.get('start_date')
        end_date = backtest_params.get('end_date')
        strategy_type = backtest_params.get('strategy_type')
        strategy_params = backtest_params.get('strategy_params', {})
        initial_capital = float(backtest_params.get('initial_capital', 10000))
        position_size = float(backtest_params.get('position_size', 100)) / 100
        stop_loss = float(backtest_params.get('stop_loss', 2)) / 100
        take_profit = float(backtest_params.get('take_profit', 5)) / 100
        
        # Fetch historical data for the ticker
        try:
            # First try to sync with yfinance if needed
            if backtest_params.get('auto_sync', True):
                sync_result = await YFinanceSync.sync_ticker_data(ticker, start_date, end_date)
                logger.info(f"Sync result for {ticker}: {sync_result}")
            
            # Get historical data for backtesting
            market_db = db.client["market"]
            collection = market_db["prices"]
            
            # Build MongoDB query
            query = {"ticker": ticker}
            if start_date:
                try:
                    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                    query["date"] = {"$gte": start_datetime}
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid start_date format: {start_date}")
            
            if end_date:
                try:
                    end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                    if "date" in query:
                        query["date"]["$lte"] = end_datetime
                    else:
                        query["date"] = {"$lte": end_datetime}
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid end_date format: {end_date}")
            
            # Execute query
            cursor = collection.find(query).sort("date", 1)
            historical_data = list(cursor)
            
            if not historical_data:
                raise HTTPException(status_code=404, detail=f"No historical data found for ticker: {ticker}")
            
            logger.info(f"Found {len(historical_data)} data points for {ticker}")
            
            # Convert to pandas DataFrame for easier analysis
            df = pd.DataFrame(historical_data)
            
            # Convert ObjectId to string for serialization
            df['_id'] = df['_id'].astype(str)
            
            # Convert date to string format for serialization
            df['date_str'] = df['date'].dt.strftime('%Y-%m-%d')
            
            # For now, return a mock backtest result
            # In a real implementation, we would run the actual strategy logic here
            
            # Mock results for demo purposes
            trades = []
            equity_curve = []
            
            # Generate mock trades based on the real dates we have
            dates = df['date'].tolist()
            if len(dates) > 10:  # Ensure we have enough data points
                # Select random dates for trades
                trade_dates = random.sample(dates, min(20, len(dates) // 5))
                
                # Sort the selected dates
                trade_dates.sort()
                
                # Generate mock trades
                current_position = None
                capital = initial_capital
                
                for i, trade_date in enumerate(trade_dates):
                    date_idx = df[df['date'] == trade_date].index[0]
                    price = df.loc[date_idx, 'close']
                    
                    # Mock trade logic
                    if i % 2 == 0:  # Buy on even indices
                        shares = int((capital * position_size) / price)
                        trades.append({
                            "date": trade_date.strftime('%Y-%m-%d'),
                            "type": "BUY",
                            "price": float(price),
                            "shares": shares,
                            "cost": float(shares * price),
                            "profit": 0
                        })
                        current_position = {
                            "entry_date": trade_date,
                            "entry_price": price,
                            "shares": shares
                        }
                    elif current_position:  # Sell on odd indices if we have a position
                        entry_price = current_position["entry_price"]
                        shares = current_position["shares"]
                        profit = float(shares * (price - entry_price))
                        trades.append({
                            "date": trade_date.strftime('%Y-%m-%d'),
                            "type": "SELL",
                            "price": float(price),
                            "shares": shares,
                            "cost": 0,
                            "profit": profit,
                            "returnPct": float(100 * (price - entry_price) / entry_price)
                        })
                        capital += profit
                        current_position = None
            
            # Generate equity curve based on trades
            current_capital = initial_capital
            for date in sorted(df['date']):
                # Find any trades on this date
                date_str = date.strftime('%Y-%m-%d')
                day_trades = [t for t in trades if t["date"] == date_str]
                
                # Update capital based on trades
                for trade in day_trades:
                    if "profit" in trade:
                        current_capital += trade["profit"]
                
                # Add point to equity curve
                equity_curve.append({
                    "date": date_str,
                    "value": float(current_capital)
                })
            
            # Calculate performance metrics
            win_trades = [t for t in trades if t.get("profit", 0) > 0]
            lose_trades = [t for t in trades if t.get("profit", 0) < 0]
            
            total_trades = len(win_trades) + len(lose_trades)
            win_rate = (len(win_trades) / total_trades) * 100 if total_trades > 0 else 0
            
            total_profit = sum(t.get("profit", 0) for t in win_trades)
            total_loss = sum(t.get("profit", 0) for t in lose_trades)
            profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')
            
            # Calculate max drawdown
            max_drawdown = 0
            peak = initial_capital
            for point in equity_curve:
                if point["value"] > peak:
                    peak = point["value"]
                else:
                    drawdown = (peak - point["value"]) / peak * 100
                    max_drawdown = max(max_drawdown, drawdown)
            
            # Return backtest results
            return {
                "success": True,
                "ticker": ticker,
                "strategy": strategy_type,
                "totalReturn": float(((current_capital - initial_capital) / initial_capital) * 100),
                "initialCapital": float(initial_capital),
                "finalCapital": float(current_capital),
                "winRate": float(win_rate),
                "profitFactor": float(profit_factor),
                "maxDrawdown": float(max_drawdown),
                "sharpeRatio": float(random.uniform(0.5, 2.5)),  # Mock Sharpe ratio
                "totalTrades": total_trades,
                "equityCurve": equity_curve,
                "trades": trades
            }
            
        except Exception as data_error:
            logger.error(f"Error getting historical data: {data_error}")
            raise HTTPException(status_code=500, detail=f"Error getting historical data: {str(data_error)}")
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error backtesting strategy: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error backtesting strategy: {str(e)}") 

@router.get("/current-price/{ticker}")
async def get_current_price(
    ticker: str
):
    """
    Get the current price for a ticker symbol using Finnhub API with YFinance fallback
    and MongoDB as a final fallback.
    
    Parameters:
        ticker: Stock ticker symbol or cryptocurrency (e.g., BTC-USD)
    
    Returns:
        Current price data for the ticker
    """
    try:
        logger.info(f"Fetching current price for ticker: {ticker}")
        
        # Check if it's a cryptocurrency (common formats: BTC-USD, ETH-USD, etc.)
        is_crypto = "-" in ticker or ticker.endswith("USDT") or ticker.endswith("USD")
        if is_crypto:
            logger.info(f"Detected cryptocurrency: {ticker}")
        
        # First try Finnhub API
        try:
            logger.info(f"Trying Finnhub API for {ticker}")
            
            # Convert crypto format if needed for Finnhub (e.g., BTC-USD to BTCUSD)
            finnhub_symbol = ticker
            if is_crypto and "-" in ticker:
                finnhub_symbol = ticker.replace("-", "")
                logger.info(f"Converted symbol for Finnhub: {ticker} -> {finnhub_symbol}")
            
            # Build Finnhub API URL
            url = f"https://finnhub.io/api/v1/quote?symbol={finnhub_symbol}&token={FINNHUB_API_KEY}"
            
            # Make the API request
            response = requests.get(url, timeout=5)  # Add timeout
            
            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                
                # Check if we have valid data
                if 'c' in data and data['c'] > 0:
                    # Extract price data from Finnhub response
                    current_price = data['c']  # Current price
                    prev_close = data['pc']  # Previous close price
                    price_change = data['c'] - data['pc']  # Change
                    percent_change = price_change / prev_close * 100 if prev_close else 0
                    
                    logger.info(f"Successfully got price from Finnhub for {ticker}: ${current_price}")
                    
                    return {
                        "ticker": ticker,
                        "current_price": float(current_price),
                        "market_price": float(current_price),
                        "previous_close": float(prev_close) if prev_close else None,
                        "change": float(price_change),
                        "percent_change": float(percent_change),
                        "timestamp": datetime.now().isoformat(),
                        "source": "finnhub"
                    }
                else:
                    logger.warning(f"Invalid data from Finnhub for {ticker}, falling back to YFinance")
            else:
                logger.warning(f"Finnhub API error: {response.status_code}, falling back to YFinance")
                
        except Exception as finnhub_error:
            logger.warning(f"Finnhub API error for {ticker}: {str(finnhub_error)}, falling back to YFinance")
        
        # If Finnhub fails or returns invalid data, try YFinance as backup
        logger.info(f"Trying YFinance for {ticker}")
        
        try:
            import yfinance as yf
            
            # Get data from yfinance
            ticker_data = yf.Ticker(ticker)
            
            # Try to get latest price data
            try:
                # First try fast info which works for most tickers
                info = ticker_data.fast_info
                current_price = info.get('lastPrice') or info.get('regularMarketPrice')
                prev_close = info.get('previousClose')
                
                if not current_price:
                    # Try slower method
                    hist = ticker_data.history(period="2d")
                    if not hist.empty:
                        # Get last row for current price
                        current_price = hist['Close'].iloc[-1]
                        # Get previous close if available
                        prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else None
            
                # Calculate change
                if current_price and prev_close:
                    price_change = current_price - prev_close
                    percent_change = (price_change / prev_close) * 100
                else:
                    price_change = 0
                    percent_change = 0
                
                logger.info(f"Successfully got price from YFinance for {ticker}: ${current_price}")
                
                return {
                    "ticker": ticker,
                    "current_price": float(current_price),
                    "market_price": float(current_price),
                    "previous_close": float(prev_close) if prev_close else None,
                    "change": float(price_change),
                    "percent_change": float(percent_change),
                    "timestamp": datetime.now().isoformat(),
                    "source": "yfinance"
                }
            except Exception as yf_data_error:
                logger.error(f"YFinance data error for {ticker}: {str(yf_data_error)}")
                logger.info(f"Both Finnhub and YFinance failed, trying MongoDB as fallback for {ticker}")
                
                # Try MongoDB as a final fallback
                mongodb_data, message = await get_mongodb_data(ticker, most_recent_only=True)
                
                if mongodb_data:
                    logger.info(f"Successfully got price from MongoDB for {ticker}")
                    return mongodb_data
                else:
                    logger.error(f"MongoDB fallback failed: {message}")
                raise HTTPException(
                    status_code=404, 
                        detail=f"Could not fetch price data for {ticker} from any source: {str(yf_data_error)}. MongoDB: {message}"
                )
                
        except Exception as yf_error:
            logger.error(f"YFinance error for {ticker}: {str(yf_error)}")
            
            # Try MongoDB as a final fallback
            mongodb_data, message = await get_mongodb_data(ticker, most_recent_only=True)
            
            if mongodb_data:
                logger.info(f"Successfully got price from MongoDB for {ticker}")
                return mongodb_data
            else:
                logger.error(f"MongoDB fallback failed: {message}")
            raise HTTPException(
                status_code=404, 
                detail=f"Could not fetch price data for {ticker} from any source. The symbol may be invalid."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching current price for {ticker}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error fetching current price: {str(e)}") 

class CorrelationMatrixRequest(BaseModel):
    tickers: List[str]
    lookback_days: int

class CorrelationMatrixResponse(BaseModel):
    matrix: List[List[float]]
    tickers: List[str]

@router.post("/stocks/correlation-matrix", response_model=CorrelationMatrixResponse)
async def get_correlation_matrix(request: CorrelationMatrixRequest):
    try:
        matrix, tickers = compute_correlation_matrix(request.tickers, request.lookback_days)
        # Convert numpy array to list for JSON serialization
        return CorrelationMatrixResponse(matrix=matrix.tolist(), tickers=tickers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))