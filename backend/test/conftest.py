import pytest
import os
import sys
from unittest.mock import patch, MagicMock
import pandas as pd

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the ibapi module since it's an external dependency
# This needs to be done before any imports that use ibapi
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

# Create mock modules
sys.modules['ibapi'] = MagicMock()
sys.modules['ibapi.client'] = MagicMock()
sys.modules['ibapi.wrapper'] = MagicMock()
sys.modules['ibapi.contract'] = MagicMock()
sys.modules['ibapi.order'] = MagicMock()
sys.modules['ibapi.execution'] = MagicMock()
sys.modules['ibapi.common'] = MagicMock()
sys.modules['ibapi.utils'] = MagicMock()
sys.modules['ibapi.commission_report'] = MagicMock()

# Set EClient and EWrapper classes in the mocked modules
sys.modules['ibapi.client'].EClient = MockEClient
sys.modules['ibapi.wrapper'].EWrapper = MockEWrapper

# Set testing environment variable
os.environ['TESTING'] = 'True'

# Create a mock for MongoDB
@pytest.fixture(autouse=True)
def mock_mongodb():
    # Create a MagicMock for MongoDB client
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    
    # Set up the chain: client -> db -> collection
    mock_client.__getitem__.return_value = mock_db
    mock_db.__getitem__.return_value = mock_collection
    
    # Set up collection.find to return an empty list by default
    mock_collection.find.return_value = []
    
    # For yfinance_sync tests, make find_one return None and find return empty list
    mock_collection.find_one.return_value = None
    
    # Set up insert_many to return a success result
    mock_collection.insert_many.return_value = MagicMock(acknowledged=True)
    mock_collection.update_many.return_value = MagicMock(modified_count=1)
    
    # Set command to return success for ping
    mock_client.admin.command.return_value = {"ok": 1}
    
    # Create patch for MongoDB client
    with patch('pymongo.MongoClient', return_value=mock_client):
        yield mock_client

# Create a mock for YFinanceSync.get_mongodb_data
@pytest.fixture(autouse=True)
def mock_get_mongodb_data():
    with patch('app.services.yfinance_sync.YFinanceSync.get_mongodb_data', 
               return_value=pd.DataFrame()):
        yield

# Create a mock for YFinanceSync.get_yfinance_data
@pytest.fixture(autouse=True)
def mock_get_yfinance_data():
    # Create a simple DataFrame that mimics yfinance data
    sample_data = {
        'date': pd.date_range(start='2020-01-01', periods=5),
        'close': [100, 102, 101, 103, 105],
        'open': [99, 100, 102, 101, 103],
        'high': [101, 103, 102, 104, 106],
        'low': [98, 99, 100, 100, 102],
        'volume': [1000, 1200, 800, 1100, 1300]
    }
    mock_df = pd.DataFrame(sample_data)
    mock_df.set_index('date', inplace=True)
    
    with patch('app.services.yfinance_sync.YFinanceSync.get_yfinance_data', 
               return_value=mock_df):
        yield

# Create a mock for YFinanceSync.update_mongodb
@pytest.fixture(autouse=True)
def mock_update_mongodb():
    with patch('app.services.yfinance_sync.YFinanceSync.update_mongodb', 
               return_value=True):
        yield 