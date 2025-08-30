import os
import pandas as pd
import numpy as np
from datetime import datetime
from .data_utils import read_and_prepare_data


def calculate_returns(df, close_col, y_days):
    """Calculate daily and forward returns."""
    df["Pct_Change"] = df[close_col].pct_change()
    df["Forward_Return"] = df[close_col].shift(-y_days) / df[close_col] - 1
    
    # Make sure date is available as a column (not just as index)
    if "date" not in df.columns and df.index.name == "date":
        df["date"] = df.index
    
    # Add multiple forward returns (1, 5, 10, 20 days)
    days_list = [1, 5, 10, 20]
    for days in days_list:
        if days != y_days:  # Skip if already calculated
            col_name = f"Forward_Return_{days}d"
            df[col_name] = df[close_col].shift(-days) / df[close_col] - 1
    
    df = df.dropna(subset=["Pct_Change", "Forward_Return"])
    return df


def filter_moves(df, x_threshold):
    """Filter moves based on threshold."""
    # Add debug logging
    print(f"Filtering data with threshold {x_threshold}, dataframe size: {len(df)}")
    
    # Ensure we have data and valid Pct_Change values
    if df.empty:
        print("WARNING: Empty dataframe provided to filter_moves")
        return pd.DataFrame(), pd.DataFrame()
    
    if 'Pct_Change' not in df.columns:
        print("WARNING: No Pct_Change column in dataframe")
        return pd.DataFrame(), pd.DataFrame()
    
    # Drop any NaN values in Pct_Change to avoid filtering issues
    df = df.dropna(subset=['Pct_Change'])
    
    if df.empty:
        print("WARNING: No valid Pct_Change values after dropping NaNs")
        return pd.DataFrame(), pd.DataFrame()
    
    print(f"Pct_Change range: min={df['Pct_Change'].min()}, max={df['Pct_Change'].max()}")
    
    # Ensure threshold is positive
    x_threshold = abs(x_threshold)
    
    # Filter with a try-except to handle potential issues
    try:
        up = df[df["Pct_Change"] >= x_threshold]
        down = df[df["Pct_Change"] <= -x_threshold]
    except Exception as e:
        print(f"ERROR in filtering moves: {e}")
        return pd.DataFrame(), pd.DataFrame()
    
    print(f"Found {len(up)} up moves and {len(down)} down moves")
    return up, down


def report_stats(group, label, date_col, x_threshold, y_days):
    """Report statistics for a group of moves."""
    # Use ASCII symbols instead of Unicode to avoid encoding issues
    print(f"\n=== {label} (+/-{x_threshold:.1%}) ===")
    
    # Safety check - ensure group is not empty
    if group.empty:
        print("WARNING: Empty group provided to report_stats")
        return
        
    sub = group[[date_col, "Pct_Change", "Forward_Return"]].copy()
    
    # Convert date to string if it's a datetime
    if pd.api.types.is_datetime64_any_dtype(sub[date_col]):
        sub[date_col] = sub[date_col].dt.strftime("%Y-%m-%d")
    elif isinstance(sub[date_col].iloc[0], datetime):
        sub[date_col] = sub[date_col].apply(lambda x: x.strftime("%Y-%m-%d") if hasattr(x, 'strftime') else str(x))
    
    sub["Pct_Change"] = (sub["Pct_Change"] * 100).map("{:.2f}%".format)
    sub["Forward_Return"] = (sub["Forward_Return"] * 100).map("{:.2f}%".format)
    print(sub.to_string(index=False))

    # Handle potential NaN values in statistics
    try:
        desc = group["Forward_Return"].describe(percentiles=[0.25, 0.5, 0.75])
        print(f"\nNext-{y_days}-Day Return Stats:")
        for k in ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]:
            v = desc[k]
            if k == 'count':
                print(f"  {k:>5}: {int(v)}")
            else:
                if pd.isna(v):
                    print(f"  {k:>5}: N/A")
                else:
                    print(f"  {k:>5}: {v*100:6.2f}%")
    except Exception as e:
        print(f"Error calculating statistics: {e}")


