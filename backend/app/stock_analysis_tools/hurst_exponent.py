import os
import numpy as np
import pandas as pd
from datetime import datetime
from .data_utils import read_and_prepare_data


def calculate_hurst_exponent(time_series, max_lag=100):
    """
    Calculate the Hurst exponent of a time series using the rescaled range (R/S) method.
    
    Parameters:
        time_series (array-like): The time series data (e.g., stock prices)
        max_lag (int): Maximum lag for R/S calculation
        
    Returns:
        float: The Hurst exponent value
    """
    # Convert to numpy array and calculate returns/changes
    ts = np.asarray(time_series)
    
    # Check for zero values that would cause division by zero
    if np.any(ts == 0):
        print("Warning: Time series contains zero values, replacing with small positive values")
        ts = np.where(ts == 0, 1e-10, ts)
    
    # Use log returns for financial time series
    returns = np.log(ts[1:] / ts[:-1])
    
    # Remove NaN and infinite values
    returns = returns[~np.isnan(returns) & ~np.isinf(returns)]
    
    if len(returns) < max_lag:
        max_lag = len(returns) // 2
    
    # Safety check for very small datasets
    if max_lag < 10:
        print(f"Warning: max_lag is very small ({max_lag}), results may be unreliable")
        if max_lag < 5:
            raise ValueError(f"Insufficient data points for Hurst calculation (max_lag={max_lag})")
    
    # Calculate R/S values for different lags
    lags = range(2, max_lag)
    rs_values = []
    
    for lag in lags:
        # Calculate the R/S value for this lag
        try:
            rs = calculate_rs(returns, lag)
            if not np.isnan(rs) and np.isfinite(rs):
                rs_values.append(rs)
            else:
                print(f"Warning: Invalid R/S value for lag {lag}, skipping")
        except Exception as e:
            print(f"Error calculating R/S for lag {lag}: {e}")
            # Skip this lag and continue
    
    # Check if we have enough valid R/S values
    if len(rs_values) < 5:
        raise ValueError(f"Insufficient valid R/S values (got {len(rs_values)}, need at least 5)")
    
    # Convert to logarithms for regression
    log_lags = np.log10(lags[:len(rs_values)])
    log_rs = np.log10(rs_values)
    
    # Perform linear regression to find the Hurst exponent
    hurst_exponent, _ = np.polyfit(log_lags, log_rs, 1)
    
    # Validate the result
    if np.isnan(hurst_exponent) or not np.isfinite(hurst_exponent):
        raise ValueError("Calculated Hurst exponent is not a valid number")
    
    return hurst_exponent


def calculate_rs(time_series, lag):
    """
    Calculate the Rescaled Range (R/S) value for a specific lag.
    """
    # Check for NaN values
    if np.any(np.isnan(time_series[:lag])) or np.any(np.isinf(time_series[:lag])):
        return np.nan
    
    # Calculate cumulative deviations from mean
    mean = np.mean(time_series[:lag])
    ts_mean_adj = time_series[:lag] - mean
    cumsum = np.cumsum(ts_mean_adj)
    
    # Calculate range (max - min)
    R = np.max(cumsum) - np.min(cumsum)
    
    # Calculate standard deviation
    S = np.std(time_series[:lag])
    
    # Handle division by zero
    if S < 1e-10:  # Use a small threshold instead of exact zero
        return np.nan
    
    # Return R/S
    return R / S


def interpret_hurst(h):
    """
    Interpret the Hurst exponent value.
    
    Parameters:
        h (float): The Hurst exponent value
        
    Returns:
        str: Interpretation of the Hurst exponent
    """
    if h > 0.55:
        trend_strength = "strong" if h > 0.7 else "moderate"
        return f"Trending (H={h:.3f}): {trend_strength} trend persistence. Past movements are likely to continue in the same direction."
    elif h < 0.45:
        reversion_strength = "strong" if h < 0.3 else "moderate"
        return f"Mean-reverting (H={h:.3f}): {reversion_strength} mean reversion. Price tends to oscillate and revert to the mean."
    else:
        return f"Random walk (H={h:.3f}): No memory effect. Past movements don't influence future ones."


