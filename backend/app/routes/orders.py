from fastapi import APIRouter, HTTPException, status, Body, Depends, Query, Response, Request
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from ..database import db
from ..auth import get_current_user
from ..services.order_validation import check_duplicate_preorder
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create API router without prefix (since it will be added in main.py)
router = APIRouter()

# Create orders collection in MongoDB
orders_collection = db["orders"]

@router.post("/orders")
async def save_orders(data: Dict[str, List[Dict[str, Any]]] = Body(...), current_user: Dict = Depends(get_current_user)):
    """
    Save orders to MongoDB
    The orders will include parent-child relationships between main orders and sub-orders
    """
    logger.info("API: Save orders to MongoDB")
    logger.info(f"Request Body: {data}")
    
    try:
        # Extract orders from request body
        orders = data.get("orders", [])
        if not orders:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No orders provided"
            )

        # Add user ID to each order
        user_id = current_user["user_id"]
        
        # Filter out duplicate preorders
        orders_to_save = []
        orders_to_update = []
        duplicate_count = 0
        updated_count = 0
        
        for order in orders:
            order["userId"] = user_id
            order["savedAt"] = datetime.now()
            
            # Check if this is an update to an existing order by checking for MongoDB ID
            has_mongo_id = False
            mongo_id = None
            
            # Check for MongoDB ID in different fields
            if order.get('mongoDbId'):
                mongo_id = order.get('mongoDbId')
                has_mongo_id = True
                logger.info(f"Found order with mongoDbId: {mongo_id}")
            elif order.get('_id'):
                mongo_id = order.get('_id')
                has_mongo_id = True
                logger.info(f"Found order with _id: {mongo_id}")
            
            # Ensure orderId is set
            if "orderId" not in order or not order["orderId"]:
                # If we have a mongoDbId, use that as orderId
                if has_mongo_id:
                    order["orderId"] = mongo_id
                # Otherwise generate a new orderId (will be replaced with _id after insert)
                else:
                    order["orderId"] = str(uuid.uuid4())
            
            if has_mongo_id:
                # This is an update, not a new insert
                logger.info(f"Found order update: {order.get('symbol')} {order.get('action')} with ID {mongo_id}")
                # Store the ID for update operation
                order['mongoDbId'] = mongo_id
                orders_to_update.append(order)
                updated_count += 1
                continue
                
            # Check if this is a duplicate preorder
            is_duplicate = check_duplicate_preorder(db, user_id, order)
            
            if is_duplicate:
                duplicate_count += 1
                logger.info(f"Skipping duplicate preorder: {order.get('symbol')} {order.get('action')} {order.get('orderType')} {order.get('totalQuantity')}")
            else:
                # Add to orders to save
                orders_to_save.append(order)
        
        # Process updates first
        for order in orders_to_update:
            mongo_id = order.pop('mongoDbId', None)
            if not mongo_id:
                continue
                
            try:
                # Try to convert the ID to ObjectId if it's in the right format
                from bson import ObjectId
                query = {"userId": user_id}
                
                try:
                    if ObjectId.is_valid(mongo_id):
                        query["_id"] = ObjectId(mongo_id)
                        logger.info(f"Using ObjectId for update: {mongo_id}")
                    else:
                        # Not a valid ObjectId, use as regular ID
                        query["$or"] = [
                            {"orderId": mongo_id},
                            {"tradeNoteId": mongo_id}
                        ]
                        logger.info(f"Using regular ID for update: {mongo_id}")
                except Exception as e:
                    logger.error(f"Error checking ObjectId validity: {str(e)}")
                    query["$or"] = [
                        {"orderId": mongo_id},
                        {"tradeNoteId": mongo_id}
                    ]
                
                # Update existing document
                result = orders_collection.update_one(
                    query,
                    {"$set": order}
                )
                
                if result.modified_count > 0:
                    logger.info(f"Successfully updated order: {order.get('symbol')} with ID {mongo_id}")
                elif result.matched_count > 0:
                    logger.info(f"Order found but no changes needed: {order.get('symbol')} with ID {mongo_id}")
                else:
                    logger.warning(f"Order update failed, no matching document: {mongo_id}")
                    # Add to orders_to_save to insert as new
                    orders_to_save.append(order)
            except Exception as e:
                logger.error(f"Error updating order {mongo_id}: {str(e)}")
                # Add to orders_to_save to insert as new
                orders_to_save.append(order)
        
        # Skip if all orders were duplicates and no updates or inserts needed
        if not orders_to_save and updated_count == 0:
            logger.info(f"All {duplicate_count} orders were duplicates, nothing to save")
            return {"success": True, "message": f"All {duplicate_count} orders were duplicates, nothing saved", "duplicates": duplicate_count}
        
        # Insert non-duplicate orders into MongoDB
        inserted_count = 0
        if orders_to_save:
            result = orders_collection.insert_many(orders_to_save)
            inserted_ids = result.inserted_ids
            inserted_count = len(inserted_ids)
            logger.info(f" -> {inserted_count} orders inserted into MongoDB")
            
            # Update the newly inserted documents with their MongoDB IDs
            for i, order_id in enumerate(inserted_ids):
                mongo_id = str(order_id)
                orders_collection.update_one(
                    {"_id": order_id},
                    {"$set": {
                        "orderId": mongo_id,
                        "tradeNoteId": mongo_id,
                        "mongoDbId": mongo_id
                    }}
                )
        
        # Return appropriate response
        total_processed = inserted_count + updated_count
        
        logger.info(f" -> {inserted_count} orders inserted, {updated_count} orders updated, {duplicate_count} duplicates skipped")
        
        if duplicate_count > 0:
            return {
                "success": True, 
                "message": f"{inserted_count} orders saved, {updated_count} orders updated, {duplicate_count} duplicates skipped",
                "inserted": inserted_count,
                "updated": updated_count,
                "duplicates": duplicate_count
            }
        else:
            return {
                "success": True, 
                "message": f"{inserted_count} orders saved, {updated_count} orders updated",
                "inserted": inserted_count,
                "updated": updated_count
            }
        
    except Exception as e:
        logger.error(f" -> Error saving orders to MongoDB: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save orders: {str(e)}"
        )

