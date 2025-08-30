import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any, Tuple
from pymongo.database import Database
from pymongo import UpdateOne
from ..database import db

# Configure logging
logger = logging.getLogger(__name__)

# Add a console handler to make debug output visible
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('[YFinance] %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

class YFinanceSync:
    """
    Service to synchronize stock data between yfinance and MongoDB.
    Compares MongoDB data with yfinance data and updates MongoDB when needed.
    """
    
    @staticmethod
    async def get_yfinance_data(ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch ticker data from yfinance.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date in format YYYY-MM-DD
            end_date: End date in format YYYY-MM-DD
            
        Returns:
            DataFrame containing the stock data
        """
        try:
            logger.info(f"Fetching {ticker} data from yfinance (start: {start_date}, end: {end_date})")
            
            # Validate dates to ensure they're not in the future
            now = datetime.now()
            
            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    if end_dt > now:
                        logger.warning(f"End date {end_date} is in the future, using yesterday's date instead")
                        end_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
                except ValueError:
                    logger.warning(f"Invalid end date format: {end_date}, using yesterday's date instead")
                    end_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else now
                    if start_dt > end_dt:
                        logger.warning(f"Start date {start_date} is after end date {end_date}, swapping")
                        start_date, end_date = end_date, start_date
                except ValueError:
                    logger.warning(f"Invalid start date format: {start_date}, using one year before end date")
                    if end_date:
                        try:
                            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                            start_date = (end_dt - timedelta(days=365)).strftime("%Y-%m-%d")
                        except ValueError:
                            start_date = (now - timedelta(days=365)).strftime("%Y-%m-%d")
                    else:
                        start_date = (now - timedelta(days=365)).strftime("%Y-%m-%d")
            
            # Use fixed historical dates for testing if none provided
            if not start_date:
                start_date = "2020-01-01"
            if not end_date:
                end_date = "2021-01-01"
                
            logger.info(f"Using date range for yfinance: {start_date} to {end_date}")
            
            # Try a simpler approach first - get the ticker info
            try:
                ticker_obj = yf.Ticker(ticker)
                # Just try to access the info to see if basic connectivity works
                info = ticker_obj.info
                logger.info(f"Successfully connected to yfinance API for {ticker}")
                
                # Now try to get history directly through the ticker object
                ticker_data = ticker_obj.history(
                    start=start_date,
                    end=end_date,
                    period="max"  # This ensures we get as much data as possible
                    # Note: Removed progress parameter which isn't supported in newer versions
                )
            except Exception as ticker_error:
                logger.warning(f"Error using Ticker approach: {ticker_error}. Trying download method.")
                # Fall back to the download method with settings from your working script
                ticker_data = yf.download(
                    ticker,
                    start=start_date,
                    end=end_date,
                    interval="1d",      # Force daily bars
                    auto_adjust=False,  # Don't auto adjust
                    progress=False      # Disable progress bar
                )
            
            if ticker_data.empty:
                logger.warning(f"No data found on yfinance for ticker: {ticker}")
                return pd.DataFrame()
            
            # Reset index to make Date a column
            ticker_data = ticker_data.reset_index()
            
            # Handle potential MultiIndex columns
            if isinstance(ticker_data.columns, pd.MultiIndex):
                ticker_data.columns = [col[0] if isinstance(col, tuple) else col for col in ticker_data.columns]
            
            # Rename columns to match MongoDB schema
            ticker_data = ticker_data.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Ensure date is datetime
            ticker_data['date'] = pd.to_datetime(ticker_data['date'])
            
            # Convert to date objects
            ticker_data['date'] = ticker_data['date'].dt.date
            
            # Add ticker column
            ticker_data['ticker'] = ticker.upper()
            
            logger.info(f"Successfully fetched {len(ticker_data)} records from yfinance for {ticker}")
            return ticker_data
        
        except Exception as e:
            logger.error(f"Error fetching yfinance data for {ticker}: {str(e)}")
            return pd.DataFrame()

    @staticmethod
    async def get_mongodb_data(ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch ticker data from MongoDB.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date in format YYYY-MM-DD
            end_date: End date in format YYYY-MM-DD
            
        Returns:
            DataFrame containing the stock data
        """
        try:
            logger.info(f"Fetching {ticker} data from MongoDB")
            
            # Build MongoDB query
            query = {"ticker": ticker.upper()}
            
            # Add date filtering if provided
            if start_date:
                try:
                    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
                    query["date"] = {"$gte": start_datetime}
                except ValueError:
                    logger.error(f"Invalid start_date format: {start_date}")
                    return pd.DataFrame()
                    
            if end_date:
                try:
                    end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                    if "date" in query:
                        query["date"]["$lte"] = end_datetime
                    else:
                        query["date"] = {"$lte": end_datetime}
                except ValueError:
                    logger.error(f"Invalid end_date format: {end_date}")
                    return pd.DataFrame()
            
            # Execute query on prices collection
            market_db = db.client["market"]
            cursor = market_db["prices"].find(query).sort("date", 1)
            
            # Convert to DataFrame
            price_data = list(cursor)
            
            if not price_data:
                logger.warning(f"No price data found in MongoDB for ticker: {ticker}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(price_data)
            
            # Ensure date column is datetime.date for comparison
            if 'date' in df.columns and not df.empty:
                df['date'] = pd.to_datetime(df['date']).dt.date
            
            logger.info(f"Successfully fetched {len(df)} records from MongoDB for {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching MongoDB data for {ticker}: {str(e)}")
            return pd.DataFrame()

    @staticmethod
    async def compare_data(mongo_df: pd.DataFrame, yf_df: pd.DataFrame) -> Tuple[bool, pd.DataFrame]:
        """
        Compare MongoDB data with yfinance data.
        
        Args:
            mongo_df: DataFrame with MongoDB data
            yf_df: DataFrame with yfinance data
            
        Returns:
            Tuple of (are_identical, merged_df)
            - are_identical: True if data matches, False otherwise
            - merged_df: DataFrame with merged data (used when updating MongoDB)
        """
        if mongo_df.empty and yf_df.empty:
            logger.warning("Both MongoDB and yfinance data are empty, nothing to compare")
            return True, pd.DataFrame()
        
        if mongo_df.empty:
            logger.info("MongoDB data is empty, yfinance data will be used")
            return False, yf_df
        
        if yf_df.empty:
            logger.info("yfinance data is empty, MongoDB data will be used")
            return True, mongo_df
        
        # Ensure both dataframes have the same columns for comparison
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'ticker']
        
        # Check if required columns exist in both dataframes
        mongo_has_cols = all(col in mongo_df.columns for col in required_columns)
        yf_has_cols = all(col in yf_df.columns for col in required_columns)
        
        if not mongo_has_cols or not yf_has_cols:
            logger.warning("Missing required columns in one of the dataframes")
            missing_mongo = [col for col in required_columns if col not in mongo_df.columns]
            missing_yf = [col for col in required_columns if col not in yf_df.columns]
            
            if missing_mongo:
                logger.warning(f"MongoDB data missing columns: {missing_mongo}")
            if missing_yf:
                logger.warning(f"yfinance data missing columns: {missing_yf}")
                
            # If MongoDB has all columns but yfinance doesn't, use MongoDB
            if mongo_has_cols and not yf_has_cols:
                return True, mongo_df
            # If yfinance has all columns but MongoDB doesn't, use yfinance
            if not mongo_has_cols and yf_has_cols:
                return False, yf_df
            # If both are missing columns, use whatever is available
            return True, mongo_df
        
        # Set index to date for comparison
        mongo_compare = mongo_df.set_index('date')
        yf_compare = yf_df.set_index('date')
        
        # Find common dates
        common_dates = mongo_compare.index.intersection(yf_compare.index)
        
        if len(common_dates) == 0:
            logger.info("No common dates between MongoDB and yfinance data")
            # Merge the two dataframes
            merged_df = pd.concat([mongo_df, yf_df]).drop_duplicates(subset=['date']).reset_index(drop=True)
            return False, merged_df
        
        # Compare the values for common dates
        mongo_subset = mongo_compare.loc[common_dates, ['open', 'high', 'low', 'close', 'volume']]
        yf_subset = yf_compare.loc[common_dates, ['open', 'high', 'low', 'close', 'volume']]
        
        # Check for significant differences (within reasonable precision)
        # We use a small epsilon for floating point comparison
        price_epsilon = 0.01  # 1 cent difference allowed
        volume_epsilon = 100  # 100 shares difference allowed
        
        price_cols = ['open', 'high', 'low', 'close']
        
        # Check price columns
        price_diff = (mongo_subset[price_cols] - yf_subset[price_cols]).abs() > price_epsilon
        has_price_diff = price_diff.any().any()
        
        # Check volume column
        volume_diff = (mongo_subset['volume'] - yf_subset['volume']).abs() > volume_epsilon
        has_volume_diff = volume_diff.any()
        
        if has_price_diff or has_volume_diff:
            logger.info("Found differences between MongoDB and yfinance data")
            diff_count = price_diff.sum().sum() + volume_diff.sum()
            logger.info(f"Number of differences: {diff_count}")
            
            # Merge the data, preferring yfinance
            # Remove common dates from MongoDB data
            mongo_unique = mongo_df[~mongo_df['date'].isin(common_dates)]
            
            # Combine with all yfinance data
            merged_df = pd.concat([mongo_unique, yf_df]).sort_values('date').reset_index(drop=True)
            
            return False, merged_df
        
        # If no differences found, check if yfinance has additional dates
        all_mongo_dates = set(mongo_df['date'])
        all_yf_dates = set(yf_df['date'])
        
        additional_dates = all_yf_dates - all_mongo_dates
        if additional_dates:
            logger.info(f"yfinance has {len(additional_dates)} additional dates not in MongoDB")
            # Add the additional dates from yfinance
            additional_rows = yf_df[yf_df['date'].isin(additional_dates)]
            merged_df = pd.concat([mongo_df, additional_rows]).sort_values('date').reset_index(drop=True)
            return False, merged_df
        
        logger.info("MongoDB and yfinance data match")
        return True, mongo_df

    @staticmethod
    async def update_mongodb(ticker: str, df: pd.DataFrame) -> bool:
        """
        Update MongoDB with new data using bulk operations and proper date handling.
        
        Args:
            ticker: Stock ticker symbol
            df: DataFrame with updated data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if df.empty:
                logger.warning(f"Cannot update MongoDB with empty data for ticker {ticker}")
                return False
            
            logger.info(f"Updating MongoDB with {len(df)} records for {ticker}")
            
            # Create a copy to avoid modifying the original DataFrame
            df_copy = df.copy()
            
            # Ensure ticker is uppercase
            ticker = ticker.upper()
            
            # Get MongoDB collection
            market_db = db.client["market"]
            collection = market_db["prices"]
            
            # Prepare bulk operations with proper datetime handling
            bulk_ops = []
            batch_size = 500  # Process in batches to avoid memory issues
            
            for _, row in df_copy.iterrows():
                # Convert date to datetime object for MongoDB
                date_val = row['date']
                if isinstance(date_val, datetime):
                    dt = date_val
                elif isinstance(date_val, pd.Timestamp):
                    dt = date_val.to_pydatetime()
                else:
                    dt = pd.Timestamp(date_val).to_pydatetime()
                
                # Create a custom ID combining ticker and date for deduplication
                doc_id = f"{ticker}_{dt.strftime('%Y-%m-%d')}"
                
                # Create document with proper data types
                doc = {
                    "_id": doc_id,
                    "ticker": ticker,
                    "date": dt,
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": int(row['volume'])
                }
                
                # Add operation to bulk write
                bulk_ops.append(
                    UpdateOne(
                        {"_id": doc_id},  # Query by the custom ID
                        {"$set": doc},    # Update or insert the document
                        upsert=True       # Create if doesn't exist
                    )
                )
                
                # Execute batch if we've reached batch_size
                if len(bulk_ops) >= batch_size:
                    collection.bulk_write(bulk_ops, ordered=False)
                    bulk_ops = []
            
            # Execute any remaining operations
            if bulk_ops:
                collection.bulk_write(bulk_ops, ordered=False)
            
            logger.info(f"Successfully updated MongoDB with {len(df_copy)} records for {ticker}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating MongoDB for {ticker}: {str(e)}")
            return False

    @classmethod
    async def sync_ticker_data(cls, ticker: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronize ticker data between yfinance and MongoDB.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Optional start date in format YYYY-MM-DD
            end_date: Optional end date in format YYYY-MM-DD
            
        Returns:
            Dictionary with results of the sync operation
        """
        try:
            # Step 1: Get data from both sources
            mongo_df = await cls.get_mongodb_data(ticker, start_date, end_date)
            yf_df = await cls.get_yfinance_data(ticker, start_date, end_date)
            
            # Step 2: Compare the data
            are_identical, merged_df = await cls.compare_data(mongo_df, yf_df)
            
            # Step 3: Update MongoDB if data is different
            if not are_identical and not yf_df.empty:
                updated = await cls.update_mongodb(ticker, merged_df)
                
                return {
                    "ticker": ticker,
                    "data_matched": False,
                    "mongodb_updated": updated,
                    "mongodb_records": len(mongo_df) if not mongo_df.empty else 0,
                    "yfinance_records": len(yf_df) if not yf_df.empty else 0,
                    "updated_records": len(merged_df) if not merged_df.empty else 0
                }
            
            return {
                "ticker": ticker,
                "data_matched": are_identical,
                "mongodb_updated": False,
                "mongodb_records": len(mongo_df) if not mongo_df.empty else 0,
                "yfinance_records": len(yf_df) if not yf_df.empty else 0
            }
            
        except Exception as e:
            logger.error(f"Error syncing ticker data for {ticker}: {str(e)}")
            return {
                "ticker": ticker,
                "error": str(e),
                "data_matched": False,
                "mongodb_updated": False
            } 