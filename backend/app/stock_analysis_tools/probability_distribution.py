# pricedist.py

import os
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
from datetime import datetime
from .data_utils import read_and_prepare_data

# ———————— Config ————————
DEFAULT_TRADING_DAYS = 252    # for annualization
# ————————————————————————————————————————————


def load_prices_from_db(ticker, date_from=None, date_to=None):
    """Load prices from MongoDB."""
    df = read_and_prepare_data(ticker, date_from=date_from, date_to=date_to, calc_returns=False)
    return df["close"].values


def compute_distribution(
    prices,
    method="hist",          # "hist", "kde", or "mc_kde"
    bin_size=5,
    smooth_window=3,
    n_sims=10000,
    horizon_days=1,
    bw_method=0.15,         # Added parameter for KDE bandwidth
    grid_size=500           # Added parameter for KDE grid size
):
    """
    Returns (x, y) for plotting:
      - method="hist": histogram + moving average on historical prices
      - method="kde": KDE on historical prices
      - method="mc_kde": Monte Carlo simulate future end-prices, then KDE

    n_sims: number of Monte Carlo simulations
    horizon_days: days ahead to simulate (uses DEFAULT_TRADING_DAYS for annualization)
    bw_method: bandwidth method for gaussian_kde (scalar or str)
    grid_size: number of points in the output grid
    """
    if method.lower() == "mc_kde":
        # Monte Carlo on log-returns
        # compute daily log returns
        returns = np.log(prices[1:] / prices[:-1])
        mu = returns.mean()
        sigma = returns.std(ddof=1)
        # simulation horizon in years
        T = horizon_days / DEFAULT_TRADING_DAYS
        last_price = prices[-1]
        # simulate N end-prices: GBM
        Z = np.random.normal(size=n_sims)
        sim_end = last_price * np.exp((mu - 0.5 * sigma**2)*T + sigma * np.sqrt(T) * Z)
        # KDE on simulated end prices
        kde = gaussian_kde(sim_end, bw_method=bw_method)
        xs = np.linspace(sim_end.min(), sim_end.max(), grid_size)
        ys = kde(xs) * 100
        return xs, ys

    if method.lower() == "kde":
        # KDE on historical prices with configurable bandwidth and grid size
        kde = gaussian_kde(prices, bw_method=bw_method)
        xs = np.linspace(prices.min(), prices.max(), grid_size)
        ys = kde(xs) * 100
        return xs, ys

    # default: histogram + moving average
    mn, mx = prices.min(), prices.max()
    bins = np.arange(mn, mx + bin_size, bin_size)
    counts, edges = np.histogram(prices, bins=bins)
    pct = counts / counts.sum() * 100
    smooth = np.convolve(pct, np.ones(smooth_window)/smooth_window, mode="same")
    centers = edges[:-1] + bin_size/2
    return centers, smooth


def get_price_distribution_data(
    ticker,
    date_from=None,
    date_to=None,
    method="hist",         # "hist", "kde", or "mc_kde"
    bin_size=5,
    smooth_window=3,
    n_sims=10000,
    horizon_days=1,
    bw_method=0.15,        # Added parameter for KDE bandwidth
    grid_size=500          # Added parameter for KDE grid size
):
    """
    Get price distribution data for a ticker.
    
    Parameters:
        ticker (str): Stock ticker symbol
        date_from (str): Optional start date in format YYYY-MM-DD
        date_to (str): Optional end date in format YYYY-MM-DD
        method (str): Distribution calculation method
        bin_size (int): Bin size for histogram
        smooth_window (int): Smoothing window size
        n_sims (int): Number of Monte Carlo simulations
        horizon_days (int): Horizon days for Monte Carlo
        bw_method (float): Bandwidth for KDE (0.01-1.0)
        grid_size (int): Number of points in KDE grid
        
    Returns:
        dict: Price distribution data
    """
    # Load price data
    prices = load_prices_from_db(ticker, date_from=date_from, date_to=date_to)
    if prices.size == 0:
        raise ValueError("No price data for given range")
        
    # Compute distribution
    x, y = compute_distribution(
        prices,
        method=method,
        bin_size=bin_size,
        smooth_window=smooth_window,
        n_sims=n_sims,
        horizon_days=horizon_days,
        bw_method=bw_method,
        grid_size=grid_size
    )
    
    # Calculate statistics
    stats = {
        "min": float(np.min(prices)),
        "max": float(np.max(prices)),
        "mean": float(np.mean(prices)),
        "median": float(np.median(prices)),
        "std": float(np.std(prices))
    }
    
    return {
        "distribution": {
            "x": x.tolist(),
            "y": y.tolist()
        },
        "stats": stats
    }


# Example usage:
if __name__ == "__main__":
    # Get distribution data
    data = get_price_distribution_data("AAPL", method="kde")
    print(f"Min: ${data['stats']['min']:.2f}")
    print(f"Max: ${data['stats']['max']:.2f}")
    print(f"Mean: ${data['stats']['mean']:.2f}")
    print(f"Median: ${data['stats']['median']:.2f}")
    print(f"Std Dev: ${data['stats']['std']:.2f}")