@router.get("/orders")
async def get_orders(
    current_user: Dict = Depends(get_current_user),
    limit: int = Query(100, description="Number of orders to return"),
    skip: int = Query(0, description="Number of orders to skip"),
    symbol: Optional[str] = Query(None, description="Filter by symbol")
):
    """
    Get orders from MongoDB with optional filtering
    Returns main orders with their associated sub-orders
    """
    logger.info("API: Get orders from MongoDB")
    
    try:
        # Build query filter - filter by user ID
        user_id = current_user["user_id"]
        query = {"userId": user_id}
        
        # Add symbol filter if provided
        if symbol:
            query["symbol"] = symbol
        
        # Log the query for debugging
        logger.info(f" -> Query: {query}")
        
        # Check if orders collection exists
        if "orders" not in db.list_collection_names():
            logger.info(" -> Orders collection does not exist yet, creating it")
            # Return empty array if collection doesn't exist yet
            return []
            
        # Query for all orders that match our filter
        cursor = orders_collection.find(query).sort("savedAt", -1).skip(skip).limit(limit)
        
        # Convert MongoDB cursor to list of dictionaries
        orders = []
        for order in cursor:
            # Convert ObjectId to string
            mongo_id = str(order["_id"])
            order["_id"] = mongo_id
            # Ensure orderId exists - silently set to MongoDB ID if missing
            if "orderId" not in order or not order["orderId"]:
                order["orderId"] = mongo_id
                
            # Also add a consistent tradeNoteId for UI components
            if "tradeNoteId" not in order or not order["tradeNoteId"]:
                order["tradeNoteId"] = order["orderId"]
            orders.append(order)
            
        # Log the number of orders found
        logger.info(f" -> Found {len(orders)} orders matching the query")
        
        # If no orders were found, return empty array
        if not orders:
            return []
            
        # Process orders based on relationships
        # First build a map for faster lookup
        order_map = {order["orderId"]: order for order in orders}
        
        # Now process executed orders and their sub-orders
        for order in orders:
            # If this is an executed order with subOrderIds
            if order.get("isExecutedOrder") and "subOrderIds" in order:
                # Make sure all referenced sub-orders are properly linked
                sub_order_ids = order["subOrderIds"]
                for sub_id in sub_order_ids:
                    if sub_id in order_map:
                        # Mark this as not an executed order
                        order_map[sub_id]["isExecutedOrder"] = False
                        # Set the parent relationship
                        order_map[sub_id]["parentOrderId"] = order["orderId"]
        
        logger.info(f" -> Retrieved {len(orders)} orders from MongoDB")
        return orders
        
    except Exception as e:
        logger.error(f" -> Error getting orders from MongoDB: {str(e)}")
        logger.exception("Full traceback:")
        # Return empty array instead of error for better frontend experience
        return []

