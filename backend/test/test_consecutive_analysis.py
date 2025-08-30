import asyncio
import logging
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import pytest
import os
from unittest.mock import patch, MagicMock

# Set testing environment variable
os.environ['TESTING'] = 'True'

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock MongoDB and ibapi when running the file directly (not via pytest)
if __name__ == "__main__":
    # Create mock classes for ibapi
    class MockBarData:
        def __init__(self):
            self.date = ""
            self.open = 0
            self.high = 0
            self.low = 0
            self.close = 0
            self.volume = 0
            self.wap = 0
            self.count = 0

    class MockContract:
        def __init__(self):
            self.symbol = ""
            self.secType = ""
            self.exchange = ""
            self.currency = ""
            self.lastTradeDateOrContractMonth = ""

    class MockOrder:
        def __init__(self):
            self.orderId = 0
            self.action = ""
            self.totalQuantity = 0
            self.orderType = ""
            self.lmtPrice = 0

    class MockExecution:
        def __init__(self):
            self.execId = ""
            self.orderId = 0
            self.shares = 0
            self.price = 0
            
    class MockEClient:
        def __init__(self, wrapper):
            self.wrapper = wrapper
            
        def connect(self, *args, **kwargs):
            pass
            
        def disconnect(self):
            pass
            
        def reqPositions(self):
            pass
            
        def reqAccountSummary(self, *args, **kwargs):
            pass

    class MockEWrapper:
        def error(self, *args, **kwargs):
            pass
            
    # Create a module structure
    ibapi_module = MagicMock()
    ibapi_client = MagicMock()
    ibapi_wrapper = MagicMock()
    ibapi_contract = MagicMock()
    ibapi_order = MagicMock()
    ibapi_execution = MagicMock()
    ibapi_common = MagicMock()
    ibapi_utils = MagicMock()
    ibapi_commission = MagicMock()
    
    # Set up mock classes in modules
    ibapi_client.EClient = MockEClient
    ibapi_wrapper.EWrapper = MockEWrapper
    ibapi_contract.Contract = MockContract
    ibapi_order.Order = MockOrder
    ibapi_execution.Execution = MockExecution
    ibapi_common.BarData = MockBarData
    
    # Install mock modules
    sys.modules['ibapi'] = ibapi_module
    sys.modules['ibapi.client'] = ibapi_client
    sys.modules['ibapi.wrapper'] = ibapi_wrapper
    sys.modules['ibapi.contract'] = ibapi_contract
    sys.modules['ibapi.order'] = ibapi_order
    sys.modules['ibapi.execution'] = ibapi_execution
    sys.modules['ibapi.common'] = ibapi_common
    sys.modules['ibapi.utils'] = ibapi_utils
    sys.modules['ibapi.commission_report'] = ibapi_commission
    
    # Create a MongoDB mock patcher
    mock_mongo_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    
    # Set up MongoDB mock chain
    mock_mongo_client.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    mock_mongo_client.admin.command.return_value = {"ok": 1}
    mock_db.list_collection_names.return_value = ["orders", "trades"]
    
    # Apply MongoDB mock
    mongo_patcher = patch('pymongo.MongoClient', return_value=mock_mongo_client)
    mongo_patcher.start()

    # Also patch yfinance to avoid external API calls during testing
    yf_patcher = patch('yfinance.download')
    mock_yf = yf_patcher.start()
    
    # Mock the yfinance response
    sample_data = {
        'Open': [100, 101, 102],
        'High': [103, 104, 105],
        'Low': [97, 98, 99],
        'Close': [101, 102, 103],
        'Volume': [1000, 1100, 1200]
    }
    mock_yf.return_value = pd.DataFrame(sample_data)

# Import app components after mocking is set up
from fastapi.testclient import TestClient
from app.main import app
from app.stock_analysis_tools import consecutive_analysis, data_utils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_consecutive_analysis")

# Create a test client
client = TestClient(app)

