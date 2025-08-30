import os
import pandas as pd
import numpy as np
from datetime import datetime
from .data_utils import read_and_prepare_data


def calculate_returns(df):
    """
    Calculate percentage returns from DataFrame.
    Works with both pre-processed data from read_and_prepare_data or
    direct DataFrame from yfinance.
    
    Args:
        df: DataFrame with price data (must have 'close' or 'Close' column)
    
    Returns:
        Series with percentage returns
    """
    try:
        # Check which column format is available
        if 'close' in df.columns:
            close_col = 'close'
        elif 'Close' in df.columns:
            close_col = 'Close'
        else:
            raise ValueError("DataFrame must have 'close' or 'Close' column")
        
        # Calculate percentage change
        if 'pct_change' in df.columns:
            # If pct_change already exists, use it
            returns = df['pct_change'] / 100  # Convert to decimal
        else:
            # Calculate pct_change
            returns = df[close_col].pct_change().dropna()
        
        return returns
    
    except Exception as e:
        print(f"Error calculating returns: {e}")
        # Return empty series as fallback
        return pd.Series()


def calculate_statistics(df):
    """Calculate volatility statistics."""
    returns = df["Pct_Change"].dropna()
    avg = returns.mean()
    std = returns.std()
    return returns, avg, std


def analyze_volatility(ticker, date_from=None, date_to=None):
    """Main function to analyze stock volatility."""
    try:
        # Read and prepare data
        df = read_and_prepare_data(ticker, date_from, date_to)
        close_col = "close"
        
        # Rename pct_change to Pct_Change for compatibility with existing code
        df["Pct_Change"] = df["pct_change"] / 100  # Convert back to decimal for calculations
        
        # Calculate statistics
        returns, avg, std = calculate_statistics(df)
        
        # Return data instead of plotting
        return df, returns
    
    except Exception as e:
        print(f"Error analyzing volatility: {e}")
        return None, None


if __name__ == "__main__":
    # ─── CONFIG ────────────────────────────────────────────────────────────────
    TICKER = "AAPL"                                     # ← your ticker here
    DATE_FROM = None                                    # Optional start date (e.g., "2020-01-01")
    DATE_TO = None                                      # Optional end date (e.g., "2023-12-31")
    
    df, returns = analyze_volatility(TICKER, DATE_FROM, DATE_TO)
    
    if df is not None and returns is not None:
        avg = returns.mean()
        std = returns.std()
        print(f"Average Daily Volatility: {avg:.2%}")
        print(f"Standard Deviation: {std:.2%}")
        print(f"Annualized Volatility: {std * (252 ** 0.5):.2%}")