@router.delete("/orders/{order_id}")
async def delete_order(
    order_id: str,
    current_user: Dict = Depends(get_current_user),
    delete_children: bool = Query(True, description="Whether to delete sub-orders")
):
    """
    Delete an order from MongoDB
    If delete_children is True, also deletes all sub-orders
    If the order is an executed order with subOrderIds, deletes those sub-orders
    """
    logger.info(f"API: Delete order {order_id} from MongoDB")
    
    try:
        user_id = current_user["user_id"]
        
        # First, get the order to check if it's an executed order with sub-order IDs
        order = orders_collection.find_one({
            "orderId": order_id,
            "userId": user_id
        })
        
        deleted_count = 0
        
        # If order exists and we should delete children
        if order and delete_children:
            # Check if this is an executed order with subOrderIds
            if order.get("isExecutedOrder") and "subOrderIds" in order and order["subOrderIds"]:
                # Delete all sub-orders by their IDs
                sub_result = orders_collection.delete_many({
                    "orderId": {"$in": order["subOrderIds"]},
                    "userId": user_id
                })
                deleted_count += sub_result.deleted_count
                logger.info(f" -> Deleted {sub_result.deleted_count} sub-orders by ID")
            
            # Also delete any sub-orders that reference this order as parent
            sub_result = orders_collection.delete_many({
                "parentOrderId": order_id,
                "userId": user_id
            })
            deleted_count += sub_result.deleted_count
            logger.info(f" -> Deleted {sub_result.deleted_count} sub-orders by parentOrderId")
        
        # Delete the main order
        result = orders_collection.delete_one({
            "orderId": order_id,
            "userId": user_id
        })
        
        deleted_count += result.deleted_count
        logger.info(f" -> Deleted {deleted_count} total orders from MongoDB")
        
        if deleted_count == 0:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
            
        return {"success": True, "deleted_count": deleted_count}
        
    except Exception as e:
        logger.error(f" -> Error deleting order from MongoDB: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete order: {str(e)}"
        )

@router.get("/executed-orders")
async def get_executed_orders(
    current_user: Dict = Depends(get_current_user),
    limit: int = Query(100, description="Number of orders to return"),
    skip: int = Query(0, description="Number of orders to skip"),
    symbol: Optional[str] = Query(None, description="Filter by symbol")
):
    """
    Get executed orders from MongoDB with optional filtering
    These are orders that have been marked as executed and can contain sub-order references
    """
    logger.info("API: Get executed orders from MongoDB")
    
    try:
        # Build query filter - filter by user ID and isExecutedOrder=true
        user_id = current_user["user_id"]
        query = {"userId": user_id, "isExecutedOrder": True}
        
        # Add symbol filter if provided
        if symbol:
            query["symbol"] = symbol
        
        # Query for executed orders
        cursor = orders_collection.find(query).sort("savedAt", -1).skip(skip).limit(limit)
        
        # Convert MongoDB cursor to list of dictionaries
        executed_orders = []
        for order in cursor:
            # Convert ObjectId to string
            order["_id"] = str(order["_id"])
            executed_orders.append(order)
            
        logger.info(f" -> Retrieved {len(executed_orders)} executed orders from MongoDB")
        return executed_orders
        
    except Exception as e:
        logger.error(f" -> Error getting executed orders from MongoDB: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get executed orders: {str(e)}"
        )

