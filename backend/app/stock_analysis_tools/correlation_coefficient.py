import numpy as np
import pandas as pd
from .data_utils import get_ticker_data


def compute_correlation_matrix(tickers, lookback_days):
    """
    Compute the correlation coefficient matrix for a list of tickers over the given lookback period.
    Args:
        tickers (List[str]): List of ticker symbols.
        lookback_days (int): Number of days to look back.
    Returns:
        np.ndarray: 2D array of correlation coefficients.
        List[str]: List of tickers (order matches matrix rows/columns).
    """
    price_data = {}
    for ticker in tickers:
        df = get_ticker_data(ticker)
        if df is not None and not df.empty:
            # Use only the last N days
            if len(df) > lookback_days:
                df = df.iloc[-lookback_days:]
            price_data[ticker] = df['close']

    # Combine into a single DataFrame, aligning on date
    combined = pd.DataFrame(price_data)
    # Drop rows with any missing values (dates where not all tickers have data)
    combined = combined.dropna()
    if combined.shape[0] < 2:
        # Not enough data to compute correlation
        return np.full((len(tickers), len(tickers)), np.nan), tickers

    corr_matrix = combined.corr().values
    return corr_matrix, list(combined.columns) 