def analyze_next_day_stats(ticker, x_threshold=0.10, y_days=10, 
                          date_from=None, date_to=None, movement=None):
    """Main function to analyze next-day statistics after significant moves."""
    try:
        # Add debug logging
        print(f"Starting next-day stats analysis for {ticker} with threshold={x_threshold}, y_days={y_days}")
        print(f"Date range: from {date_from or 'beginning'} to {date_to or 'end'}")
        
        # Input validation
        if x_threshold <= 0:
            x_threshold = 0.01  # Default to 1% if threshold is invalid
            print(f"WARNING: Invalid threshold provided. Using {x_threshold} (1%) instead.")
            
        if y_days <= 0:
            y_days = 10  # Default to 10 days if look ahead is invalid
            print(f"WARNING: Invalid look ahead days provided. Using {y_days} days instead.")
        
        # Read and prepare data - set calc_returns=False as we'll do it ourselves
        df = read_and_prepare_data(ticker, date_from, date_to, calc_returns=False, sync_with_yfinance=True)
        date_col = "date"
        close_col = "close"
        
        # Debug log data shape
        print(f"Data loaded: {len(df)} rows")
        if df.empty:
            print("ERROR: No data loaded")
            return None, None, None
            
        if not df.empty:
            print(f"Date range: {df.index.min()} to {df.index.max()}")
            print(f"Close price range: {df[close_col].min()} to {df[close_col].max()}")
            print(f"Columns before date handling: {df.columns.tolist()}")
        
        # Handle date column properly
        if df.index.name == "date":
            # Reset index to make date a column
            print("Converting date index to column")
            df = df.reset_index()
        elif "date" not in df.columns:
            # If no date column and index is not named 'date', create one from index
            print("No date column found, creating from index")
            df["date"] = df.index
            
        # Check if date exists as a column
        if "date" not in df.columns:
            print("WARNING: No date column available after processing")
        else:
            print(f"Date column type: {type(df['date'][0])}")
            
        # Calculate returns
        df = calculate_returns(df, close_col, y_days)
        
        # Debug log after returns calculation
        print(f"After calculating returns: {len(df)} rows")
        print(f"Columns after calculations: {df.columns.tolist()}")
        if len(df) < 5:
            print("WARNING: Very few data points after calculating returns!")
            return df, pd.DataFrame(), pd.DataFrame()  # Return empty DataFrames for up/down moves
        
        # Filter moves
        up, down = filter_moves(df, x_threshold)
        
        # Check if we found any moves
        if len(up) == 0 and len(down) == 0:
            print(f"WARNING: No significant price moves found for {ticker} with threshold {x_threshold}")
            return df, pd.DataFrame(), pd.DataFrame()  # Return empty DataFrames with the same structure
        
        # Run reports based on movement config - use ASCII versions to avoid Unicode encoding issues
        try:
            if movement == "up":
                if len(up) > 0:
                    report_stats(up, f"Up-moves >= +{x_threshold:.1%}", "date", x_threshold, y_days)
            elif movement == "down":
                if len(down) > 0:
                    report_stats(down, f"Down-moves <= -{x_threshold:.1%}", "date", x_threshold, y_days)
            else:
                if len(up) > 0:
                    report_stats(up, f"Up-moves >= +{x_threshold:.1%}", "date", x_threshold, y_days)
                if len(down) > 0:
                    report_stats(down, f"Down-moves <= -{x_threshold:.1%}", "date", x_threshold, y_days)
        except Exception as e:
            print(f"WARNING: Error generating reports: {e}")
            # Continue anyway - we still want to return the data
        
        return df, up, down
    
    except Exception as e:
        print(f"Error analyzing next day stats: {e}")
        import traceback
        print(traceback.format_exc())
        return None, None, None


if __name__ == "__main__":
    # ─── CONFIG ────────────────────────────────────────────────────────────────
    TICKER       = "AAPL"                                    # ← your ticker here
    X_THRESHOLD  = 0.10                                      # e.g. 0.143 == 14.3%
    Y_DAYS       = 10                                        # look-ahead days
    DATE_FROM    = None                                      # e.g. "2020-01-01" or None
    DATE_TO      = None                                      # e.g. "2021-12-31" or None
    MOVEMENT     = "down"                                    # "up" for only up-moves, "down" for only down-moves, None for both
    
    df, up, down = analyze_next_day_stats(
        TICKER, X_THRESHOLD, Y_DAYS, DATE_FROM, DATE_TO, MOVEMENT
    )
