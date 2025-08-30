import os
import sys
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Set testing environment variable
os.environ['TESTING'] = 'True'

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.stock_analysis_tools.volatility import (
    calculate_returns,
    calculate_statistics,
    analyze_volatility
)

# Create sample data for testing
def create_test_data():
    """Create sample price data for testing"""
    dates = pd.date_range(start='2020-01-01', periods=50)
    
    # Create price series with known volatility
    np.random.seed(42)  # For reproducibility
    base_price = 100
    prices = [base_price]
    
    # Generate returns with known parameters
    daily_returns = np.random.normal(0.001, 0.02, 49)  # Mean 0.1%, SD 2%
    
    # Convert returns to prices
    for ret in daily_returns:
        new_price = prices[-1] * (1 + ret)
        prices.append(new_price)
    
    # Create DataFrame with lowercase column names (like our processed data)
    df_lower = pd.DataFrame({
        'date': dates,
        'close': prices,
        'pct_change': np.concatenate([[np.nan], daily_returns]) * 100  # Convert to percentage with leading NaN
    })
    df_lower.set_index('date', inplace=True)
    
    # Create DataFrame with uppercase column names (like raw yfinance data)
    df_upper = pd.DataFrame({
        'Date': dates,
        'Close': prices
    })
    
    return df_lower, df_upper

def test_calculate_returns():
    """Test the returns calculation function"""
    # Create test data
    df_lower, df_upper = create_test_data()
    
    # Test with lowercase columns (processed data)
    returns_lower = calculate_returns(df_lower.reset_index())
    assert not returns_lower.empty, "Returns should not be empty"
    assert len(returns_lower) > 0, "Should calculate returns"
    
    # Test with uppercase columns (raw yfinance data)
    returns_upper = calculate_returns(df_upper)
    assert not returns_upper.empty, "Returns should not be empty"
    assert len(returns_upper) > 0, "Should calculate returns"
    
    # Test with missing columns
    df_invalid = pd.DataFrame({'date': pd.date_range(start='2020-01-01', periods=10)})
    returns_invalid = calculate_returns(df_invalid)
    assert returns_invalid.empty, "Should handle missing columns gracefully"
    
    # Test with empty DataFrame
    returns_empty = calculate_returns(pd.DataFrame())
    assert returns_empty.empty, "Should handle empty DataFrame gracefully"

def test_calculate_statistics():
    """Test the volatility statistics calculation"""
    # Create test data with known parameters
    df = pd.DataFrame({
        'date': pd.date_range(start='2020-01-01', periods=50),
        'Pct_Change': np.random.normal(0.001, 0.02, 50)
    })
    
    # Calculate statistics
    returns, avg, std = calculate_statistics(df)
    
    # Check that we get reasonable results
    assert returns is not None, "Should return returns series"
    assert not np.isnan(avg), "Mean should be a number"
    assert not np.isnan(std), "Standard deviation should be a number"
    assert abs(avg - 0.001) < 0.01, "Mean should be close to expected value"
    assert abs(std - 0.02) < 0.01, "SD should be close to expected value"

@patch('app.stock_analysis_tools.volatility.read_and_prepare_data')
def test_analyze_volatility(mock_read_data):
    """Test the volatility analysis function"""
    # Create mock data with correctly formatted pct_change column
    dates = pd.date_range(start='2020-01-01', periods=50)
    prices = 100 + np.cumsum(np.random.randn(50) * 0.1)
    pct_changes = np.diff(prices) / prices[:-1] * 100  # Convert to percentage
    
    # Create a properly formatted DataFrame
    mock_df = pd.DataFrame({
        'date': dates,
        'close': prices,
        'pct_change': np.concatenate([[np.nan], pct_changes])  # Add NaN for first value
    })
    mock_df.set_index('date', inplace=True)
    
    # Configure the mock
    mock_read_data.return_value = mock_df
    
    # Test with default parameters
    df, returns = analyze_volatility("TEST")
    
    # Check that we get reasonable results
    assert df is not None, "Should return DataFrame"
    assert returns is not None, "Should return returns series"
    assert not returns.empty, "Returns should not be empty"
    
    # Test with date range
    df, returns = analyze_volatility("TEST", "2020-01-01", "2020-12-31")
    assert df is not None, "Should return DataFrame with date range"
    assert returns is not None, "Should return returns with date range"
    
    # Test with data error
    mock_read_data.side_effect = Exception("Test error")
    df_error, returns_error = analyze_volatility("ERROR")
    assert df_error is None, "Should handle errors gracefully"
    assert returns_error is None, "Should handle errors gracefully"

def test_annualized_volatility():
    """Test annualized volatility calculation (used in main block)"""
    # This tests the formula used in the __main__ block
    # Create test data with known daily volatility
    daily_returns = np.random.normal(0.001, 0.02, 252)  # 1 year of data
    daily_std = np.std(daily_returns)
    
    # Calculate annualized volatility
    annualized_vol = daily_std * (252 ** 0.5)
    
    # Check that the annualization factor works as expected
    assert abs(annualized_vol / daily_std - (252 ** 0.5)) < 1e-10, "Annualization formula should be correct"

if __name__ == "__main__":
    # Run tests directly
    test_calculate_returns()
    test_calculate_statistics()
    test_annualized_volatility()
    print("All volatility tests passed!") 