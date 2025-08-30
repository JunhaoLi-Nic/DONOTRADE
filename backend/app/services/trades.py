import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Import database
from app.database import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for user context only
class Globals:
    current_user = None
    timezone_offset = 0

globals = Globals()

async def get_time_zone():
    """Get timezone information - simplified version of useGetTimeZone"""
    logger.info("Getting timezone information")
    # Use UTC by default
    globals.timezone_offset = 0
    return globals.timezone_offset

async def get_existing_trades(user_id: str) -> List[Dict[str, Any]]:
    """Get existing trades directly from database without local storage"""
    logger.info("Getting existing trades")
    
    if not user_id:
        logger.info(" -> No user ID provided, returning empty list")
        return []
    
    # Fetch existing trades from database
    trades_collection = db["trades"]
    try:
        from bson import ObjectId
        # Convert user_id to ObjectId since that's how it's stored in MongoDB
        user_object_id = ObjectId(user_id)
        existing_trades = list(trades_collection.find({"user_id": user_object_id}))
        logger.info(f" -> Found {len(existing_trades)} existing trades")
    except Exception as e:
        logger.error(f" -> Error fetching trades: {str(e)}")
        existing_trades = []
    
    return existing_trades

async def import_trades(trades_data: List[Dict[str, Any]], context: str = "api", broker: str = "default"):
    """Import trades from the provided data without storing in globals"""
    logger.info(f"Importing {len(trades_data)} trades from {broker}")
    
    # Get user ID for filtering
    user_id = globals.current_user.get("objectId", "") if globals.current_user else ""
    logger.info(f" -> Using user_id: {user_id}")
    
    # Convert user_id to ObjectId for storage
    from bson import ObjectId
    try:
        user_object_id = ObjectId(user_id) if user_id else None
    except:
        logger.error(f" -> Could not convert user_id to ObjectId: {user_id}")
        user_object_id = None
    
    if not user_object_id:
        logger.error(" -> No valid user_id, cannot import trades")
        return []
        
    # Get existing trades directly for duplicate checking
    existing_trades = await get_existing_trades(user_id)
    
    # Initialize list for valid trades
    valid_trades = []
    
    # Process each trade
    for trade in trades_data:
        # Skip test data or insufficient trade data
        if trade.get("test") == True and len(trade) <= 5:
            logger.info(" -> Skipping test data entry")
            continue
            
        # Skip trades without required fields
        required_fields = ["symbol", "side"]
        missing_fields = [field for field in required_fields if not trade.get(field)]
        if missing_fields:
            logger.info(f" -> Skipping trade missing required fields: {missing_fields}")
            continue
        
        # Simplified version of the trade processing logic
        processed_trade = {
            "symbol": trade.get("symbol", ""),
            "broker": broker,
            "price": float(trade.get("price", 0)),
            "quantity": float(trade.get("quantity", 0)),
            "side": trade.get("side", ""),
            "date": trade.get("date", datetime.now(timezone.utc).isoformat()),
            "user_id": user_object_id,  # Store as ObjectId
            "status": "imported",
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        
        # If this is a comprehensive trade data (like the example provided), use it directly
        if len(trade) > 10 and "id" in trade and "executions" in trade:
            # Keep all original data but ensure user_id is set
            processed_trade = trade.copy()
            if "user_id" not in processed_trade:
                processed_trade["user_id"] = user_object_id
        
        # Check if trade already exists (simplified)
        trade_exists = False
        for existing_trade in existing_trades:
            # Match using id field if available
            if "id" in processed_trade and "id" in existing_trade:
                if processed_trade["id"] == existing_trade["id"]:
                    trade_exists = True
                    break
            # Fall back to basic matching
            elif (existing_trade.get("symbol") == processed_trade["symbol"] and
                existing_trade.get("price") == processed_trade["price"] and
                existing_trade.get("date") == processed_trade["date"]):
                trade_exists = True
                break
        
        if not trade_exists:
            valid_trades.append(processed_trade)
    
    # Upload trades directly to database instead of storing in globals
    if valid_trades:
        result = await upload_trades_direct(valid_trades)
        return result
    else:
        logger.info(" -> No new trades to upload")
        return []

async def upload_trades_direct(trades_to_upload: List[Dict[str, Any]]):
    """Upload trades directly to database"""
    if not trades_to_upload:
        logger.info(" -> No trades to upload")
        return []
    
    logger.info(f" -> Uploading {len(trades_to_upload)} trades to database")
    
    trades_collection = db["trades"]
    
    # Insert trades in batches
    try:
        result = trades_collection.insert_many(trades_to_upload)
        logger.info(f" -> Uploaded {len(result.inserted_ids)} trades successfully")
        return trades_to_upload
    except Exception as e:
        logger.error(f" -> Error uploading trades: {str(e)}")
        raise

async def delete_trades(trade_ids: List[str], context: str = "api"):
    """Delete trades from database by their IDs"""
    logger.info(f"Deleting {len(trade_ids)} trades")
    
    if not trade_ids:
        logger.info(" -> No trades to delete")
        return 0
    
    trades_collection = db["trades"]
    
    try:
        # Ensure user can only delete their own trades
        user_filter = {}
        if globals.current_user:
            # Try to get objectId_obj first (which is already an ObjectId)
            user_object_id = globals.current_user.get("objectId_obj")
            if not user_object_id:
                # Fall back to converting string ID to ObjectId
                user_id = globals.current_user.get("objectId", "")
                if user_id:
                    from bson import ObjectId
                    user_object_id = ObjectId(user_id)
                    
            if user_object_id:
                user_filter["user_id"] = user_object_id
                logger.info(f" -> Using user_id filter: {user_filter}")
        
        # Create the delete filter with trade IDs and user filter
        from bson import ObjectId
        delete_filter = {"_id": {"$in": [ObjectId(id) for id in trade_ids]}}
        
        # Add user filter for security if available
        if user_filter:
            delete_filter.update(user_filter)
            
        logger.info(f" -> Delete filter: {delete_filter}")
        
        # Execute delete operation
        result = trades_collection.delete_many(delete_filter)
        deleted_count = result.deleted_count
        logger.info(f" -> Deleted {deleted_count} trades successfully")
        return deleted_count
    except Exception as e:
        logger.error(f" -> Error deleting trades: {str(e)}")
        raise 