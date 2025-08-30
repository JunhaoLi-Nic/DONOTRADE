import yfinance as yf
import pandas as pd
import sys
import logging
import pytest
import os
from unittest.mock import patch, MagicMock

# Set testing environment variable
os.environ['TESTING'] = 'True'

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup mocks when running directly
if __name__ == "__main__":
    # Mock yfinance
    class MockTicker:
        def __init__(self, symbol):
            self.symbol = symbol
            self.info = {
                'shortName': f'Mock {symbol}',
                'longName': f'Mock {symbol} Inc.',
                'sector': 'Technology',
                'industry': 'Software'
            }
        
        def history(self, **kwargs):
            data = {
                'Open': [100, 101, 102, 103, 104],
                'High': [105, 106, 107, 108, 109],
                'Low': [95, 96, 97, 98, 99],
                'Close': [101, 102, 103, 104, 105],
                'Volume': [1000, 1100, 1200, 1300, 1400]
            }
            return pd.DataFrame(data)
    
    # Replace yfinance Ticker with our mock
    yf_mock = MagicMock()
    yf_mock.Ticker.return_value = MockTicker("MOCK")
    yf_mock.__version__ = "0.0.0-TEST"
    yf_mock.download.return_value = pd.DataFrame({
        'Open': [100, 101, 102],
        'High': [103, 104, 105],
        'Low': [97, 98, 99],
        'Close': [101, 102, 103],
        'Volume': [1000, 1100, 1200]
    })
    
    # Apply the mock
    original_yf = yf
    sys.modules['yfinance'] = yf_mock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

@pytest.mark.parametrize("ticker_symbol", ["AAPL", "MSFT", "GOOGL"])
def test_ticker(ticker_symbol):
    """Test downloading data for a single ticker"""
    logger.info(f"Attempting to download data for {ticker_symbol}")
    
    try:
        # Get ticker info
        ticker = yf.Ticker(ticker_symbol)
        logger.info(f"Ticker object created for {ticker_symbol}")
        
        # Try getting info
        info = ticker.info
        logger.info(f"Successfully retrieved info for {ticker_symbol}")
        logger.info(f"Company name: {info.get('shortName', 'Unknown')}")
        
        # Download historical data - don't use period with start and end dates
        logger.info(f"Downloading historical data for {ticker_symbol} (2020-2021)")
        hist = ticker.history(start="2020-01-01", end="2021-12-31")
        
        if hist.empty:
            logger.error(f"No historical data returned for {ticker_symbol}")
        else:
            logger.info(f"Successfully downloaded {len(hist)} records for {ticker_symbol}")
            logger.info(f"First few records:\n{hist.head()}")
            
        assert not hist.empty, f"Historical data for {ticker_symbol} should not be empty"
        
    except Exception as e:
        logger.error(f"Error downloading data for {ticker_symbol}: {str(e)}")
        pytest.fail(f"Test failed for {ticker_symbol}: {str(e)}")

def test_yfinance_version():
    """Test yfinance version info"""
    logger.info("=== DIRECT YFINANCE TEST ===")
    
    # Version info
    logger.info(f"yfinance version: {yf.__version__}")
    logger.info(f"pandas version: {pd.__version__}")
    
    assert hasattr(yf, "__version__"), "yfinance should have a __version__ attribute"

# Allow running the test module directly
if __name__ == "__main__":
    logger.info("Running yfinance direct tests")
    try:
        test_yfinance_version()
        for ticker in ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]:
            test_ticker(ticker)
        logger.info("All tests passed!")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 