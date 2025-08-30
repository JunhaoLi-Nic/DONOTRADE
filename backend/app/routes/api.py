from fastapi import APIRouter, HTTPException, Depends, Body, Response, Request, status
from typing import Dict, Any, Optional, List
import os
from ..config import APP_ID, REGISTRATION_ENABLED, POSTHOG_API_KEY, POSTHOG_HOST
from ..auth import get_current_user
from ..database import db
from bson import ObjectId
import logging
from datetime import datetime, timezone
import json
import secrets
import io
from pathlib import Path
from ..stock_analysis_tools import calculate_option_rolling

# Create API router without prefix (prefix is set in main.py)
api_router = APIRouter()

logger = logging.getLogger(__name__)

# Path to the catalysts.json file
CATALYSTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "catalysts.json")

# Helper function to serialize MongoDB documents for JSON response
def serialize_mongo_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MongoDB document to a JSON serializable format
    by converting ObjectId and other non-serializable types to strings
    """
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = serialize_mongo_doc(value)
        elif isinstance(value, list):
            result[key] = [
                serialize_mongo_doc(item) if isinstance(item, dict) else 
                str(item) if isinstance(item, ObjectId) else 
                item.isoformat() if isinstance(item, datetime) else 
                item 
                for item in value
            ]
        else:
            result[key] = value
    
    # Ensure id field is present for frontend compatibility
    if "_id" in result and "id" not in result:
        result["id"] = result["_id"]
    
    # Add objectId field for Parse compatibility
    if "_id" in result and "objectId" not in result:
        result["objectId"] = result["_id"]
        
    return result

@api_router.post("/parseAppId")
async def get_parse_app_id():
    """Return the Parse App ID for configuration"""
    app_id = APP_ID or os.environ.get("APP_ID", "123456")
    # Ensure it's always a string, not an object
    return str(app_id)

@api_router.post("/registerPage")
async def get_register_page():
    """Check if registration is enabled/disabled"""
    # Check if registration is disabled in config or environment
    register_off = not REGISTRATION_ENABLED
    
    # Log the actual value to help debugging
    logger.info(f"Registration disabled: {register_off} (REGISTRATION_ENABLED={REGISTRATION_ENABLED})")
    
    # Return as JSON object with proper boolean
    return {"registerOff": bool(register_off)}

@api_router.post("/posthog")
async def get_posthog():
    """Return PostHog configuration"""
    posthog_api_key = POSTHOG_API_KEY or os.environ.get("POSTHOG_API_KEY", "")
    posthog_host = POSTHOG_HOST or os.environ.get("POSTHOG_HOST", "https://app.posthog.com")
    
    # Check if analytics is disabled
    if not posthog_api_key or posthog_api_key.lower() == "off" or os.environ.get("ANALYTICS_OFF", "").lower() == "true":
        logger.info("Analytics is disabled")
        return {"api_key": "off", "host": posthog_host}
    
    logger.info(f"Returning PostHog configuration with host: {posthog_host}")
    return {
        "api_key": posthog_api_key,
        "host": posthog_host
    }

@api_router.get("/tags")
async def get_tags(
    current_user: Dict[str, Any] = Depends(get_current_user),
    startDate: Optional[int] = None,
    endDate: Optional[int] = None,
    limit: int = 100,
    skip: int = 0
):
    """Get tags for the current user with optional date filtering"""
    try:
        # Log the input parameters for debugging
        logger.info(f"get_tags called with startDate={startDate}, endDate={endDate}, limit={limit}, skip={skip}")
        
        # Add safety check for extremely large limit values
        if limit > 10000:
            logger.warning(f"Received very large limit value: {limit}, capping at 10000")
            limit = 10000
            
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in get_tags")
            return []
            
        try:
            user_id = ObjectId(current_user["user_id"])
        except Exception as e:
            logger.error(f"Invalid user_id format: {current_user.get('user_id')}, error: {str(e)}")
            return []
            
        query = {"user_id": user_id}
        
        # Add date filtering if provided
        if startDate and endDate:
            try:
                # Convert to integers if they're strings
                if isinstance(startDate, str):
                    startDate = int(startDate)
                if isinstance(endDate, str):
                    endDate = int(endDate)
                    
                # Add date range to query
                query["dateUnix"] = {"$gte": startDate, "$lt": endDate}
                logger.info(f"Added date range filter: {startDate} to {endDate}")
            except ValueError as e:
                logger.error(f"Date conversion error: {str(e)}")
                # Continue without date filtering
                
        # Log the final query for debugging
        logger.info(f"MongoDB query: {query}")
        
        # Execute the query with error handling
        try:
            # Check if the tags collection exists
            if "tags" not in db.list_collection_names():
                logger.warning("Tags collection does not exist in the database")
                return []
                
            # Execute the query
            tags = list(db["tags"].find(query).skip(skip).limit(limit))
            logger.info(f"Successfully retrieved {len(tags)} tags")
            
            # Use the helper function to serialize each tag
            serialized_tags = [serialize_mongo_doc(tag) for tag in tags]
            
            return serialized_tags
        except Exception as e:
            logger.error(f"MongoDB query error: {str(e)}")
            return []
            
    except Exception as e:
        logger.error(f"Error getting tags: {str(e)}")
        # Return an empty list instead of raising an exception
        return []

@api_router.get("/excursions")
async def get_excursions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    startDate: Optional[int] = None,
    endDate: Optional[int] = None,
    sortBy: str = "order",
    sortDirection: str = "asc",
    limit: int = 100
):
    """Get excursions for the current user with optional date filtering"""
    try:
        user_id = ObjectId(current_user["user_id"])
        query = {"user_id": user_id}
        
        if startDate and endDate:
            query["dateUnix"] = {"$gte": startDate, "$lt": endDate}
            
        sort_direction = 1 if sortDirection == "asc" else -1
        
        excursions = list(db["excursions"].find(query)
                          .sort(sortBy, sort_direction)
                          .limit(limit))
                          
        for excursion in excursions:
            excursion["_id"] = str(excursion["_id"])
            
        return excursions
    except Exception as e:
        logger.error(f"Error getting excursions: {str(e)}")
        return []

@api_router.get("/satisfactions")
async def get_satisfactions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    startDate: Optional[int] = None,
    endDate: Optional[int] = None,
    tradeId: Optional[str] = None,
    limit: int = 100,
    skip: int = 0
):
    """Get satisfactions for the current user with optional filters"""
    try:
        user_id = ObjectId(current_user["user_id"])
        query = {"user_id": user_id}
        
        if startDate and endDate:
            query["dateUnix"] = {"$gte": startDate, "$lt": endDate}
        
        # Handle special case for diary page (non-trade satisfactions)
        if tradeId == "undefined":
            query["tradeId"] = {"$exists": False}
        elif tradeId:
            query["tradeId"] = tradeId
            
        # Execute query
        satisfactions = list(db["satisfactions"].find(query).skip(skip).limit(limit))
        logger.info(f"Successfully retrieved {len(satisfactions)} satisfactions")
        
        # Use the helper function to serialize each satisfaction
        serialized_satisfactions = [serialize_mongo_doc(satisfaction) for satisfaction in satisfactions]
        
        return serialized_satisfactions
    except Exception as e:
        logger.error(f"Error getting satisfactions: {str(e)}")
        return []

@api_router.get("/availableTags")
async def get_available_tags(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get available tag groups for the current user"""
    try:
        user_id = ObjectId(current_user["user_id"])
        user = db["users"].find_one({"_id": user_id})
        
        if user and "tags" in user:
            return user["tags"]
            
        # Return default structure if no tags defined
        return [{
            "id": "group_0",
            "name": "Ungrouped",
            "color": "#6c757d",
            "tags": []
        }]
    except Exception as e:
        logger.error(f"Error getting available tags: {str(e)}")
        return []