def calculate_hurst_by_window(time_series, window_size=252, step=63):
    """
    Calculate the Hurst exponent over rolling windows.
    
    Parameters:
        time_series (array-like): The time series data
        window_size (int): Size of each window (e.g., 252 for annual window)
        step (int): Step size for rolling window (e.g., 63 for quarterly steps)
        
    Returns:
        tuple: (dates, hurst_values)
    """
    hurst_values = []
    indices = []
    
    # Clean the input data
    if hasattr(time_series, 'dropna'):  # Check if it's a pandas Series or similar
        time_series = time_series.dropna().values
    else:
        # For numpy arrays or lists, convert to numpy and filter out NaN and Inf values
        time_series = np.array(time_series)
        time_series = time_series[~np.isnan(time_series) & ~np.isinf(time_series)]
    
    # Safety check for window size
    if len(time_series) < window_size:
        print(f"Warning: time series length ({len(time_series)}) is less than window size ({window_size})")
        # Try with a smaller window size if possible
        if len(time_series) >= 20:  # Minimum reasonable window size
            window_size = len(time_series) // 2
            step = max(1, window_size // 4)
            print(f"Adjusting window size to {window_size} and step to {step}")
        else:
            print("Insufficient data points for rolling Hurst calculation")
            return indices, hurst_values
    
    # Use a smaller step if we have few data points
    if len(time_series) < 4 * step:
        step = max(1, len(time_series) // 8)
        print(f"Adjusted step size to {step} based on available data")
    
    for i in range(0, len(time_series) - window_size + 1, step):
        if i + window_size <= len(time_series):
            try:
                window_data = time_series[i:i+window_size]
                # Skip windows with insufficient valid data
                if len(window_data) < window_size * 0.8:  # Require at least 80% of the window
                    print(f"Skipping window at index {i} due to insufficient valid data")
                    continue
                    
                h = calculate_hurst_exponent(window_data)
                
                # Validate the result
                if np.isnan(h) or not np.isfinite(h) or h < 0 or h > 1:
                    print(f"Invalid Hurst value {h} for window at index {i}, skipping")
                    continue
                    
                hurst_values.append(h)
                indices.append(i + window_size - 1)  # Index at the end of the window
            except Exception as e:
                print(f"Error calculating Hurst for window starting at index {i}: {e}")
                # Skip this window and continue
                continue
    
    return indices, hurst_values


def analyze_hurst_exponent(ticker, window_size=252, step=63, date_from=None, date_to=None, visualize=False):
    """
    Analyze the Hurst exponent for a stock.
    
    Parameters:
        ticker (str): Stock ticker symbol to analyze
        window_size (int): Size of the rolling window in days
        step (int): Step size for rolling window
        date_from (str): Optional start date for analysis (YYYY-MM-DD)
        date_to (str): Optional end date for analysis (YYYY-MM-DD)
        visualize (bool): Whether to display visualization (kept for compatibility)
        
    Returns:
        tuple: (DataFrame, Hurst exponent value)
    """
    try:
        date_range_info = ""
        if date_from or date_to:
            date_range_info = f" (from {date_from or 'beginning'} to {date_to or 'end'})"
        print(f"Analyzing Hurst exponent for {ticker}{date_range_info}")
        
        # Read and prepare data with date filtering
        try:
            df = read_and_prepare_data(ticker, date_from, date_to)
        except Exception as data_error:
            print(f"Error reading data: {data_error}")
            # Provide more specific error message
            if "No data available" in str(data_error) or "File not found" in str(data_error):
                raise ValueError(f"No price data found for ticker '{ticker}'{date_range_info}")
            elif "Insufficient data points" in str(data_error):
                raise ValueError(f"Insufficient data points for ticker '{ticker}'{date_range_info}")
            else:
                raise ValueError(f"Error reading price data: {data_error}")
        
        # Ensure we have enough data
        if len(df) < window_size:
            raise ValueError(f"Insufficient data points ({len(df)}) for window size {window_size}. Need at least {window_size} data points.")
        
        # Check for future dates
        today = pd.Timestamp.today()
        future_dates = df.index[df.index > today]
        if len(future_dates) > 0:
            print(f"Warning: Found {len(future_dates)} future dates in the data (first: {future_dates[0]})")
        
        # Calculate Hurst exponent for the entire series
        # First try with log_returns if available
        try:
            if 'log_returns' in df.columns and not df['log_returns'].empty and not df['log_returns'].isna().all():
                # Verify we have valid log_returns
                valid_returns = df["log_returns"].dropna()
                if len(valid_returns) >= window_size:
                    print(f"Using log_returns for Hurst calculation ({len(valid_returns)} valid points)")
                    hurst = calculate_hurst_exponent(valid_returns.values)
                else:
                    # Not enough valid log returns, fall back to using price data
                    print(f"Insufficient valid log_returns ({len(valid_returns)}), falling back to close prices")
                    prices = df["close"].dropna().values
                    if len(prices) < window_size:
                        raise ValueError(f"Insufficient close prices ({len(prices)}) for Hurst calculation")
                    hurst = calculate_hurst_exponent(prices)
            else:
                # Fall back to calculating from close prices
                print("No valid log_returns in data, using close prices for Hurst calculation")
                prices = df["close"].dropna().values
                if len(prices) < window_size:
                    raise ValueError(f"Insufficient close prices ({len(prices)}) for Hurst calculation")
                hurst = calculate_hurst_exponent(prices)
                
        except Exception as calc_error:
            print(f"Error in Hurst calculation: {calc_error}")
            
            # Try with a smaller window size if the original calculation failed
            try:
                print(f"Retrying with a smaller subset of data (last {min(252, len(df))} points)")
                if len(df) >= 20:  # Need at least some reasonable number of points
                    subset_size = min(252, len(df))
                    
                    # Try with log_returns first if available
                    if 'log_returns' in df.columns and not df['log_returns'].empty:
                        valid_returns = df["log_returns"].dropna().tail(subset_size)
                        if len(valid_returns) >= 20:
                            print(f"Using last {len(valid_returns)} valid log_returns for retry")
                            hurst = calculate_hurst_exponent(valid_returns.values)
                        else:
                            # Not enough valid returns, use prices
                            print(f"Using last {subset_size} close prices for retry")
                            prices = df["close"].dropna().tail(subset_size).values
                            hurst = calculate_hurst_exponent(prices)
                    else:
                        # Use prices directly
                        prices = df["close"].dropna().tail(subset_size).values
                        print(f"Using last {len(prices)} close prices for retry")
                        hurst = calculate_hurst_exponent(prices)
                        
                    print(f"Successfully calculated Hurst with subset: {hurst:.3f}")
                else:
                    raise ValueError(f"Not enough data points for retry (have {len(df)}, need at least 20)")
            except Exception as retry_error:
                print(f"Retry failed: {retry_error}")
                raise ValueError(f"Failed to calculate Hurst exponent: {calc_error}. Retry error: {retry_error}")
            
        # Validate Hurst value
        if np.isnan(hurst) or not np.isfinite(hurst):
            print(f"Invalid Hurst value calculated: {hurst}")
            raise ValueError("Calculated Hurst exponent is not a valid number")
            
        interpretation = interpret_hurst(hurst)
        
        print(f"\n=== Hurst Exponent Analysis for {ticker}{date_range_info} ===")
        print(f"Full period Hurst: {hurst:.3f}")
        print(interpretation)
        
        return df, hurst
    
    except Exception as e:
        print(f"Error analyzing Hurst exponent: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    # ─── CONFIG ──────────────────────────────────────────────────────────────────
    TICKER = "AAPL"                                      # Ticker to analyze
    WINDOW_SIZE = 252                                   # Window size in days (roughly 1 year of trading)
    STEP = 63                                           # Window step size (roughly quarterly)
    DATE_FROM = None                                    # Optional start date (e.g., "2020-01-01")
    DATE_TO = None                                      # Optional end date (e.g., "2023-12-31")
    
    df, hurst = analyze_hurst_exponent(
        TICKER, WINDOW_SIZE, STEP, DATE_FROM, DATE_TO, visualize=False
    )
    
    if df is not None and hurst is not None:
        # Calculate rolling Hurst values
        indices, hurst_values = calculate_hurst_by_window(
            df["log_returns"].values, WINDOW_SIZE, STEP
        )
        
        # Print rolling Hurst values
        if len(indices) > 0:
            print("\nRolling Hurst Exponent Values:")
            dates = [df.index[i].strftime("%Y-%m-%d") for i in indices]
            for i, (date, h) in enumerate(zip(dates, hurst_values)):
                print(f"{date}: {h:.3f}")
                if i >= 9:  # Limit to 10 values
                    print("...")
                    break 