@router.put("/orders/{order_id}/checklist")
async def update_order_checklist(
    order_id: str,
    reason_data: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_current_user)
):
    """
    Updates the reasonData (checklist) for a specific order.
    """
    logger.info(f"API: Attempting to update checklist for order {order_id} by user {current_user['user_id']}")
    
    try:
        user_id = current_user["user_id"]
        
        # Ensure reason_data is not empty
        if not reason_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No reason_data provided for update"
            )

        # Update the order in the database
        result = orders_collection.update_one(
            {"orderId": order_id, "userId": user_id},
            {"$set": {"reasonData": reason_data, "updatedAt": datetime.now()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {order_id} not found for user {user_id} or no changes were made."
            )
        
        logger.info(f"Successfully updated checklist for order {order_id}. Matched: {result.matched_count}, Modified: {result.modified_count}")
        return {"success": True, "message": "Order checklist updated successfully"}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f" -> Error updating order checklist: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order checklist: {str(e)}"
        )

@router.post("/orders/update")
async def update_order(data: Dict[str, Any] = Body(...), current_user: Dict = Depends(get_current_user)):
    """
    Update an existing order, primarily for updating reasonData
    """
    logger.info("API: Update order in MongoDB")
    
    try:
        # Extract order data
        order = data.get("order")
        if not order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No order data provided"
            )
        
        # Extract orderId
        order_id = order.get("orderId") or order.get("tradeNoteId") or order.get("mongoDbId")
        if not order_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No order ID provided for update"
            )
        
        user_id = current_user["user_id"]
        
        # Set updated timestamp
        order["updatedAt"] = datetime.now()
        
        # Remove fields that should not be updated
        if "_id" in order:
            del order["_id"]
        
        # Build query to find the order
        query = {"userId": user_id}
        
        # Try to use the order_id as a MongoDB ObjectId
        try:
            from bson import ObjectId
            if ObjectId.is_valid(order_id):
                # Valid ObjectId format, use it directly
                query["$or"] = [
                    {"_id": ObjectId(order_id)},
                    {"orderId": order_id},
                    {"tradeNoteId": order_id}
                ]
                logger.info(f"Using valid ObjectId format for update: {order_id}")
            else:
                # Not a valid ObjectId, use as regular ID
                query["$or"] = [
                    {"orderId": order_id},
                    {"tradeNoteId": order_id}
                ]
                logger.info(f"Using regular ID format for update: {order_id}")
        except Exception as e:
            # If any error, fall back to regular ID matching
            logger.error(f"Error checking ObjectId validity: {str(e)}")
            query["$or"] = [
                {"orderId": order_id},
                {"tradeNoteId": order_id}
            ]
        
        logger.info(f"Update query: {query}")
        
        # Use $set to update only the fields provided
        update_result = orders_collection.update_one(
            query,
            {"$set": order}
        )
        
        if update_result.matched_count == 0:
            logger.warning(f"No order found with query {query} for user {user_id}")
            return {
                "success": False,
                "message": f"Order with ID {order_id} not found"
            }
        
        if update_result.modified_count == 0:
            logger.info(f"Order {order_id} was found but no changes were made")
            return {
                "success": True,
                "message": "Order found but no changes were necessary"
            }
        
        logger.info(f"Successfully updated order {order_id}")
        return {
            "success": True,
            "message": "Order updated successfully",
            "orderId": order_id
        }
        
    except Exception as e:
        logger.error(f"Error updating order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order: {str(e)}"
        )

@router.get("/orders/state/{current_state}")
async def get_orders_by_state(
    current_state: str,
    current_user: Dict = Depends(get_current_user),
    limit: int = Query(100, description="Number of orders to return"),
    skip: int = Query(0, description="Number of orders to skip"),
    symbol: Optional[str] = Query(None, description="Filter by symbol")
):
    """
    Get orders from MongoDB filtered by their current state.
    Specifically created for tracking "preorder" state orders.
    """
    logger.info(f"API: Get orders by state: {current_state}")
    
    try:
        # Build query filter - filter by user ID and current state
        user_id = current_user["user_id"]
        query = {"userId": user_id, "currentState": current_state}
        
        # Add symbol filter if provided
        if symbol:
            query["symbol"] = symbol
        
        # Log the query for debugging
        logger.info(f" -> Query: {query}")
        
        # Check if orders collection exists
        if "orders" not in db.list_collection_names():
            logger.info(" -> Orders collection does not exist yet, creating it")
            # Return empty array if collection doesn't exist yet
            return []
            
        # Query for all orders that match our filter
        cursor = orders_collection.find(query).sort("savedAt", -1).skip(skip).limit(limit)
        
        # Convert MongoDB cursor to list of dictionaries
        orders = []
        for order in cursor:
            # Convert ObjectId to string
            mongo_id = str(order["_id"])
            order["_id"] = mongo_id
            
            # Ensure orderId exists - use MongoDB ID if not present
            # This ensures we have a consistent ID for frontend matching
            if "orderId" not in order or not order["orderId"]:
                # Set orderId to _id without logging
                order["orderId"] = mongo_id
            
            # Also add a consistent tradeNoteId for UI components
            if "tradeNoteId" not in order or not order["tradeNoteId"]:
                order["tradeNoteId"] = order["orderId"]
            
            orders.append(order)
            
        # Log the number of orders found
        logger.info(f" -> Found {len(orders)} {current_state} orders matching the query")
        
        return orders
        
    except Exception as e:
        logger.error(f" -> Error getting {current_state} orders from MongoDB: {str(e)}")
        logger.exception("Full traceback:")
        # Return empty array instead of error for better frontend experience
        return []