def test_consecutive_endpoint():
    """Test the consecutive analysis endpoint with different parameters"""
    logger.info("=== Testing consecutive analysis endpoint ===")
    
    # Test with a well-known ticker (should work)
    ticker = "BTC-USD"
    
    # Use recent historical dates to ensure we have data
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    logger.info(f"Testing with {ticker} from {start_date} to {end_date}")
    
    # Test "up" direction
    response = client.get(
        f"/api/stock-analysis/consecutive/{ticker}",
        params={
            "direction": "up",
            "min_days": 2,
            "max_days": 5,
            "start_date": start_date,
            "end_date": end_date
        }
    )
    
    # Log response status and first part of content
    logger.info(f"Response status: {response.status_code}")
    response_data = response.json()
    
    # Check if we got a valid response (should not 500 even if no patterns found)
    assert response.status_code != 500, "Endpoint should not return a 500 error"
    
    # Check that we have a response with the correct structure
    assert "ticker" in response_data, "Response should contain ticker"
    assert "direction" in response_data, "Response should contain direction"
    assert "probabilities" in response_data, "Response should contain probabilities"
    
    # If we have an error field, log it but don't fail the test
    if "error" in response_data:
        logger.warning(f"Response contains error: {response_data['error']}")
    
    # Log the probabilities (if any)
    probabilities = response_data.get("probabilities", {})
    if probabilities:
        logger.info(f"Found patterns for {len(probabilities)} different streak lengths")
        # Print some stats for the first streak length
        first_key = next(iter(probabilities.keys()), None)
        if first_key:
            first_streak = probabilities[first_key]
            logger.info(f"For {first_key}-day streaks: count={first_streak.get('count')}, "
                        f"next_day_probability={first_streak.get('next_day_probability')}")
    else:
        logger.warning("No patterns found in the response")
    
    # Test with a cryptocurrency (may have different data characteristics)
    crypto_ticker = "BTC-USD"
    
    logger.info(f"Testing with cryptocurrency {crypto_ticker}")
    
    crypto_response = client.get(
        f"/api/stock-analysis/consecutive/{crypto_ticker}",
        params={
            "direction": "down",
            "min_days": 2,
            "max_days": 5,
            "start_date": start_date,
            "end_date": end_date
        }
    )
    
    logger.info(f"Crypto response status: {crypto_response.status_code}")
    
    # Crypto response should also not 500
    assert crypto_response.status_code != 500, "Endpoint should not return a 500 error for crypto"
    
    # Test with future dates (should be handled gracefully)
    future_start = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    future_end = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    
    logger.info(f"Testing with future dates from {future_start} to {future_end}")
    
    future_response = client.get(
        f"/api/stock-analysis/consecutive/{ticker}",
        params={
            "direction": "up",
            "min_days": 2,
            "max_days": 5,
            "start_date": future_start,
            "end_date": future_end
        }
    )
    
    logger.info(f"Future dates response status: {future_response.status_code}")
    
    # Even with future dates, should not 500
    assert future_response.status_code != 500, "Endpoint should handle future dates gracefully"
    
    logger.info("=== Consecutive analysis endpoint tests passed ===")

