from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from .config import MONGO_URI, TRADENOTE_DATABASE
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if we're in testing mode
TESTING = os.environ.get('TESTING', 'False').lower() == 'true'

# Initialize MongoDB client
try:
    logger.info("CONNECTING TO MONGODB")
    # Hide sensitive information in logs
    hidden_db_uri = MONGO_URI.replace("://", "://***@") if "://" in MONGO_URI else MONGO_URI
    logger.info(f" -> Database URI {hidden_db_uri}")
    
    if TESTING:
        logger.info(" -> Running in TEST mode, using mock MongoDB")
        client = MongoClient()  # This will be mocked by pytest
        db = client[TRADENOTE_DATABASE]
    else:
        client = MongoClient(MONGO_URI)
        # Force a command to check the connection
        client.admin.command('ping')
        logger.info(" -> Connected to MongoDB successfully")
        
        # Get the database
        db = client[TRADENOTE_DATABASE]
        
        # This block checks if the "orders" collection exists in the MongoDB database.
        # If it does, it creates indexes on several fields ("orderId", "userId", "symbol", "isExecutedOrder", "parentOrderId")
        # to improve the speed of queries that filter or sort by these fields.
        # After ensuring the indexes are created, it logs a message indicating success.
        if "orders" in db.list_collection_names():
            db["orders"].create_index("orderId")
            db["orders"].create_index("userId")
            db["orders"].create_index("symbol")
            db["orders"].create_index("isExecutedOrder")
            db["orders"].create_index("parentOrderId")
            logger.info("Ensured indexes for orders collection")
    
except ConnectionFailure as e:
    if TESTING:
        logger.info(" -> Mock connection failure handled in test mode")
        client = MongoClient()  # Will be mocked
        db = client[TRADENOTE_DATABASE]
    else:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise

def rename_collection(old_name: str, new_name: str):
    """Rename a collection in MongoDB"""
    try:
        logger.info(f" -> Renaming class {old_name} to {new_name}")
        
        if TESTING:
            logger.info(" -> Skip renaming in test mode")
            return
            
        collections = db.list_collection_names()
        
        if old_name in collections:
            db[old_name].rename(new_name)
            logger.info(" -> Renamed class successfully")
        else:
            logger.info(" -> Collection doesn't exist.")
    except Exception as e:
        logger.error(f" -> Error renaming MongoDB class: {e}")
        if not TESTING:
            raise 