from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, Optional, List
from bson import ObjectId
import logging
from datetime import datetime, timezone
from pymongo import ASCENDING, DESCENDING

from ..auth import get_current_user
from ..database import db
from ..routes.api import serialize_mongo_doc
from ..services.trades import delete_trades

logger = logging.getLogger(__name__)

# Create trades router
trades_router = APIRouter(prefix="/trades")

@trades_router.get("")
async def get_trades(
    current_user: Dict[str, Any] = Depends(get_current_user),
    startDate: Optional[int] = None,
    endDate: Optional[int] = None,
    sort: str = "dateUnix",
    sortDirection: str = "asc",
    limit: int = 1000000,
    skip: int = 0,
    openPositions: Optional[bool] = None,
    order: Optional[str] = None
):
    """Get trades for the current user with optional filters"""
    try:
        # Get user ID for filtering
        user_id = current_user["user_id"]
        
        # First, check what's in the collection without any filters
        all_trades = list(db["trades"].find().limit(limit))
        logger.info(f"Total trades in database: {len(all_trades)}")
        
        # Import here to avoid circular imports
        from bson import ObjectId
        
        # Try checking for both string and ObjectId formats
        try:
            user_object_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
            query = {"user_id": user_object_id}
        except Exception as e:
            logger.error(f"Error converting user_id to ObjectId: {e}")
            query = {"user_id": user_id}
        
        logger.info(f"Fetching trades with query: {query}")
        
        # Find all trades to see if any belong to this user
        user_trades_count = db["trades"].count_documents(query)
        logger.info(f"Found {user_trades_count} trades for user {user_id}")
        
        if user_trades_count == 0:
            # If no trades found, try alternative query formats
            all_user_ids = set()
            for trade in all_trades:
                user_id_value = trade.get('user_id')
                if user_id_value:
                    all_user_ids.add(str(user_id_value))
            
            logger.info(f"Available user_ids in database: {list(all_user_ids)}")
            
            # Try all possible formats
            alternative_queries = [
                {"user_id": user_id},  # As is
                {"userId": user_id},  # Different field name
                {"user": user_id},    # Different field name
            ]
            
            for alt_query in alternative_queries:
                count = db["trades"].count_documents(alt_query)
                if count > 0:
                    query = alt_query
                    logger.info(f"Found {count} trades using alternative query: {alt_query}")
                    break
        
        # Apply filters
        if startDate is not None:
            query["td"] = {"$gte": startDate}
        if endDate is not None:
            if "td" in query:
                query["td"]["$lt"] = endDate
            else:
                query["td"] = {"$lt": endDate}
        
        # Set up sort and direction
        sort_direction = ASCENDING if sortDirection == "asc" else DESCENDING
        
        # Apply limit
        cursor = db["trades"].find(query).sort(sort, sort_direction).skip(skip).limit(limit)
        trades = list(cursor)
        logger.info(f"Found {len(trades)} trades for user {user_id}")
        
        # Extract some sample account info for debugging
        if trades:
            sample_accounts = [t.get("account", "N/A") for t in trades[:3]]
        
        # Convert ObjectId to string for serialization
        for trade in trades:
            if "user_id" in trade and isinstance(trade["user_id"], ObjectId):
                trade["user_id"] = str(trade["user_id"])
            if "_id" in trade:
                trade["_id"] = str(trade["_id"])
        #logger.info(f"trades: {trades}")
        return trades
        
    except Exception as e:
        logger.error(f"Error getting trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@trades_router.post("/single")
async def create_trade_single(
    trade_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a single trade from direct upload"""
    try:
        # Handle test requests from the server status monitor
        if trade_data.get("test") is True:
            logger.info("Received test request for /api/trades/single")
            return {"success": True, "message": "Test request successful"}
            
        user_id = current_user["user_id"]
        logger.info(f"Creating trade for user_id: {user_id}")
        
        # Skip if this is a test document with minimal fields
        if trade_data.get("test") == True and len(trade_data) <= 5:
            logger.info("Skipping test document with minimal fields")
            return {
                "success": True,
                "message": "Test document skipped",
                "trade_id": None
            }
            
        # Remove test flag if present
        if "test" in trade_data:
            del trade_data["test"]
        
        # Convert user_id to ObjectId for storage
        user_object_id = ObjectId(user_id)
        
        # Ensure the trade has the necessary user ID as ObjectId
        trade_data["user_id"] = user_object_id
        
        # Add timestamps if not present
        if "createdAt" not in trade_data:
            trade_data["createdAt"] = datetime.now(timezone.utc)
        if "updatedAt" not in trade_data:
            trade_data["updatedAt"] = datetime.now(timezone.utc)
        
        logger.info(f"Processed trade data: {trade_data}")
            
        # Insert the trade into the database
        result = db["trades"].insert_one(trade_data)
        logger.info(f"Created trade with ID {result.inserted_id} via direct upload")
        
        # Return the created trade ID
        return {
            "success": True,
            "message": "Trade created successfully",
            "trade_id": str(result.inserted_id)
        }
            
    except Exception as e:
        logger.error(f"Error creating trade: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating trade: {str(e)}")

@trades_router.post("/bulk")
async def create_trades_bulk(
    trades_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create multiple trades from direct upload"""
    try:
        # Handle test requests from the server status monitor
        if trades_data.get("test") is True:
            logger.info("Received test request for /api/trades/bulk")
            return {"success": True, "message": "Test request successful"}

        user_id = current_user["user_id"]
        logger.info(f"Bulk creating trades for user_id: {user_id}")
        trades = trades_data.get("trades", [])
        
        if not trades:
            return {"success": False, "message": "No trades provided"}
        
        logger.info(f"Processing {len(trades)} trades for bulk upload")
        
        # Convert user_id to ObjectId for storage
        user_object_id = ObjectId(user_id)
        
        # Process and insert trades
        processed_trades = []
        skipped_count = 0
        
        for trade in trades:
            # Skip test documents with minimal fields
            if trade.get("test") == True and len(trade) <= 5:
                skipped_count += 1
                continue
                
            # Remove test flag if present
            if "test" in trade:
                del trade["test"]
            
            # Ensure the trade has the necessary user ID as ObjectId
            trade["user_id"] = user_object_id
            
            # Add timestamps if not present
            if "createdAt" not in trade:
                trade["createdAt"] = datetime.now(timezone.utc)
            if "updatedAt" not in trade:
                trade["updatedAt"] = datetime.now(timezone.utc)
                
            processed_trades.append(trade)
        
        logger.info(f"Processed {len(processed_trades)} valid trades, skipped {skipped_count}")
            
        # Insert trades into the database
        if processed_trades:
            result = db["trades"].insert_many(processed_trades)
            inserted_count = len(result.inserted_ids)
            logger.info(f"Created {inserted_count} trades via direct upload, skipped {skipped_count} test documents")
            
            # Return the created trade IDs
            return {
                "success": True,
                "message": f"Created {inserted_count} trades, skipped {skipped_count} test documents",
                "trade_ids": [str(id) for id in result.inserted_ids]
            }
        else:
            return {"success": False, "message": "No valid trades to insert"}
            
    except Exception as e:
        logger.error(f"Error creating trades: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating trades: {str(e)}")

@trades_router.delete("")
async def delete_trades_endpoint(
    trade_ids: List[str] = Body(..., embed=True),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete trades by their IDs"""
    try:
        # Convert user_id to ObjectId
        from bson import ObjectId
        user_id = current_user["user_id"]
        user_object_id = ObjectId(user_id)
        
        # Update the current_user in globals for the delete_trades service
        from ..services.trades import globals
        globals.current_user = {"objectId": user_id, "objectId_obj": user_object_id}
        
        # Call the delete_trades service function
        deleted_count = await delete_trades(trade_ids)
        
        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} trades",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error deleting trades: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting trades: {str(e)}")

@trades_router.get("/debug")
async def debug_trades(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Diagnostic endpoint to check trades in MongoDB"""
    try:
        # Get first 10 trades without any filters to see what's in the collection
        all_trades = list(db["trades"].find().limit(10))
        
        # Check different user_id formats
        user_id = current_user["user_id"]
        
        # Count trades with various filters
        counts = {
            "total_trades": db["trades"].count_documents({}),
            "with_string_user_id": db["trades"].count_documents({"user_id": user_id}),
            "with_objectid_user_id": db["trades"].count_documents({"user_id": ObjectId(user_id) if isinstance(user_id, str) else user_id}),
            "with_userId_field": db["trades"].count_documents({"userId": user_id}),  # Check alternate field name
            "with_user_field": db["trades"].count_documents({"user": user_id})  # Check another alternate
        }
        
        # Get sample of fields used in trades collection
        sample_fields = []
        for trade in all_trades:
            for field in trade.keys():
                if field not in sample_fields:
                    sample_fields.append(field)
        
        # Return serialized trade examples and counts
        return {
            "trade_count": counts,
            "fields_used": sample_fields,
            "sample_trades": [serialize_mongo_doc(trade) for trade in all_trades]
        }
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        return {"error": str(e)} 