@router.post("/orders/fix-missing-fields")
async def fix_missing_order_fields(current_user: Dict = Depends(get_current_user)):
    """
    Fix orders in MongoDB that are missing required fields like orderId.
    This will update the actual documents in MongoDB.
    """
    logger.info("API: Fix orders with missing fields in MongoDB")
    
    try:
        # Get user ID
        user_id = current_user["user_id"]
        
        # Query for orders that are missing orderId
        missing_order_id_query = {
            "userId": user_id,
            "$or": [
                {"orderId": {"$exists": False}},
                {"orderId": None},
                {"orderId": ""}
            ]
        }
        
        # Find orders missing orderId
        orders_cursor = orders_collection.find(missing_order_id_query)
        updated_count = 0
        
        # Update each order with missing fields
        for order in orders_cursor:
            mongo_id = str(order["_id"])
            update_data = {
                "orderId": mongo_id,
                "tradeNoteId": mongo_id,
                "mongoDbId": mongo_id,
                "updatedAt": datetime.now()
            }
            
            # Update the document in MongoDB
            result = orders_collection.update_one(
                {"_id": order["_id"]},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                updated_count += 1
        
        logger.info(f" -> Fixed {updated_count} orders with missing fields")
        
        return {
            "success": True,
            "message": f"Fixed {updated_count} orders with missing fields",
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.error(f" -> Error fixing orders with missing fields: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fix orders with missing fields: {str(e)}"
        )

# Debug endpoint to verify router is registered
@router.get("/orders-debug")
async def orders_debug():
    """Debug endpoint to verify orders router is working"""
    logger.info("API: Orders debug endpoint called")
    return {"message": "Orders router is working", "time": str(datetime.now())}

@router.post("/orders/merge")
async def merge_trades(
    data: Dict[str, Any] = Body(...),
    current_user: Dict = Depends(get_current_user)
):
    """
    Merge multiple trades for the same symbol into a single consolidated position
    """
    logger.info("API: Merge trades for a symbol")
    
    try:
        # Extract data from request
        trades = data.get("trades", [])
        ibkr_holding = data.get("ibkrHolding")
        symbol = data.get("symbol")
        
        if not trades or not symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters: trades and symbol"
            )
            
        user_id = current_user["user_id"]
        logger.info(f"Merging {len(trades)} trades for symbol {symbol} by user {user_id}")
        
        # Step 1: Verify all trades belong to this user and symbol
        trade_ids = []
        for trade in trades:
            trade_id = trade.get("_id") or trade.get("mongoDbId") or trade.get("orderId") or trade.get("tradeNoteId")
            if not trade_id:
                logger.warning(f"Trade without ID in merge request: {trade}")
                continue
            trade_ids.append(trade_id)
        
        # If no valid trades, return error
        if not trade_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid trade IDs provided for merging"
            )
            
        # Step 2: Calculate combined quantities and values
        combined_quantity = 0
        combined_value = 0
        position_count = len(trade_ids)
        
        # Fetch the actual trades from MongoDB to ensure we have accurate data
        from bson import ObjectId
        mongo_trades = []
        
        for trade_id in trade_ids:
            query = {"userId": user_id, "symbol": symbol}
            try:
                if ObjectId.is_valid(trade_id):
                    query["$or"] = [{"_id": ObjectId(trade_id)}, {"orderId": trade_id}, {"tradeNoteId": trade_id}]
                else:
                    query["$or"] = [{"orderId": trade_id}, {"tradeNoteId": trade_id}]
                    
                trade = orders_collection.find_one(query)
                if trade:
                    mongo_trades.append(trade)
                    quantity = trade.get("totalQuantity") or trade.get("quantity") or trade.get("shares") or 0
                    value = (
                        trade.get("positionValue") or 
                        (trade.get("entryPrice", 0) * quantity) or 
                        (trade.get("limitPrice", 0) * quantity) or 
                        0
                    )
                    combined_quantity += quantity
                    combined_value += value
                else:
                    logger.warning(f"Trade not found for ID {trade_id}")
            except Exception as e:
                logger.error(f"Error fetching trade {trade_id}: {str(e)}")
        
        if not mongo_trades:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No trades found for the provided IDs for symbol {symbol}"
            )
        
        # Step 3: Calculate weighted average entry price
        weighted_avg_price = combined_value / combined_quantity if combined_quantity > 0 else 0
        
        # Step 4: Check if IBKR holding data should be used
        if ibkr_holding:
            ibkr_value = ibkr_holding.get("value") or 0
            value_diff = abs(combined_value - ibkr_value)
            tolerance = combined_value * 0.02  # 2% tolerance
            
            if value_diff <= tolerance:
                # Values are close enough, use IBKR's values
                logger.info(f"Using IBKR values for merged position (diff: {value_diff})")
                combined_value = ibkr_value
                if combined_quantity > 0 and ibkr_holding.get("entryPrice"):
                    weighted_avg_price = ibkr_holding.get("entryPrice")
        
        # Step 5: Sort trades by date and use newest as base for merged record
        sorted_trades = sorted(mongo_trades, key=lambda x: x.get("timestamp") or x.get("savedAt") or "", reverse=True)
        base_trade = sorted_trades[0] if sorted_trades else None
        
        if not base_trade:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to determine base trade for merging"
            )
        
        # Step 6: Create merged trade record
        merged_trade_id = f"merged_{symbol}_{int(datetime.now().timestamp())}"
        
        merged_trade = {
            # Base fields from the newest position
            **base_trade,
            # Override with merged values
            "_id": None,  # Will be assigned by MongoDB
            "orderId": merged_trade_id,
            "tradeNoteId": merged_trade_id,
            "mongoDbId": None,  # Will be assigned by MongoDB
            
            "userId": user_id,
            "symbol": symbol,
            "totalQuantity": combined_quantity,
            "shares": combined_quantity,
            "quantity": combined_quantity,
            
            "positionValue": combined_value,
            "entryPrice": weighted_avg_price,
            "limitPrice": weighted_avg_price,
            
            # Set merged state
            "currentState": "bought",  # Keep as bought, not merged
            "isMergedPosition": True,
            "mergedFromCount": position_count,
            "mergedFrom": trade_ids,
            
            "mergedAt": datetime.now(),
            "timestamp": datetime.now(),
            "savedAt": datetime.now(),
            
            # Clear irrelevant fields
            "mergeToId": None,
        }
        
        # Remove the _id field which can't be inserted
        if "_id" in merged_trade:
            del merged_trade["_id"]
        
        # Step 7: Insert the merged trade
        insert_result = orders_collection.insert_one(merged_trade)
        merged_id = str(insert_result.inserted_id)
        
        # Update the merged trade with its MongoDB ID
        orders_collection.update_one(
            {"_id": insert_result.inserted_id},
            {"$set": {
                "orderId": merged_id,
                "tradeNoteId": merged_id,
                "mongoDbId": merged_id
            }}
        )
        
        # Step 8: Update original trades to mark them as merged
        update_operations = []
        for trade_id in trade_ids:
            query = {"userId": user_id, "symbol": symbol}
            
            try:
                if ObjectId.is_valid(trade_id):
                    query["$or"] = [{"_id": ObjectId(trade_id)}, {"orderId": trade_id}, {"tradeNoteId": trade_id}]
                else:
                    query["$or"] = [{"orderId": trade_id}, {"tradeNoteId": trade_id}]
                
                update_result = orders_collection.update_one(
                    query,
                    {"$set": {
                        "currentState": "merged",  # Not "merge" as in original spec for clarity
                        "mergeToId": merged_id,
                        "mergedAt": datetime.now()
                    }}
                )
                
                update_operations.append({
                    "tradeId": trade_id,
                    "matched": update_result.matched_count > 0,
                    "modified": update_result.modified_count > 0
                })
                
            except Exception as e:
                logger.error(f"Error updating trade {trade_id}: {str(e)}")
                update_operations.append({
                    "tradeId": trade_id,
                    "matched": False,
                    "modified": False,
                    "error": str(e)
                })
        
        # Step 9: Return success with details
        return {
            "success": True,
            "message": f"Successfully merged {len(mongo_trades)} positions for {symbol}",
            "mergedTradeId": merged_id,
            "symbol": symbol,
            "combinedQuantity": combined_quantity,
            "combinedValue": combined_value,
            "entryPrice": weighted_avg_price,
            "originalTradeIds": trade_ids,
            "updateOperations": update_operations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging trades: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge trades: {str(e)}"
        ) 