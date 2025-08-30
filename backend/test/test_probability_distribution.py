import os
import sys
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

# Set testing environment variable
os.environ['TESTING'] = 'True'

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.stock_analysis_tools.probability_distribution import (
    load_prices_from_db,
    compute_distribution,
    get_price_distribution_data
)

def create_mock_price_data():
    """Create realistic price data for testing"""
    # Use numpy random with a fixed seed for reproducibility
    np.random.seed(42)
    
    # Generate 100 days of prices with a slight upward trend
    prices = 100 + np.cumsum(np.random.normal(0.05, 1, size=100))
    return prices

@patch('app.stock_analysis_tools.probability_distribution.read_and_prepare_data')
def test_load_prices_from_db(mock_read_prepare):
    """Test loading prices from database"""
    # Create mock data
    mock_prices = create_mock_price_data()
    mock_df = pd.DataFrame({
        "date": pd.date_range(start='2020-01-01', periods=len(mock_prices)),
        "close": mock_prices
    })
    mock_df.set_index("date", inplace=True)
    
    # Set up mock return value
    mock_read_prepare.return_value = mock_df
    
    # Test function
    result = load_prices_from_db("AAPL")
    
    # Verify results
    assert isinstance(result, np.ndarray), "Should return a numpy array"
    assert len(result) == len(mock_prices), "Should return all prices"
    assert np.array_equal(result, mock_prices), "Should return the correct prices"
    
    # Test with date parameters
    load_prices_from_db("AAPL", date_from="2020-01-01", date_to="2020-12-31")
    mock_read_prepare.assert_called_with("AAPL", date_from="2020-01-01", 
                                        date_to="2020-12-31", calc_returns=False)

def test_compute_distribution_histogram():
    """Test histogram distribution computation"""
    # Create sample price data
    prices = create_mock_price_data()
    
    # Test with histogram method
    x, y = compute_distribution(prices, method="hist", bin_size=5, smooth_window=3)
    
    # Verify results
    assert len(x) == len(y), "X and Y arrays should have the same length"
    assert isinstance(x, np.ndarray), "X should be a numpy array"
    assert isinstance(y, np.ndarray), "Y should be a numpy array"
    assert np.all(y >= 0), "Y values should be non-negative (percentages)"
    
    # Test with smaller bin size
    x2, y2 = compute_distribution(prices, method="hist", bin_size=2, smooth_window=3)
    assert len(x2) > len(x), "Smaller bin size should give more data points"

def test_compute_distribution_kde():
    """Test KDE distribution computation"""
    # Create sample price data
    prices = create_mock_price_data()
    
    # Test with KDE method
    x, y = compute_distribution(prices, method="kde", grid_size=100, bw_method=0.2)
    
    # Verify results
    assert len(x) == len(y), "X and Y arrays should have the same length"
    assert len(x) == 100, "Should have grid_size points"
    assert isinstance(x, np.ndarray), "X should be a numpy array"
    assert isinstance(y, np.ndarray), "Y should be a numpy array"
    assert np.all(y >= 0), "Y values should be non-negative (percentages)"
    
    # Test with different bandwidth
    x2, y2 = compute_distribution(prices, method="kde", grid_size=100, bw_method=0.05)
    assert np.max(y2) > np.max(y), "Smaller bandwidth should give more pronounced peaks"

def test_compute_distribution_monte_carlo():
    """Test Monte Carlo KDE distribution computation"""
    # Create sample price data
    prices = create_mock_price_data()
    
    # Fix random seed for reproducibility
    np.random.seed(42)
    
    # Test with Monte Carlo KDE method
    x, y = compute_distribution(
        prices, 
        method="mc_kde", 
        n_sims=1000, 
        horizon_days=30,
        grid_size=100,
        bw_method=0.2
    )
    
    # Verify results
    assert len(x) == len(y), "X and Y arrays should have the same length"
    assert len(x) == 100, "Should have grid_size points"
    assert isinstance(x, np.ndarray), "X should be a numpy array"
    assert isinstance(y, np.ndarray), "Y should be a numpy array"
    assert np.all(y >= 0), "Y values should be non-negative (percentages)"
    
    # Test with different horizon
    np.random.seed(42)  # Reset seed for reproducibility
    x2, y2 = compute_distribution(
        prices, 
        method="mc_kde", 
        n_sims=1000, 
        horizon_days=60,
        grid_size=100,
        bw_method=0.2
    )
    
    # A longer horizon should result in a wider distribution
    assert np.std(x2) > np.std(x), "Longer horizon should give wider distribution"

