import os
import pandas as pd
import numpy as np
from pymongo import MongoClient
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

def connect_to_mongodb(connection_string="mongodb://localhost:27017/"):
    """Connect to MongoDB and return the client."""
    try:
        client = MongoClient(connection_string)
        # Test connection
        client.server_info()
        return client
    except Exception as e:
        raise ConnectionError(f"Failed to connect to MongoDB: {e}")


def get_ticker_data(ticker, db_name="market", collection_name="prices", date_from=None, date_to=None, sync_with_yfinance=False):
    """
    Get price data for a ticker from MongoDB.
    
    Parameters:
        ticker (str): Stock ticker symbol
        db_name (str): MongoDB database name
        collection_name (str): MongoDB collection name
        date_from (str): Optional start date in format YYYY-MM-DD
        date_to (str): Optional end date in format YYYY-MM-DD
        sync_with_yfinance (bool): Whether to sync with yfinance before getting data
    
    Returns:
        pandas.DataFrame: Price data for the ticker
    """
    try:
        print(f"Fetching data from MongoDB for {ticker}")
        print(f"Date range: from {date_from or 'beginning'} to {date_to or 'end'}")
        
        # Check for yfinance sync
        if sync_with_yfinance:
            # We'll just log this for now - the actual sync will be added in the endpoint
            print(f"Sync with yfinance requested for {ticker}")
            logger.info(f"Checking yfinance data for {ticker} before MongoDB fetch (sync_with_yfinance=True)")
        
        # Connect to MongoDB
        try:
            client = connect_to_mongodb()
            db = client[db_name]
            collection = db[collection_name]
            
            # Check if collection exists
            if collection_name not in db.list_collection_names():
                print(f"Collection '{collection_name}' does not exist in database '{db_name}'")
                # Try to fallback to file-based data
                raise ValueError(f"Collection '{collection_name}' not found in database")
                
        except Exception as conn_err:
            print(f"MongoDB connection error: {conn_err}")
            raise
        
        # Build MongoDB query
        query = {"ticker": ticker.upper()}
        
        # Add date filtering if provided
        if date_from:
            try:
                start_datetime = datetime.strptime(date_from, "%Y-%m-%d")
                query["date"] = {"$gte": start_datetime}
                print(f"Added start date filter: {start_datetime}")
            except ValueError:
                print(f"Invalid date_from format: {date_from}")
                raise ValueError(f"Invalid date_from format: {date_from}. Use YYYY-MM-DD")
                
        if date_to:
            try:
                end_datetime = datetime.strptime(date_to, "%Y-%m-%d")
                if "date" in query:
                    query["date"]["$lte"] = end_datetime
                else:
                    query["date"] = {"$lte": end_datetime}
                print(f"Added end date filter: {end_datetime}")
            except ValueError:
                print(f"Invalid date_to format: {date_to}")
                raise ValueError(f"Invalid date_to format: {date_to}. Use YYYY-MM-DD")
        
        print(f"MongoDB query: {query}")
        
        # Execute query
        try:
            cursor = collection.find(query).sort("date", 1)
            data = list(cursor)
            print(f"Query returned {len(data)} documents")
        except Exception as query_err:
            print(f"MongoDB query error: {query_err}")
            raise
        
        if not data:
            print(f"No data found for ticker: {ticker}")
            if sync_with_yfinance:
                print(f"No MongoDB data, will try yfinance in the endpoint")
            raise ValueError(f"No data found for ticker: {ticker}")
            
        df = pd.DataFrame(data)
        
        # Rename columns if needed to match expected format
        column_mapping = {
            "date": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume"
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # Ensure required columns exist
        required_cols = ["close"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"Missing required columns: {missing_cols}")
            raise ValueError(f"Missing required columns in data: {missing_cols}")
        
        # Ensure date column is datetime
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            
            # Print date range summary
            if not df.empty:
                print(f"DataFrame date range: {df.index.min()} to {df.index.max()}")
        
        # Close connection
        client.close()
        
        return df
        
    except Exception as e:
        print(f"Error getting ticker data from MongoDB: {e}")
        raise Exception(f"Error getting ticker data from MongoDB: {e}")


def read_and_prepare_data(ticker, date_from=None, date_to=None, source="mongodb", calc_returns=True, sync_with_yfinance=False):
    """
    Read and prepare price data for analysis.
    
    Parameters:
        ticker (str): Stock ticker symbol
        date_from (str): Optional start date in format YYYY-MM-DD
        date_to (str): Optional end date in format YYYY-MM-DD
        source (str): Data source, either "file" or "mongodb"
        calc_returns (bool): Whether to calculate returns
        sync_with_yfinance (bool): Whether to sync with yfinance before getting data
    
    Returns:
        pandas.DataFrame: Prepared price data
    """
    try:
        print(f"Reading data for {ticker} from {date_from} to {date_to}, sync_with_yfinance={sync_with_yfinance}")
        
        if sync_with_yfinance:
            logger.info(f"Will check yfinance data for {ticker} before analysis")
            # Note: The actual sync is handled in the API endpoint to avoid circular imports
            # We just log this for information
        
        df = None
        mongodb_error = None
        
        # First try MongoDB if that's the preferred source
        if source == "mongodb":
            try:
                # Get data from MongoDB
                df = get_ticker_data(ticker, date_from=date_from, date_to=date_to, sync_with_yfinance=sync_with_yfinance)
                print(f"Successfully retrieved data from MongoDB for {ticker} ({len(df)} rows)")
                
                # Log some data information
                if not df.empty:
                    print(f"Date range in data: {df.index.min()} to {df.index.max()}")
                    print(f"Columns: {list(df.columns)}")
            except Exception as e:
                mongodb_error = str(e)
                print(f"MongoDB retrieval failed: {e}")
                print("Will try file-based fallback...")
                source = "file"  # Fall back to file-based approach
        
        # File-based approach (either as primary source or fallback)
        if source == "file":
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                file_path = os.path.join(base_dir, "data", "stocks", f"{ticker}.csv")
                
                if not os.path.exists(file_path):
                    print(f"File not found: {file_path}")
                    # Try lowercase filename as fallback
                    file_path = os.path.join(base_dir, "data", "stocks", f"{ticker.lower()}.csv")
                    
                    if not os.path.exists(file_path):
                        if mongodb_error:
                            raise ValueError(f"No data available for {ticker}. MongoDB error: {mongodb_error}. File not found: {file_path}")
                        else:
                            raise FileNotFoundError(f"File not found: {file_path}")
                
                print(f"Reading from file: {file_path}")
                df = pd.read_csv(file_path)
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)
                
                # Apply date filtering if provided
                if date_from:
                    df = df[df.index >= date_from]
                if date_to:
                    df = df[df.index <= date_to]
                    
                print(f"Successfully read {len(df)} rows from file for {ticker}")
            except Exception as file_err:
                if mongodb_error:
                    raise ValueError(f"Failed to get data for {ticker}. MongoDB error: {mongodb_error}. File error: {file_err}")
                else:
                    raise
        
        if df is None or len(df) == 0:
            raise ValueError(f"No data available for {ticker} in the specified date range")
            
        print(f"Retrieved {len(df)} data points for {ticker}")
        
        # Ensure we have necessary columns
        required_columns = ["close"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        if calc_returns:
            # Calculate percentage changes
            try:
                # First ensure close prices are valid numeric values
                df["close"] = pd.to_numeric(df["close"], errors='coerce')
                
                # Remove any invalid values
                df = df.dropna(subset=["close"])
                
                # Check if we have enough data points after cleaning
                if len(df) < 2:
                    raise ValueError(f"Insufficient valid close prices for {ticker}, only {len(df)} valid data points")
                
                # Calculate returns
                df["pct_change"] = df["close"].pct_change() * 100
                
                # Calculate log returns safely with error handling
                close_ratios = df["close"] / df["close"].shift(1)
                # Filter out zeros, negative values, and infinity that would cause problems with log
                valid_ratios = close_ratios[(close_ratios > 0) & (close_ratios != np.inf)]
                if len(valid_ratios) > 0:
                    df["log_returns"] = np.log(valid_ratios)
                else:
                    # Create an empty series with the right index if we have no valid data
                    df["log_returns"] = pd.Series(index=df.index)
                
                # Remove rows with NaN in calculated returns
                df_clean = df.dropna(subset=["log_returns"])
                
                # Only replace the dataframe if we still have sufficient data points
                if len(df_clean) >= 10:  # Arbitrary minimum threshold
                    df = df_clean
                    print(f"After calculating and cleaning returns, {len(df)} data points remain")
                else:
                    # Keep the original dataframe but warn about insufficient data
                    print(f"Warning: Only {len(df_clean)} valid data points after calculating returns, keeping original data")
                    # At minimum, we need the close column for basic analysis
            except Exception as calc_error:
                print(f"Error calculating returns: {calc_error}")
                # If returns calculation fails, continue with just the price data
                print("Continuing with price data only, without returns")
            
            # Check if we have enough data after calculating returns
            if len(df) < 10:  # Arbitrary minimum threshold
                raise ValueError(f"Insufficient data points ({len(df)}) after calculating returns")
        
        # Print date range summary
        if not df.empty:
            print(f"Date range: {df.index.min()} to {df.index.max()}")
        else:
            print("Warning: DataFrame is empty after processing")
            raise ValueError("DataFrame is empty after processing")
        
        return df
        
    except Exception as e:
        print(f"Error reading and preparing data: {e}")
        raise Exception(f"Error reading and preparing data: {e}") 