def test_consecutive_analysis_directly():
    """Test the consecutive analysis functions directly with sample data"""
    logger.info("=== Testing consecutive analysis functions directly ===")
    
    # Create a simple test dataframe with known patterns
    dates = pd.date_range(start='2023-01-01', periods=20)
    
    # Create test data with known patterns:
    # - First 5 days: price goes up every day
    # - Next 5 days: price goes down every day
    # - Last 10 days: alternating up/down
    
    closes = [100, 105, 110, 115, 120,  # 5 days up
              115, 110, 105, 100, 95,    # 5 days down
              100, 95, 100, 95, 100,     # alternating
              95, 100, 95, 100, 95]      # alternating
              
    # Create the dataframe
    df = pd.DataFrame({
        'close': closes,
        'date': dates
    })
    
    # Calculate required columns for analysis
    df['is_target_day'] = df['close'] > df['close'].shift(1)  # True for up days
    df['daily_return'] = df['close'].pct_change()
    df = df.dropna()
    
    # Analyze consecutive patterns (up direction)
    logger.info("Testing analyze_consecutive_patterns with 'up' direction")
    consecutive_moves = consecutive_analysis.analyze_consecutive_patterns(df, min_days=2, max_days=5)
    
    # We should have found patterns of length 2, 3, and 4 days (for up direction)
    assert len(consecutive_moves) > 0, "Should have found consecutive patterns"
    
    # Calculate probabilities
    logger.info("Testing calculate_continuation_probabilities")
    probabilities = consecutive_analysis.calculate_continuation_probabilities(consecutive_moves)
    
    # We should have probabilities for the patterns we found
    assert len(probabilities) == len(consecutive_moves), "Should have probabilities for all pattern lengths"
    
    # Test the other direction (down)
    logger.info("Testing with 'down' direction")
    df['is_target_day'] = df['close'] < df['close'].shift(1)  # True for down days
    df = df.dropna()
    
    consecutive_moves_down = consecutive_analysis.analyze_consecutive_patterns(df, min_days=2, max_days=5)
    probabilities_down = consecutive_analysis.calculate_continuation_probabilities(consecutive_moves_down)
    
    # Should have found some down patterns too
    assert len(consecutive_moves_down) > 0, "Should have found consecutive down patterns"
    
    logger.info("=== Direct consecutive analysis tests passed ===")

def test_edge_cases():
    """Test edge cases for consecutive analysis"""
    logger.info("=== Testing consecutive analysis edge cases ===")
    
    # Test with empty dataframe
    empty_df = pd.DataFrame()
    logger.info("Testing with empty dataframe")
    
    empty_result = consecutive_analysis.analyze_consecutive_patterns(empty_df, min_days=2, max_days=5)
    assert empty_result == {}, "Empty dataframe should return empty result"
    
    # Test with dataframe missing required columns
    invalid_df = pd.DataFrame({
        'date': pd.date_range(start='2023-01-01', periods=20),
        'price': np.random.randn(20) + 100  # No 'close' or 'is_target_day' columns
    })
    
    logger.info("Testing with dataframe missing required columns")
    invalid_result = consecutive_analysis.analyze_consecutive_patterns(invalid_df, min_days=2, max_days=5)
    assert invalid_result == {}, "Dataframe missing required columns should return empty result"
    
    # Test with dataframe that's too short
    short_df = pd.DataFrame({
        'close': [100, 105],
        'date': pd.date_range(start='2023-01-01', periods=2),
        'is_target_day': [False, True],
        'daily_return': [0, 0.05]
    })
    
    logger.info("Testing with dataframe that's too short")
    short_result = consecutive_analysis.analyze_consecutive_patterns(short_df, min_days=2, max_days=5)
    assert short_result == {}, "Dataframe that's too short should return empty result"
    
    # Test with min_days > max_days (invalid parameters)
    logger.info("Testing with min_days > max_days")
    valid_df = pd.DataFrame({
        'close': [100, 105, 110, 115, 120],
        'date': pd.date_range(start='2023-01-01', periods=5),
        'is_target_day': [False, True, True, True, True],
        'daily_return': [0, 0.05, 0.0476, 0.0455, 0.0435]
    })
    
    invalid_params_result = consecutive_analysis.analyze_consecutive_patterns(valid_df, min_days=5, max_days=2)
    assert invalid_params_result == {}, "Invalid parameters should return empty result"
    
    logger.info("=== Edge case tests passed ===")

# Allow running the test module directly
if __name__ == "__main__":
    logger.info("Running consecutive analysis tests")
    
    try:
        # Run the simpler tests first (those not requiring API access)
        test_consecutive_analysis_directly()
        test_edge_cases()
        
        # Now run the API test
        test_consecutive_endpoint()
        
        logger.info("All tests passed!")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 