@api_router.post("/updateSchemas")
async def update_schemas():
    """Legacy endpoint for Parse schema updating"""
    # This is a no-op now but returns success to not break legacy code
    return {"status": 200, "existingSchema": []}

@api_router.post("/checkCloudPayment")
async def check_cloud_payment():
    """Legacy endpoint for subscription status"""
    # Return default data
    return {"status": "free"}

@api_router.get("/notes")
async def get_notes(
    current_user: Dict[str, Any] = Depends(get_current_user),
    startDate: Optional[int] = None,
    endDate: Optional[int] = None,
    limit: int = 100
):
    """Get notes for the current user with optional date filtering"""
    try:
        user_id = ObjectId(current_user["user_id"])
        query = {"user_id": user_id}
        
        if startDate and endDate:
            query["dateUnix"] = {"$gte": startDate, "$lt": endDate}
            
        notes = list(db["notes"].find(query).limit(limit))
        
        # Use the helper function to serialize each note
        serialized_notes = [serialize_mongo_doc(note) for note in notes]
        
        return serialized_notes
    except Exception as e:
        logger.error(f"Error getting notes: {str(e)}")
        return []

# The get_trades endpoint has been moved to the trades.py file

# The trade endpoints have been moved to the trades.py file

@api_router.post("/updateNote")
async def update_note(
    note_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update or create a note"""
    try:
        user_id = ObjectId(current_user["user_id"])
        note_id = note_data.get("id")
        date_unix = note_data.get("dateUnix")
        content = note_data.get("note")
        trade_id = note_data.get("tradeId")
        
        if not date_unix:
            raise HTTPException(status_code=400, detail="Missing dateUnix field")
            
        # Check if note exists
        query = {
            "user_id": user_id,
            "dateUnix": date_unix
        }
        
        if trade_id:
            query["tradeId"] = trade_id
            
        existing_note = db["notes"].find_one(query)
        
        if existing_note:
            # Update existing note
            db["notes"].update_one(
                {"_id": existing_note["_id"]},
                {"$set": {"note": content, "updatedAt": datetime.now(timezone.utc)}}
            )
            return {"status": "updated", "id": str(existing_note["_id"])}
        else:
            # Create new note
            note = {
                "user_id": user_id,
                "dateUnix": date_unix,
                "note": content,
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            }
            
            if trade_id:
                note["tradeId"] = trade_id
                
            result = db["notes"].insert_one(note)
            return {"status": "created", "id": str(result.inserted_id)}
            
    except Exception as e:
        logger.error(f"Error updating note: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update note")

@api_router.post("/updateSatisfaction")
async def update_satisfaction(
    satisfaction_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update or create a satisfaction record"""
    try:
        user_id = ObjectId(current_user["user_id"])
        date_unix = satisfaction_data.get("dateUnix")
        satisfaction_value = satisfaction_data.get("satisfaction")
        trade_id = satisfaction_data.get("tradeId")
        
        if date_unix is None:
            raise HTTPException(status_code=400, detail="Missing dateUnix field")
            
        if satisfaction_value is None:
            raise HTTPException(status_code=400, detail="Missing satisfaction value")
            
        # Check if satisfaction record exists
        query = {
            "user_id": user_id,
            "dateUnix": date_unix
        }
        
        if trade_id:
            query["tradeId"] = trade_id
        else:
            query["tradeId"] = {"$exists": False}
            
        existing_record = db["satisfactions"].find_one(query)
        
        if existing_record:
            # Update existing record
            db["satisfactions"].update_one(
                {"_id": existing_record["_id"]},
                {"$set": {"satisfaction": satisfaction_value, "updatedAt": datetime.now(timezone.utc)}}
            )
            return {"status": "updated", "id": str(existing_record["_id"])}
        else:
            # Create new record
            record = {
                "user_id": user_id,
                "dateUnix": date_unix,
                "satisfaction": satisfaction_value,
                "createdAt": datetime.now(timezone.utc),
                "updatedAt": datetime.now(timezone.utc)
            }
            
            if trade_id:
                record["tradeId"] = trade_id
                
            result = db["satisfactions"].insert_one(record)
            return {"status": "created", "id": str(result.inserted_id)}
            
    except Exception as e:
        logger.error(f"Error updating satisfaction: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update satisfaction")

@api_router.post("/updateTags")
async def update_tags(
    tag_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update or create tag mappings"""
    try:
        user_id = ObjectId(current_user["user_id"])
        
        # Check if tags already exist for this trade/item
        existing_tags = db["tags"].find_one({
            "user_id": user_id,
            "tradeId": tag_data.get("tradeId")
        })
        
        if existing_tags:
            # Update existing tags
            db["tags"].update_one(
                {"_id": existing_tags["_id"]},
                {"$set": {
                    "tags": tag_data.get("tags"),
                    "updated_at": datetime.now(timezone.utc)
                }}
            )
            logger.info(f"Updated tags {existing_tags['_id']}")
            return {"success": True, "id": str(existing_tags["_id"])}
        else:
            # Create new tags
            new_tags = {
                "user_id": user_id,
                "tags": tag_data.get("tags"),
                "dateUnix": tag_data.get("dateUnix"),
                "tradeId": tag_data.get("tradeId"),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            result = db["tags"].insert_one(new_tags)
            logger.info(f"Created new tags with ID {result.inserted_id}")
            return {"success": True, "id": str(result.inserted_id)}
    
    except Exception as e:
        logger.error(f"Error updating tags: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating tags: {str(e)}")

@api_router.post("/updateAvailableTags")
async def update_available_tags(
    data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user's available tag groups"""
    try:
        user_id = ObjectId(current_user["user_id"])
        
        # Update user's tags field
        db["users"].update_one(
            {"_id": user_id},
            {"$set": {
                "tags": data.get("tags"),
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.info(f"Updated available tags for user {user_id}")
        return {"success": True}
    
    except Exception as e:
        logger.error(f"Error updating available tags: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating available tags: {str(e)}")

@api_router.get("/dockerVersion")
async def get_docker_version():
    """Return Docker version from environment or default"""
    version = os.environ.get("VERSION", "19.0.3")  # Default version if not set
    return {"version": version}

@api_router.post("/login")
async def login(
    credentials: Dict[str, Any] = Body(...),
    response: Response = None
):
    """Login a user and return a session token"""
    try:
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            raise HTTPException(status_code=400, detail="Missing username or password")
            
        # Find user by username or email
        user = db["users"].find_one({
            "$or": [
                {"username": username},
                {"email": username}
            ]
        })
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # Check password (in a real app, you'd use proper password hashing)
        # This is just for compatibility with Parse Server
        if user.get("password") != password:
            raise HTTPException(status_code=401, detail="Invalid username or password")
            
        # Create a session token
        token = secrets.token_hex(32)
        
        # Update user with session token
        db["users"].update_one(
            {"_id": user["_id"]},
            {"$set": {"sessionToken": token, "lastLogin": datetime.now(timezone.utc)}}
        )
        
        # Remove password from user object
        user.pop("password", None)
        # Convert ObjectId to string
        user["_id"] = str(user["_id"])
        user["objectId"] = user.get("objectId") or str(user["_id"])
        
        # Add token to response
        return {
            "token": token,
            "user": user
        }
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@api_router.post("/register")
async def register(
    user_data: Dict[str, Any] = Body(...),
    response: Response = None
):
    """Register a new user"""
    try:
        # Check if registration is disabled
        if not REGISTRATION_ENABLED:
            raise HTTPException(status_code=403, detail="Registration is disabled")
            
        # Check if username or email already exists
        username = user_data.get("username")
        email = user_data.get("email")
        password = user_data.get("password")
        
        if not username or not email or not password:
            raise HTTPException(status_code=400, detail="Missing required fields")
            
        existing_user = db["users"].find_one({
            "$or": [
                {"username": username},
                {"email": email}
            ]
        })
        
        if existing_user:
            raise HTTPException(status_code=409, detail="Username or email already exists")
            
        # Create a session token
        token = secrets.token_hex(32)
        
        # Create user document
        user = {
            "username": username,
            "email": email,
            "password": password,  # In real app, hash this password
            "sessionToken": token,
            "createdAt": datetime.now(timezone.utc),
            "lastLogin": datetime.now(timezone.utc),
            "accounts": [],
            "tags": [{
                "id": "group_0",
                "name": "Ungrouped",
                "color": "#6c757d",
                "tags": []
            }]
        }
        
        # Insert user
        result = db["users"].insert_one(user)
        
        # Return user data
        user["_id"] = str(result.inserted_id)
        user["objectId"] = str(result.inserted_id)
        user.pop("password", None)
        
        return {
            "token": token,
            "user": user
        }
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail="Registration failed")

@api_router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Log out the current user by clearing their session token"""
    try:
        user_id = ObjectId(current_user["user_id"])
        
        # Clear the session token
        db["users"].update_one(
            {"_id": user_id},
            {"$unset": {"sessionToken": ""}}
        )
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")

@api_router.get("/diaries")
async def get_diaries(
    current_user: Dict[str, Any] = Depends(get_current_user),
    startDate: Optional[int] = None,
    endDate: Optional[int] = None,
    exact: bool = False,
    dateUnix: Optional[int] = None,
    limit: int = 100,
    skip: int = 0
):
    """Get diaries for the current user with optional date filtering"""
    try:
        # Log the input parameters for debugging
        logger.info(f"get_diaries called with startDate={startDate}, endDate={endDate}, exact={exact}, dateUnix={dateUnix}, limit={limit}, skip={skip}")
        
        # Add safety check for extremely large limit values
        if limit > 10000:
            logger.warning(f"Received very large limit value: {limit}, capping at 10000")
            limit = 10000
            
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in get_diaries")
            return []
            
        try:
            user_id = ObjectId(current_user["user_id"])
        except Exception as e:
            logger.error(f"Invalid user_id format: {current_user.get('user_id')}, error: {str(e)}")
            return []
            
        query = {"user_id": user_id}
        
        # Check if diaries collection exists
        if "diaries" not in db.list_collection_names():
            logger.warning("Diaries collection does not exist in the database")
            return []
            
        # Handle exact date match (used to check if diary exists for a specific date)
        if exact and dateUnix:
            query["dateUnix"] = dateUnix
            logger.info(f"Looking for exact match with dateUnix={dateUnix}")
        # Handle date range
        elif startDate and endDate:
            try:
                # Convert to integers if they're strings
                if isinstance(startDate, str):
                    startDate = int(startDate)
                if isinstance(endDate, str):
                    endDate = int(endDate)
                    
                query["dateUnix"] = {"$gte": startDate, "$lt": endDate}
                logger.info(f"Added date range filter: {startDate} to {endDate}")
            except ValueError as e:
                logger.error(f"Date conversion error: {str(e)}")
                # Continue without date filtering
        
        # Log the final query for debugging
        logger.info(f"MongoDB query: {query}")
        
        try:
            # Query diaries collection
            diaries = list(db["diaries"].find(query).skip(skip).limit(limit).sort("dateUnix", -1))
            logger.info(f"Successfully retrieved {len(diaries)} diaries")
            
            # Use the helper function to serialize each diary
            serialized_diaries = [serialize_mongo_doc(diary) for diary in diaries]
            
            return serialized_diaries
        except Exception as e:
            logger.error(f"MongoDB query error: {str(e)}")
            return []
            
    except Exception as e:
        logger.error(f"Error getting diaries: {str(e)}")
        # Return an empty list instead of raising an exception
        return []

@api_router.get("/diaries/{diary_id}")
async def get_diary_by_id(
    diary_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific diary by ID"""
    try:
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in get_diary_by_id")
            raise HTTPException(status_code=400, detail="Invalid user ID")
            
        try:
            user_id = ObjectId(current_user["user_id"])
            diary_object_id = ObjectId(diary_id)
        except Exception as e:
            logger.error(f"Invalid ID format: {e}")
            raise HTTPException(status_code=400, detail="Invalid ID format")
        
        # Verify ownership and retrieve diary
        diary = db["diaries"].find_one({
            "_id": diary_object_id,
            "user_id": user_id
        })
        
        if not diary:
            logger.warning(f"Diary {diary_id} not found or not owned by user {user_id}")
            raise HTTPException(status_code=404, detail="Diary not found")
            
        # Serialize and return the diary
        return serialize_mongo_doc(diary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving diary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving diary: {str(e)}")

@api_router.post("/diaries")
async def create_diary(
    diary_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new diary entry"""
    try:
        user_id = ObjectId(current_user["user_id"])
        
        # Prepare diary document
        new_diary = {
            "user_id": user_id,
            "date": diary_data.get("date"),
            "dateUnix": diary_data.get("dateUnix"),
            "diary": diary_data.get("diary"),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = db["diaries"].insert_one(new_diary)
        diary_id = str(result.inserted_id)
        
        logger.info(f"Created diary with ID: {diary_id}")
        return {"id": diary_id, "status": "success"}
    except Exception as e:
        logger.error(f"Error creating diary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating diary: {str(e)}")

@api_router.put("/diaries/{diary_id}")
async def update_diary(
    diary_id: str,
    diary_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update an existing diary entry"""
    try:
        user_id = ObjectId(current_user["user_id"])
        
        # Verify ownership
        existing_diary = db["diaries"].find_one({
            "_id": ObjectId(diary_id),
            "user_id": user_id
        })
        
        if not existing_diary:
            raise HTTPException(status_code=404, detail="Diary not found or you don't have permission to edit it")
        
        # Prepare update data
        update_data = {
            "date": diary_data.get("date", existing_diary.get("date")),
            "dateUnix": diary_data.get("dateUnix", existing_diary.get("dateUnix")),
            "diary": diary_data.get("diary", existing_diary.get("diary")),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = db["diaries"].update_one(
            {"_id": ObjectId(diary_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            logger.warning(f"Diary {diary_id} update had no effect")
            
        return {"id": diary_id, "status": "success"}
    except Exception as e:
        logger.error(f"Error updating diary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating diary: {str(e)}")

@api_router.delete("/diaries/{diary_id}")
async def delete_diary(
    diary_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a diary entry"""
    try:
        user_id = ObjectId(current_user["user_id"])
        
        # Verify ownership
        existing_diary = db["diaries"].find_one({
            "_id": ObjectId(diary_id),
            "user_id": user_id
        })
        
        if not existing_diary:
            raise HTTPException(status_code=404, detail="Diary not found or you don't have permission to delete it")
        
        result = db["diaries"].delete_one({"_id": ObjectId(diary_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Diary not found")
            
        return {"id": diary_id, "status": "success"}
    except Exception as e:
        logger.error(f"Error deleting diary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting diary: {str(e)}")

@api_router.get("/screenshots")
async def get_screenshots(
    current_user: Dict[str, Any] = Depends(get_current_user),
    startDate: Optional[int] = None,
    endDate: Optional[int] = None,
    dateUnixDay: Optional[int] = None,
    sort: str = "dateUnix",
    sortDirection: str = "desc",
    limit: int = 100,
    skip: int = 0,
    excludeFields: Optional[str] = None
):
    """Get screenshots for the current user with optional filters"""
    try:
        user_id = ObjectId(current_user["user_id"])
        query = {"user_id": user_id}
        
        # Handle specific day
        if dateUnixDay:
            query["dateUnixDay"] = dateUnixDay
        # Handle date range
        elif startDate and endDate:
            query["dateUnix"] = {"$gte": startDate, "$lt": endDate}
            
        # Get projection (fields to exclude)
        projection = {}
        if excludeFields:
            fields = excludeFields.split(',')
            for field in fields:
                projection[field.strip()] = 0
        
        sort_direction = 1 if sortDirection == "asc" else -1
        
        screenshots = list(db["screenshots"].find(
            query, 
            projection
        ).sort(sort, sort_direction).skip(skip).limit(limit))
        
        for screenshot in screenshots:
            screenshot["_id"] = str(screenshot["_id"])
            # Ensure id is also available for frontend compatibility
            if "_id" in screenshot and not "id" in screenshot:
                screenshot["id"] = screenshot["_id"]
            
        return screenshots
    except Exception as e:
        logger.error(f"Error getting screenshots: {str(e)}")
        return []

@api_router.post("/screenshots")
async def create_screenshot(
    screenshot_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new screenshot entry"""
    try:
        user_id = ObjectId(current_user["user_id"])
        
        # Prepare screenshot document
        new_screenshot = {
            "user_id": user_id,
            "name": screenshot_data.get("name"),
            "dateUnix": screenshot_data.get("dateUnix"),
            "dateUnixDay": screenshot_data.get("dateUnixDay"),
            "originalBase64": screenshot_data.get("originalBase64"),
            "annotatedBase64": screenshot_data.get("annotatedBase64", screenshot_data.get("originalBase64")),
            "maState": screenshot_data.get("maState"),
            "symbol": screenshot_data.get("symbol"),
            "side": screenshot_data.get("side"),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = db["screenshots"].insert_one(new_screenshot)
        screenshot_id = str(result.inserted_id)
        
        logger.info(f"Created screenshot with ID: {screenshot_id}")
        return {"id": screenshot_id, "status": "success"}
    except Exception as e:
        logger.error(f"Error creating screenshot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating screenshot: {str(e)}")

@api_router.put("/screenshots/{screenshot_id}")
async def update_screenshot(
    screenshot_id: str,
    screenshot_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update an existing screenshot entry"""
    try:
        user_id = ObjectId(current_user["user_id"])
        
        # Verify ownership
        existing_screenshot = db["screenshots"].find_one({
            "_id": ObjectId(screenshot_id),
            "user_id": user_id
        })
        
        if not existing_screenshot:
            raise HTTPException(status_code=404, detail="Screenshot not found or you don't have permission to edit it")
        
        # Prepare update data with all fields that might be updated
        update_data = {
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Add any fields that are present in the request
        for key in ["name", "dateUnix", "dateUnixDay", "originalBase64", "annotatedBase64", "maState", "symbol", "side"]:
            if key in screenshot_data:
                update_data[key] = screenshot_data[key]
        
        result = db["screenshots"].update_one(
            {"_id": ObjectId(screenshot_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            logger.warning(f"Screenshot {screenshot_id} update had no effect")
            
        return {"id": screenshot_id, "status": "success"}
    except Exception as e:
        logger.error(f"Error updating screenshot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating screenshot: {str(e)}")

@api_router.delete("/screenshots/{screenshot_id}")
async def delete_screenshot(
    screenshot_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a screenshot entry"""
    try:
        user_id = ObjectId(current_user["user_id"])
        
        # Verify ownership
        existing_screenshot = db["screenshots"].find_one({
            "_id": ObjectId(screenshot_id),
            "user_id": user_id
        })
        
        if not existing_screenshot:
            raise HTTPException(status_code=404, detail="Screenshot not found or you don't have permission to delete it")
        
        result = db["screenshots"].delete_one({"_id": ObjectId(screenshot_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Screenshot not found")
            
        return {"id": screenshot_id, "status": "success"}
    except Exception as e:
        logger.error(f"Error deleting screenshot: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting screenshot: {str(e)}")

@api_router.post("/updateAPIs")
async def update_apis(
    data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update API keys for the current user"""
    try:
        user_id = ObjectId(current_user["user_id"])
        
        # Validate input
        if "apis" not in data or not isinstance(data["apis"], list):
            raise HTTPException(status_code=400, detail="Invalid API data format")
            
        # Update user document with new API keys
        result = db["users"].update_one(
            {"_id": user_id},
            {"$set": {"apis": data["apis"]}}
        )
        
        if result.modified_count == 0:
            logger.warning(f"API keys update for user {user_id} had no effect")
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating API keys: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating API keys: {str(e)}")

@api_router.get("/apis")
async def get_apis(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get API keys for the current user"""
    try:
        user_id = ObjectId(current_user["user_id"])
        user = db["users"].find_one({"_id": user_id})
        
        if user and "apis" in user:
            return user["apis"]
            
        # Return empty array if no APIs defined
        return []
    except Exception as e:
        logger.error(f"Error getting APIs: {str(e)}")
        return []

@api_router.get("/patterns")
async def get_patterns(
    current_user: Dict[str, Any] = Depends(get_current_user),
    startDate: Optional[int] = None,
    endDate: Optional[int] = None,
    limit: int = 10,
    skip: int = 0
):
    """Get patterns for the current user with optional date filtering"""
    logger.info(f"get_patterns called with startDate={startDate}, endDate={endDate}, limit={limit}, skip={skip}")
    
    try:
        # Ensure limit is reasonable
        if limit > 10000:
            logger.warning(f"Received very large limit value: {limit}, capping at 10000")
            limit = 10000
            
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in get_patterns")
            return []
            
        try:
            user_id = ObjectId(current_user["user_id"])
        except Exception as e:
            logger.error(f"Invalid user_id format: {current_user.get('user_id')}, error: {str(e)}")
            return []
            
        query = {"user_id": user_id}
        
        # Add date filtering if provided
        if startDate and endDate:
            try:
                # Convert to integers if they're strings
                if isinstance(startDate, str):
                    startDate = int(startDate)
                if isinstance(endDate, str):
                    endDate = int(endDate)
                    
                query["dateUnix"] = {"$gte": startDate, "$lt": endDate}
                logger.info(f"Added date range filter: {startDate} to {endDate}")
            except ValueError as e:
                logger.error(f"Date conversion error: {str(e)}")
                # Continue without date filtering
                
        # Log the final query for debugging
        logger.info(f"MongoDB query: {query}")
        
        # Execute the query with error handling
        try:
            # Check if the patterns collection exists
            if "patterns" not in db.list_collection_names():
                logger.warning("Patterns collection does not exist in the database")
                return []
                
            # Execute the query
            patterns = list(db["patterns"].find(query).skip(skip).limit(limit))
            logger.info(f"Successfully retrieved {len(patterns)} patterns")
            
            # Use the helper function to serialize each pattern
            serialized_patterns = [serialize_mongo_doc(pattern) for pattern in patterns]
            
            return serialized_patterns
        except Exception as e:
            logger.error(f"MongoDB query error: {str(e)}")
            return []
            
    except Exception as e:
        logger.error(f"Error getting patterns: {str(e)}")
        return []

@api_router.get("/user-profile")
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get the current user's profile information"""
    try:
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in get_user_profile")
            raise HTTPException(status_code=401, detail="Invalid authentication")
            
        try:
            user_id = ObjectId(current_user["user_id"])
        except Exception as e:
            logger.error(f"Invalid user_id format: {current_user.get('user_id')}, error: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid authentication")
            
        # Get user data from the database
        user = db["users"].find_one({"_id": user_id})
        
        if not user:
            logger.error(f"User not found for ID: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
            
        # Serialize the user document
        serialized_user = serialize_mongo_doc(user)
        
        # Remove sensitive fields
        if "password" in serialized_user:
            serialized_user.pop("password")
        if "sessionToken" in serialized_user:
            serialized_user.pop("sessionToken")
            
        return serialized_user
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user profile")

# Input: 
#   - Authenticated user (from Depends(get_current_user))
#   - Optional dateUnix (int): filter playbooks by this date
#   - limit (int): max number of playbooks to return (default 1000, max 10000)
#   - skip (int): number of playbooks to skip (for pagination)
# Output:
#   - List of playbook documents (serialized), belonging to the current user, optionally filtered by date, paginated and limited.
@api_router.get("/playbooks")
async def get_playbooks(
    current_user: Dict[str, Any] = Depends(get_current_user),
    dateUnix: Optional[int] = None,
    limit: int = 1000,
    skip: int = 0
):
    """Get playbooks for the current user with optional date filtering"""
    logger.info(f"get_playbooks called with dateUnix={dateUnix}, limit={limit}, skip={skip}")
    
    try:
        # Ensure limit is reasonable
        if limit > 10000:
            logger.warning(f"Received very large limit value: {limit}, capping at 10000")
            limit = 10000
            
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in get_playbooks")
            return []
            
        try:
            user_id = ObjectId(current_user["user_id"])
        except Exception as e:
            logger.error(f"Invalid user_id format: {current_user.get('user_id')}, error: {str(e)}")
            return []
            
        query = {"user_id": user_id}
        
        # Add date filtering if provided
        if dateUnix:
            query["dateUnix"] = dateUnix
                
        # Log the final query for debugging
        logger.info(f"MongoDB query: {query}")
        
        try:
            # Check if the playbooks collection exists
            if "playbooks" not in db.list_collection_names():
                logger.warning("Playbooks collection does not exist in the database")
                return []
                
            # Execute the query
            playbooks = list(db["playbooks"].find(query).skip(skip).limit(limit).sort("dateUnix", -1))
            logger.info(f"Successfully retrieved {len(playbooks)} playbooks")
            
            # Use the helper function to serialize each playbook
            serialized_playbooks = [serialize_mongo_doc(playbook) for playbook in playbooks]
            
            return serialized_playbooks
        except Exception as e:
            logger.error(f"MongoDB query error: {str(e)}")
            return []
            
    except Exception as e:
        logger.error(f"Error getting playbooks: {str(e)}")
        return []

@api_router.post("/playbooks")
async def create_playbook(
    current_user: Dict[str, Any] = Depends(get_current_user),
    playbook_data: Dict[str, Any] = Body(...)
):
    """Create a new playbook entry"""
    logger.info(f"create_playbook called with data: {playbook_data}")
    
    try:
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in create_playbook")
            raise HTTPException(status_code=401, detail="Invalid authentication")
            
        try:
            user_id = ObjectId(current_user["user_id"])
        except Exception as e:
            logger.error(f"Invalid user_id format: {current_user.get('user_id')}, error: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid authentication")
            
        # Validate required fields
        required_fields = ["dateUnix", "playbook"]
        for field in required_fields:
            if field not in playbook_data:
                logger.error(f"Missing required field: {field}")
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Check if playbook with this date already exists
        existing = db["playbooks"].find_one({
            "user_id": user_id,
            "dateUnix": playbook_data["dateUnix"]
        })
        
        if existing:
            logger.warning(f"Playbook with dateUnix {playbook_data['dateUnix']} already exists")
            raise HTTPException(status_code=400, detail="Playbook with this date already exists")
            
        # Prepare document to insert
        now = datetime.now(timezone.utc)
        playbook_doc = {
            "user_id": user_id,
            "dateUnix": playbook_data["dateUnix"],
            "playbook": playbook_data["playbook"],
            "created_at": now,
            "updated_at": now
        }
        
        # Add date field if provided
        if "date" in playbook_data:
            playbook_doc["date"] = playbook_data["date"]
            
        # Add rules field if provided
        if "rules" in playbook_data:
            playbook_doc["rules"] = playbook_data["rules"]
            logger.info(f"Adding rules to playbook: {playbook_data['rules']}")
            
        # Add additional metadata fields if provided
        for field in ["name", "description", "icon", "color"]:
            if field in playbook_data:
                playbook_doc[field] = playbook_data[field]
            
        # Insert the document
        result = db["playbooks"].insert_one(playbook_doc)
        
        if not result.acknowledged:
            logger.error("Failed to insert playbook")
            raise HTTPException(status_code=500, detail="Failed to create playbook")
            
        logger.info(f"Successfully created playbook with ID: {result.inserted_id}")
        
        # Return the created playbook
        created_playbook = db["playbooks"].find_one({"_id": result.inserted_id})
        return serialize_mongo_doc(created_playbook)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error creating playbook: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create playbook")

# Endpoint for Playbook Missed Trades will go here
@api_router.put("/playbooks/{playbook_id}")
async def update_playbook(
    playbook_id: str,
    playbook_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update an existing playbook entry"""
    logger.info(f"update_playbook called for ID: {playbook_id}")
    
    try:
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in update_playbook")
            raise HTTPException(status_code=401, detail="Invalid authentication")
            
        try:
            user_id = ObjectId(current_user["user_id"])
            playbook_obj_id = ObjectId(playbook_id)
        except Exception as e:
            logger.error(f"Invalid ID format: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid ID format")
            
        # Find the playbook to update
        existing = db["playbooks"].find_one({
            "_id": playbook_obj_id,
            "user_id": user_id
        })
        
        if not existing:
            logger.error(f"Playbook not found or doesn't belong to user: {playbook_id}")
            raise HTTPException(status_code=404, detail="Playbook not found")
            
        # Prepare update document
        update_doc = {
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Add fields to update
        if "playbook" in playbook_data:
            update_doc["playbook"] = playbook_data["playbook"]
            
        if "dateUnix" in playbook_data:
            update_doc["dateUnix"] = playbook_data["dateUnix"]
            
        if "date" in playbook_data:
            update_doc["date"] = playbook_data["date"]
            
        # Add rules if present
        if "rules" in playbook_data:
            update_doc["rules"] = playbook_data["rules"]
            logger.info(f"Updating playbook rules: {playbook_data['rules']}")
            
        # Update the document
        result = db["playbooks"].update_one(
            {"_id": playbook_obj_id},
            {"$set": update_doc}
        )
        
        if result.matched_count == 0:
            logger.error(f"Playbook not found for update: {playbook_id}")
            raise HTTPException(status_code=404, detail="Playbook not found")
            
        logger.info(f"Successfully updated playbook: {playbook_id}")
        
        # Return the updated playbook
        updated_playbook = db["playbooks"].find_one({"_id": playbook_obj_id})
        return serialize_mongo_doc(updated_playbook)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error updating playbook: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update playbook")

@api_router.delete("/playbooks/{playbook_id}")
async def delete_playbook(
    playbook_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a playbook entry"""
    logger.info(f"delete_playbook called for ID: {playbook_id}")
    
    try:
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in delete_playbook")
            raise HTTPException(status_code=401, detail="Invalid authentication")
            
        try:
            user_id = ObjectId(current_user["user_id"])
            playbook_obj_id = ObjectId(playbook_id)
        except Exception as e:
            logger.error(f"Invalid ID format: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid ID format")
            
        # Find the playbook to delete
        existing = db["playbooks"].find_one({
            "_id": playbook_obj_id,
            "user_id": user_id
        })
        
        if not existing:
            logger.error(f"Playbook not found or doesn't belong to user: {playbook_id}")
            raise HTTPException(status_code=404, detail="Playbook not found")
            
        # Delete the document
        result = db["playbooks"].delete_one({
            "_id": playbook_obj_id,
            "user_id": user_id
        })
        
        if result.deleted_count == 0:
            logger.error(f"Failed to delete playbook: {playbook_id}")
            raise HTTPException(status_code=500, detail="Failed to delete playbook")
            
        logger.info(f"Successfully deleted playbook: {playbook_id}")
        
        return {"status": "success", "message": "Playbook deleted successfully"}
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error deleting playbook: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete playbook")

# Get a specific playbook by ID
@api_router.get("/playbooks/{playbook_id}")
async def get_playbook(
    playbook_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific playbook by ID"""
    logger.info(f"get_playbook called for ID: {playbook_id}")
    
    try:
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in get_playbook")
            raise HTTPException(status_code=401, detail="Invalid authentication")
            
        try:
            user_id = ObjectId(current_user["user_id"])
            playbook_obj_id = ObjectId(playbook_id)
        except Exception as e:
            logger.error(f"Invalid ID format: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid ID format")
            
        # Find the playbook
        playbook = db["playbooks"].find_one({
            "_id": playbook_obj_id,
            "user_id": user_id
        })
        
        if not playbook:
            logger.error(f"Playbook not found or doesn't belong to user: {playbook_id}")
            raise HTTPException(status_code=404, detail="Playbook not found")
            
        # Return the serialized playbook
        return serialize_mongo_doc(playbook)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting playbook: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve playbook")

@api_router.post("/playbook/tags")
async def save_playbook_tags(
    tag_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Save tags for a playbook"""
    logger.info(f"save_playbook_tags called with data: {tag_data}")
    
    try:
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in save_playbook_tags")
            raise HTTPException(status_code=401, detail="Invalid authentication")
            
        # Validate required fields
        required_fields = ["playbookId", "tags"]
        for field in required_fields:
            if field not in tag_data:
                logger.error(f"Missing required field: {field}")
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        try:
            user_id = ObjectId(current_user["user_id"])
            playbook_id = ObjectId(tag_data["playbookId"])
        except Exception as e:
            logger.error(f"Invalid ID format: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid ID format")
            
        # Check if the playbook exists and belongs to the user
        playbook = db["playbooks"].find_one({
            "_id": playbook_id,
            "user_id": user_id
        })
        
        if not playbook:
            logger.error(f"Playbook not found or doesn't belong to user: {tag_data['playbookId']}")
            raise HTTPException(status_code=404, detail="Playbook not found")
            
        # Check if tags entry already exists for this playbook
        existing = db["playbook_tags"].find_one({
            "playbook_id": playbook_id,
            "user_id": user_id
        })
        
        now = datetime.now(timezone.utc)
        
        if existing:
            # Update existing tags
            result = db["playbook_tags"].update_one(
                {"_id": existing["_id"]},
                {
                    "$set": {
                        "tags": tag_data["tags"],
                        "updated_at": now
                    }
                }
            )
            
            if not result.acknowledged:
                logger.error("Failed to update playbook tags")
                raise HTTPException(status_code=500, detail="Failed to update playbook tags")
                
            logger.info(f"Successfully updated tags for playbook: {tag_data['playbookId']}")
            
            # Return the updated tags document
            updated = db["playbook_tags"].find_one({"_id": existing["_id"]})
            return serialize_mongo_doc(updated)
        else:
            # Create new tags document
            new_tags = {
                "user_id": user_id,
                "playbook_id": playbook_id,
                "tags": tag_data["tags"],
                "created_at": now,
                "updated_at": now
            }
            
            result = db["playbook_tags"].insert_one(new_tags)
            
            if not result.acknowledged:
                logger.error("Failed to create playbook tags")
                raise HTTPException(status_code=500, detail="Failed to create playbook tags")
                
            logger.info(f"Successfully created tags for playbook: {tag_data['playbookId']}")
            
            # Return the created tags document
            created = db["playbook_tags"].find_one({"_id": result.inserted_id})
            return serialize_mongo_doc(created)
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error saving playbook tags: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save playbook tags")

@api_router.get("/playbook/{playbook_id}/tags")
async def get_playbook_tags(
    playbook_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get tags for a specific playbook by ID"""
    logger.info(f"get_playbook_tags called for ID: {playbook_id}")
    
    try:
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in get_playbook_tags")
            raise HTTPException(status_code=401, detail="Invalid authentication")
            
        try:
            user_id = ObjectId(current_user["user_id"])
            playbook_obj_id = ObjectId(playbook_id)
        except Exception as e:
            logger.error(f"Invalid ID format: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid ID format")
            
        # Find the playbook tags
        playbook_tags = db["playbook_tags"].find_one({
            "playbook_id": playbook_obj_id,
            "user_id": user_id
        })
        
        if not playbook_tags:
            # Return empty tags array if none found
            logger.info(f"No tags found for playbook: {playbook_id}")
            return {"tags": []}
            
        # Return the serialized playbook tags
        return serialize_mongo_doc(playbook_tags)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting playbook tags: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve playbook tags")

@api_router.get("/catalysts", response_model=List[Dict[str, Any]])
async def get_catalysts(
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = 10000,
    skip: int = 0
):
    """Get all market catalysts"""
    try:
        # Get catalysts from MongoDB
        catalysts = list(db["catalysts"].find().sort("date", -1).skip(skip).limit(limit))
        
        # Check if we have any results
        if not catalysts:
            # Fall back to file if MongoDB is empty
            if os.path.exists(CATALYSTS_FILE):
                with open(CATALYSTS_FILE, "r") as f:
                    file_catalysts = json.load(f)
                    
                if file_catalysts and len(file_catalysts) > 0:
                    # We found catalysts in the file, return them
                    return file_catalysts
        
        # Serialize MongoDB documents for JSON response
        return [serialize_mongo_doc(catalyst) for catalyst in catalysts]
    except Exception as e:
        logger.error(f"Error getting catalysts: {str(e)}")
        # Fall back to file if MongoDB query fails
        try:
            if os.path.exists(CATALYSTS_FILE):
                with open(CATALYSTS_FILE, "r") as f:
                    return json.load(f)
            return []
        except Exception as file_error:
            logger.error(f"Error reading catalysts file: {str(file_error)}")
            return []
        
@api_router.post("/catalysts", response_model=Dict[str, Any])
async def add_catalyst(
    catalyst_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Add a new market catalyst"""
    try:
        # Add user_id to the catalyst data
        user_id = ObjectId(current_user["user_id"])
        catalyst_data["user_id"] = user_id
        
        # Add timestamps
        catalyst_data["created_at"] = datetime.now(timezone.utc)
        catalyst_data["updated_at"] = datetime.now(timezone.utc)
        
        # Insert into MongoDB
        result = db["catalysts"].insert_one(catalyst_data)
        
        if not result.acknowledged:
            raise HTTPException(status_code=500, detail="Failed to add catalyst")
            
        # Get the inserted document
        inserted_catalyst = db["catalysts"].find_one({"_id": result.inserted_id})
        return serialize_mongo_doc(inserted_catalyst)
    except Exception as e:
        logger.error(f"Error adding catalyst: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add catalyst: {str(e)}")

@api_router.put("/catalysts/{catalyst_id}", response_model=Dict[str, Any])
async def update_catalyst(
    catalyst_id: str,
    catalyst_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a market catalyst"""
    try:
        # Convert ID to ObjectId
        try:
            catalyst_obj_id = ObjectId(catalyst_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid catalyst ID format")
            
        # Get user_id
        user_id = ObjectId(current_user["user_id"])
        
        # Find the catalyst to ensure it exists and belongs to the user
        existing = db["catalysts"].find_one({
            "_id": catalyst_obj_id,
            "user_id": user_id
        })
        
        if not existing:
            raise HTTPException(status_code=404, detail="Catalyst not found or doesn't belong to you")
            
        # Update the timestamp
        catalyst_data["updated_at"] = datetime.now(timezone.utc)
        
        # Ensure the user_id remains intact
        catalyst_data["user_id"] = user_id
        
        # Don't override the creation timestamp
        if "created_at" not in catalyst_data and "created_at" in existing:
            catalyst_data["created_at"] = existing["created_at"]
            
        # Update the catalyst
        result = db["catalysts"].update_one(
            {"_id": catalyst_obj_id},
            {"$set": catalyst_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Catalyst not found")
            
        # Get the updated document
        updated_catalyst = db["catalysts"].find_one({"_id": catalyst_obj_id})
        return serialize_mongo_doc(updated_catalyst)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating catalyst: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update catalyst: {str(e)}")
        
@api_router.delete("/catalysts/{catalyst_id}", response_model=Dict[str, str])
async def delete_catalyst(
    catalyst_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a market catalyst"""
    try:
        # Convert ID to ObjectId
        try:
            catalyst_obj_id = ObjectId(catalyst_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid catalyst ID format")
            
        # Get user_id
        user_id = ObjectId(current_user["user_id"])
        
        # Find the catalyst to ensure it exists and belongs to the user
        existing = db["catalysts"].find_one({
            "_id": catalyst_obj_id,
            "user_id": user_id
        })
        
        if not existing:
            raise HTTPException(status_code=404, detail="Catalyst not found or doesn't belong to you")
            
        # Delete the catalyst
        result = db["catalysts"].delete_one({
            "_id": catalyst_obj_id,
            "user_id": user_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=500, detail="Failed to delete catalyst")
            
        return {"status": "success", "message": "Catalyst deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting catalyst: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete catalyst: {str(e)}")

@api_router.post("/updateProfile")
async def update_profile(
    profile_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update the user's profile information including timezone preferences"""
    try:
        # Validate user_id before using it
        if not current_user or "user_id" not in current_user:
            logger.error("Missing or invalid user in update_profile")
            raise HTTPException(status_code=401, detail="Invalid authentication")
            
        try:
            user_id = ObjectId(current_user["user_id"])
        except Exception as e:
            logger.error(f"Invalid user_id format: {current_user.get('user_id')}, error: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid authentication")
        
        # Create update dictionary with allowed fields
        update_data = {}
        
        # Add timezone settings if provided
        if "timeZone" in profile_data:
            update_data["timeZone"] = profile_data["timeZone"]
            
        if "useDeviceTimeZone" in profile_data:
            update_data["useDeviceTimeZone"] = profile_data["useDeviceTimeZone"]
        
        # Only update if there's something to update
        if not update_data:
            logger.warning("No valid profile data provided for update")
            return {"status": "no_change"}
            
        # Update the user document
        result = db["users"].update_one(
            {"_id": user_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            logger.warning(f"Profile update for user {user_id} had no effect")
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating user profile: {str(e)}") 

@api_router.get("/stocks/tickers")
def get_stock_tickers():
    """Get all available stock tickers."""
    try:
        # Get the path to the tickers.json file
        base_dir = Path(__file__).resolve().parent.parent
        tickers_file = base_dir / "data" / "tickers.json"
        
        # Read the tickers from the file
        with open(tickers_file, "r") as f:
            tickers = json.load(f)
        
        return tickers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading tickers: {str(e)}"
        ) 

@api_router.post("/option/rolling")
async def option_rolling_endpoint(data: Dict[str, Any] = Body(...)):
    """Calculate option rolling (out, up, down) for a given option."""
    symbol = data.get('symbol')
    expiry = data.get('expiry')
    strike = data.get('strike')
    direction = data.get('direction')
    if not all([symbol, expiry, strike, direction]):
        raise HTTPException(status_code=400, detail="Missing required fields.")
    try:
        result = calculate_option_rolling(symbol, expiry, float(strike), direction)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 