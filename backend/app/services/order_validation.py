from pymongo.database import Database
from bson.objectid import ObjectId
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_duplicate_preorder(db: Database, user_id: str, order_data: dict) -> bool:
    """
    Check if a duplicate preorder already exists in MongoDB for the current user.
    
    Args:
        db: MongoDB database instance
        user_id: Current user ID
        order_data: Order data to check for duplicates
        
    Returns:
        bool: True if a duplicate preorder exists, False otherwise
    """
    # Extract the fields to check for duplicates
    symbol = order_data.get('symbol')
    action = order_data.get('action')
    order_type = order_data.get('orderType')
    total_quantity = order_data.get('totalQuantity')
    current_state = order_data.get('currentState')
    source = order_data.get('source')
    
    # Log the order we're checking
    logger.info(f"Checking for duplicate: {symbol} {action} {order_type} {total_quantity}")
    logger.info(f"Order source: {source}, current_state: {current_state}")
    
    # Only check for duplicates if this is a preorder
    if current_state != "preorder":
        logger.info(f"Not a preorder (state: {current_state}), skipping duplicate check")
        return False
    
    # Check if this is an update to an existing order
    order_id = order_data.get('orderId') or order_data.get('tradeNoteId')
    mongo_db_id = order_data.get('mongoDbId')
    
    # If mongoDbId is provided, this is an update operation, not a duplicate
    if mongo_db_id:
        logger.info(f"Order has mongoDbId {mongo_db_id}, treating as update not duplicate")
        return False
        
    # If _id is provided, this is an existing document
    if '_id' in order_data:
        logger.info(f"Order has _id {order_data['_id']}, treating as update not duplicate")
        return False
    
    # Create reference to orders collection
    orders_collection = db["orders"]
    
    # Query for existing preorders with matching criteria
    query = {
        "userId": user_id,
        "currentState": "preorder",
        "symbol": symbol,
        "action": action,
        "orderType": order_type,
        "totalQuantity": total_quantity
    }
    
    logger.info(f"Duplicate check query: {query}")
    
    # Check if a matching preorder exists
    existing_preorder = orders_collection.find_one(query)
    
    # If no existing preorder, it's not a duplicate
    if not existing_preorder:
        logger.info("No existing preorder found with matching criteria")
        return False
    
    logger.info(f"Found potential duplicate: {existing_preorder.get('_id')}")
    
    # If the order has an ID that matches the existing order, it's an update not a duplicate
    existing_id = str(existing_preorder.get('_id'))
    existing_order_id = existing_preorder.get('orderId')
    
    if order_id and (order_id == existing_id or order_id == existing_order_id):
        logger.info(f"Order ID {order_id} matches existing order, treating as update")
        return False
    
    # If the current order has reasonData but the existing one doesn't,
    # or if the reasonData has changed, treat it as an update
    if order_data.get('reasonData'):
        # If the existing order doesn't have reasonData, this is an update
        if not existing_preorder.get('reasonData'):
            logger.info("Current order has reasonData but existing one doesn't, treating as update")
            
            # Update the existing order with the reasonData
            try:
                orders_collection.update_one(
                    {"_id": existing_preorder["_id"]},
                    {"$set": {"reasonData": order_data.get('reasonData'), "reasonCompleted": True}}
                )
                logger.info(f"Updated existing order {existing_id} with reasonData")
            except Exception as e:
                logger.error(f"Error updating existing order with reasonData: {str(e)}")
                
            # Still treat as duplicate to prevent creating a new document
            return True
            
        # If both have reasonData, check if they're different
        current_reason_data = order_data.get('reasonData')
        existing_reason_data = existing_preorder.get('reasonData')
        
        # Check key fields that indicate changes in the checklist
        has_changes = False
        for key in ['buyReason', 'strategy', 'timeframe', 'entryBasis', 'stopLoss']:
            if current_reason_data.get(key) != existing_reason_data.get(key):
                logger.info(f"ReasonData differs in field '{key}', treating as update")
                logger.info(f"Current value: '{current_reason_data.get(key)}', Existing value: '{existing_reason_data.get(key)}'")
                has_changes = True
        
        if has_changes:
            # Update the existing order with the new reasonData
            try:
                orders_collection.update_one(
                    {"_id": existing_preorder["_id"]},
                    {"$set": {"reasonData": current_reason_data, "reasonCompleted": True}}
                )
                logger.info(f"Updated existing order {existing_id} with new reasonData")
            except Exception as e:
                logger.error(f"Error updating existing order with new reasonData: {str(e)}")
    
    # If we got here, it's a duplicate
    logger.info(f"Determined order is a duplicate of existing order {existing_id}")
    return True 