@patch('app.stock_analysis_tools.probability_distribution.load_prices_from_db')
def test_get_price_distribution_data(mock_load_prices):
    """Test the main function to get price distribution data"""
    # Create mock price data
    prices = create_mock_price_data()
    mock_load_prices.return_value = prices
    
    # Test histogram method
    result = get_price_distribution_data(
        "AAPL", 
        method="hist",
        bin_size=5,
        smooth_window=3
    )
    
    # Verify structure and content of result
    assert "distribution" in result, "Result should contain distribution data"
    assert "stats" in result, "Result should contain statistics"
    assert "x" in result["distribution"], "Distribution should have x values"
    assert "y" in result["distribution"], "Distribution should have y values"
    assert "mean" in result["stats"], "Stats should include mean"
    assert "median" in result["stats"], "Stats should include median"
    assert "min" in result["stats"], "Stats should include min"
    assert "max" in result["stats"], "Stats should include max"
    assert "std" in result["stats"], "Stats should include std"
    
    # Test KDE method
    result = get_price_distribution_data(
        "AAPL", 
        method="kde",
        grid_size=100,
        bw_method=0.2
    )
    assert len(result["distribution"]["x"]) == 100, "KDE should respect grid_size parameter"
    
    # Test Monte Carlo method
    result = get_price_distribution_data(
        "AAPL", 
        method="mc_kde",
        n_sims=1000,
        horizon_days=30
    )
    assert "distribution" in result, "Result should contain distribution data for MC KDE"
    
    # Test with empty price data
    mock_load_prices.return_value = np.array([])
    with pytest.raises(ValueError):
        get_price_distribution_data("EMPTY")

def test_edge_cases():
    """Test edge cases for distribution calculation"""
    # Skip testing single price point histogram - not supported by the library
    # Instead test with at least two data points for histogram
    two_prices = np.array([100.0, 101.0])
    
    # This should work with at least two data points
    x, y = compute_distribution(two_prices, method="hist", bin_size=1, smooth_window=3)
    assert len(x) > 0, "Should handle two price points in histogram mode"
    
    # Test with multiple price points for KDE - use at least 10 points to be safe
    multi_prices = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 
                            105.0, 106.0, 107.0, 108.0, 109.0])
    
    # Test KDE with multiple price points
    x_kde, y_kde = compute_distribution(multi_prices, method="kde", grid_size=50, bw_method=1.0)
    assert len(x_kde) > 0, "KDE should work with multiple data points"
    assert len(y_kde) > 0, "KDE should generate non-empty probability density values"
    
    # Monte Carlo should work with multiple points for returns calculation
    x_mc, y_mc = compute_distribution(multi_prices, method="mc_kde", n_sims=100, bw_method=1.0, horizon_days=5)
    assert len(x_mc) > 0, "Monte Carlo should work with multiple data points"
    assert len(y_mc) > 0, "Monte Carlo should generate non-empty probability density values"
    
    # Test with negative prices (should still work but might not be realistic)
    neg_prices = np.array([100.0, 90.0, 80.0, -10.0, -20.0, 
                           30.0, 40.0, 50.0, 60.0, 70.0])  # Add more data points
    x_neg, y_neg = compute_distribution(neg_prices, method="hist")
    assert min(x_neg) < 0, "Should handle negative prices"
    
    # Test KDE with negative prices too
    x_neg_kde, y_neg_kde = compute_distribution(neg_prices, method="kde", grid_size=50, bw_method=1.0)
    assert len(x_neg_kde) > 0, "KDE should work with negative prices"

if __name__ == "__main__":
    # Run tests directly
    test_load_prices_from_db()
    test_compute_distribution_histogram()
    test_compute_distribution_kde()
    test_compute_distribution_monte_carlo()
    test_get_price_distribution_data()
    test_edge_cases()
    print("All probability distribution tests passed!") 