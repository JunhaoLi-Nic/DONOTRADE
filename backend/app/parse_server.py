import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import hashlib
import random
import string
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Response, HTTPException, status
from bson import ObjectId

from .config import APP_ID, MASTER_KEY
from .database import db, rename_collection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router for Parse Server compatible API
parse_router = APIRouter(prefix="/parse")

# JSON encoder that can handle MongoDB ObjectId
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(MongoJSONEncoder, self).default(obj)

# Helper function to serialize MongoDB documents
def serialize_mongo_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MongoDB document to a JSON serializable format
    by converting ObjectId and other non-serializable types to strings
    """
    if doc is None:
        return None
        
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
    
    # For Parse compatibility, also provide objectId
    if "_id" in result and "objectId" not in result:
        result["objectId"] = result["_id"]
        
    return result

class ParseSchema:
    """A class to mimic Parse Server Schema functionality."""
    
    def __init__(self, class_name: str):
        self.class_name = class_name
        self.schema = {}
        self.fields = {}
        
    def add_string(self, field_name: str):
        self.fields[field_name] = {"type": "String"}
        
    def add_number(self, field_name: str):
        self.fields[field_name] = {"type": "Number"}
        
    def add_boolean(self, field_name: str):
        self.fields[field_name] = {"type": "Boolean"}
        
    def add_date(self, field_name: str):
        self.fields[field_name] = {"type": "Date"}
        
    def add_file(self, field_name: str):
        self.fields[field_name] = {"type": "File"}
        
    def add_geo_point(self, field_name: str):
        self.fields[field_name] = {"type": "GeoPoint"}
        
    def add_polygon(self, field_name: str):
        self.fields[field_name] = {"type": "Polygon"}
        
    def add_array(self, field_name: str):
        self.fields[field_name] = {"type": "Array"}
        
    def add_object(self, field_name: str):
        self.fields[field_name] = {"type": "Object"}
        
    def add_pointer(self, field_name: str, target_class: str):
        self.fields[field_name] = {
            "type": "Pointer", 
            "targetClass": target_class
        }
        
    def add_relation(self, field_name: str, target_class: str):
        self.fields[field_name] = {
            "type": "Relation", 
            "targetClass": target_class
        }
        
    def save(self):
        """Save schema to database"""
        logger.info(f"  --> Saving schema for class {self.class_name}")
        schema_collection = db["_SCHEMA"]
        
        # Create or update the schema document
        schema_doc = {
            "_id": self.class_name,
            "className": self.class_name,
            "fields": self.fields,
        }
        
        schema_collection.update_one(
            {"_id": self.class_name},
            {"$set": schema_doc},
            upsert=True
        )
        return schema_doc
        
    def update(self):
        """Update schema in database"""
        logger.info(f"  --> Updating schema for class {self.class_name}")
        return self.save()

class ParseServer:
    @staticmethod
    async def get_all_schemas() -> List[Dict[str, Any]]:
        """Get all schemas from the database"""
        schema_collection = db["_SCHEMA"]
        schemas = list(schema_collection.find({}))
        return schemas
    
    @staticmethod
    async def update_schemas(schema_file_path: str):
        """Update schemas from JSON file"""
        # Get existing schemas
        existing_schema = []
        schemas = await ParseServer.get_all_schemas()
        
        # Check for classes/collections that need to be renamed
        for schema in schemas:
            class_name = schema.get("className", "")
            if class_name in ["setupsEntries", "journals", "patternsMistakes"]:
                old_name = class_name
                new_name = ""
                
                if class_name == "setupsEntries":
                    new_name = "screenshots"
                elif class_name == "journals":
                    new_name = "diaries"
                elif class_name == "patternsMistakes":
                    new_name = "setups"
                    
                if new_name:
                    await rename_collection(old_name, new_name)
            else:
                existing_schema.append(class_name)
        
        # Read schema definitions from file
        schema_file = Path(schema_file_path)
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file_path}")
            return {"error": "Schema file not found"}
            
        with open(schema_file, 'r') as f:
            schemas_json = json.load(f)
        
        # Update or save schemas
        for schema_def in schemas_json:
            class_name = schema_def.get("className")
            if not class_name:
                continue
                
            logger.info(f" -> Upsert class/collection {class_name} in Parse Schema")
            fields = schema_def.get("fields", {})
            
            for key, field_def in fields.items():
                if key in ["objectId", "updatedAt", "createdAt", "ACL"]:
                    continue
                    
                schema = ParseSchema(class_name)
                field_type = field_def.get("type")
                
                if field_type == "String":
                    schema.add_string(key)
                elif field_type == "Number":
                    schema.add_number(key)
                elif field_type == "Boolean":
                    schema.add_boolean(key)
                elif field_type == "Date":
                    schema.add_date(key)
                elif field_type == "File":
                    schema.add_file(key)
                elif field_type == "GeoPoint":
                    schema.add_geo_point(key)
                elif field_type == "Polygon":
                    schema.add_polygon(key)
                elif field_type == "Array":
                    schema.add_array(key)
                elif field_type == "Object":
                    schema.add_object(key)
                elif field_type == "Pointer":
                    schema.add_pointer(key, field_def.get("targetClass", ""))
                elif field_type == "Relation":
                    schema.add_relation(key, field_def.get("targetClass", ""))
                
                if class_name in existing_schema:
                    schema.update()
                else:
                    schema.save()
                    if class_name not in existing_schema:
                        existing_schema.append(class_name)
        
        return {"existingSchema": existing_schema}

    @staticmethod
    async def get_all_users():
        """Get all users from the database"""
        users = list(db["_User"].find({}))
        return users 
    
    @staticmethod
    def generate_session_token():
        """Generate a random session token"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    
    @staticmethod
    def hash_password(password):
        """Hash a password for storage"""
        return hashlib.sha256(password.encode()).hexdigest()

# Parse Server compatible endpoints

@parse_router.post("/login")
async def login(request: Request):
    """Handle Parse login request"""
    try:
        # Debug logging
        logger.info(f"Parse Login request received")
        logger.info(f"Headers: {request.headers}")
        
        data = await request.json()
        logger.info(f"Request data: {data}")
        
        username = data.get("username")
        password = data.get("password")
        app_id = data.get("_ApplicationId")
        
        # Check if the app ID is valid (not an [object Object] string)
        if app_id == "[object Object]" or not app_id:
            # This means the Parse client is not sending the app ID correctly
            logger.warning(f"Invalid app ID received: {app_id}")
            # Use the APP_ID from our config instead
            app_id = APP_ID
            logger.info(f"Using server config APP_ID: {app_id}")
        
        if not username or not password:
            error_response = {
                "code": 200,
                "error": "Invalid username/password"
            }
            logger.error(f"Missing username or password: username={username}, password={'*' * len(password) if password else None}")
            return Response(
                content=json.dumps(error_response),
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="application/json"
            )
            
        # Find user by username/email
        user = db["_User"].find_one({
            "$or": [
                {"username": username},
                {"email": username}
            ]
        })
        
        if not user:
            logger.error(f"User not found: {username}")
            error_response = {
                "code": 101,
                "error": "Invalid username/password"
            }
            return Response(
                content=json.dumps(error_response),
                status_code=status.HTTP_404_NOT_FOUND,
                media_type="application/json"
            )
            
        # Check password
        hashed_password = ParseServer.hash_password(password)
        if user.get("password") != hashed_password:
            logger.error(f"Invalid password for user: {username}")
            error_response = {
                "code": 101,
                "error": "Invalid username/password"
            }
            return Response(
                content=json.dumps(error_response),
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
            
        # Generate session token
        session_token = ParseServer.generate_session_token()
        logger.info(f"Login successful for user: {username}")
        
        # Update user with session token
        db["_User"].update_one(
            {"_id": user["_id"]},
            {"$set": {"sessionToken": session_token, "updatedAt": datetime.now(timezone.utc)}}
        )
        
        # Prepare Parse Server format response
        response_data = {
            "objectId": str(user["_id"]),
            "username": user.get("username"),
            "email": user.get("email"),
            "timeZone": user.get("timeZone", "America/New_York"),
            "createdAt": user.get("createdAt").isoformat() if isinstance(user.get("createdAt"), datetime) else user.get("createdAt"),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "sessionToken": session_token,
            "ACL": user.get("ACL", {})
        }
        
        # Add any additional user fields
        for key, value in user.items():
            if key not in ["_id", "password", "username", "email", "createdAt", "updatedAt", "sessionToken", "ACL", "timeZone"]:
                if isinstance(value, ObjectId):
                    response_data[key] = str(value)
                elif isinstance(value, datetime):
                    response_data[key] = value.isoformat()
                else:
                    response_data[key] = value
        
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,HEAD,OPTIONS,POST,PUT",
            "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept, X-Parse-Application-Id, X-Parse-REST-API-Key, X-Parse-Session-Token",
            "X-Parse-Application-Id": APP_ID
        }
        
        return Response(
            content=json.dumps(response_data),
            status_code=status.HTTP_200_OK,
            media_type="application/json",
            headers=headers
        )
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response(
            content=json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )

@parse_router.post("/users")
async def create_user(request: Request):
    """Handle Parse user creation request"""
    try:
        # Log the headers
        logger.info(f"User creation request received")
        logger.info(f"Headers: {request.headers}")
        
        data = await request.json()
        logger.info(f"Request data: {data}")
        
        username = data.get("username")
        password = data.get("password")
        email = data.get("email", username)  # Use username as email if not provided
        timezone = data.get("timeZone", "America/New_York")  # Default timezone
        
        if not username or not password:
            logger.error(f"Missing required fields: username={username}, password={'*' * len(password) if password else None}")
            return Response(
                content=json.dumps({"error": "Username and password are required"}),
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="application/json"
            )
            
        # Check if username already exists
        existing_user = db["_User"].find_one({"username": username})
        if existing_user:
            logger.info(f" -> User already exists: {username}")
            return Response(
                content=json.dumps({"error": "Username already exists"}),
                status_code=status.HTTP_409_CONFLICT,
                media_type="application/json"
            )
            
        # Check if email already exists if provided
        if email:
            existing_email = db["_User"].find_one({"email": email})
            if existing_email:
                logger.info(f" -> Email already exists: {email}")
                return Response(
                    content=json.dumps({"error": "Email already exists"}),
                    status_code=status.HTTP_409_CONFLICT,
                    media_type="application/json"
                )
        
        # Hash password and generate session token
        hashed_password = ParseServer.hash_password(password)
        session_token = ParseServer.generate_session_token()
        
        # Create user document
        now = datetime.now(timezone.utc)
        user = {
            "username": username,
            "password": hashed_password,
            "email": email,
            "sessionToken": session_token,
            "timeZone": timezone,
            "createdAt": now,
            "updatedAt": now
        }
        
        # Insert user into database
        result = db["_User"].insert_one(user)
        logger.info(f" -> Created user with id {result.inserted_id}")
        
        # Prepare response
        user_response = {
            "objectId": str(result.inserted_id),
            "username": username,
            "email": email,
            "timeZone": timezone,
            "sessionToken": session_token,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat()
        }
        
        return Response(
            content=json.dumps(user_response),
            status_code=status.HTTP_201_CREATED,
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Create user error: {str(e)}")
        return Response(
            content=json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )

@parse_router.get("/users/me")
async def get_current_user(request: Request):
    """Get the current user based on session token"""
    try:
        # Get session token from request headers
        auth_header = request.headers.get("X-Parse-Session-Token")
        
        if not auth_header:
            return Response(
                content=json.dumps({"error": "Session token is required"}),
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
            
        # Find user by session token
        user = db["_User"].find_one({"sessionToken": auth_header})
        
        if not user:
            return Response(
                content=json.dumps({"error": "Invalid session token"}),
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
            
        # Return user data without password
        if "password" in user:
            del user["password"]
            
        # Convert ObjectId to string and format dates
        user["objectId"] = str(user["_id"])
        if "createdAt" in user:
            user["createdAt"] = user["createdAt"].isoformat() if isinstance(user["createdAt"], datetime) else user["createdAt"]
        if "updatedAt" in user:
            user["updatedAt"] = user["updatedAt"].isoformat() if isinstance(user["updatedAt"], datetime) else user["updatedAt"]
        
        return Response(
            content=json.dumps(user),
            status_code=status.HTTP_200_OK,
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )

@parse_router.post("/logout")
async def logout(request: Request):
    """Handle Parse logout request"""
    try:
        # Get session token from request headers
        auth_header = request.headers.get("X-Parse-Session-Token")
        
        if auth_header:
            # Remove session token from user
            db["_User"].update_one(
                {"sessionToken": auth_header},
                {"$unset": {"sessionToken": ""}}
            )
            
        return Response(
            content=json.dumps({}),
            status_code=status.HTTP_200_OK,
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )

# General object CRUD endpoints
@parse_router.get("/classes/{class_name}")
async def get_objects(class_name: str, request: Request):
    """Get objects from a Parse class/collection"""
    try:
        # Parse query parameters
        limit = request.query_params.get("limit")
        skip = request.query_params.get("skip")
        where = request.query_params.get("where")
        order = request.query_params.get("order")
        
        # Build query
        query = {}
        if where:
            try:
                query = json.loads(where)
            except json.JSONDecodeError:
                pass
            
        # Build options
        options = {}
        if limit:
            try:
                options["limit"] = int(limit)
            except ValueError:
                pass
                
        if skip:
            try:
                options["skip"] = int(skip)
            except ValueError:
                pass
                
        if order:
            sort_order = []
            for field in order.split(","):
                if field.startswith("-"):
                    sort_order.append((field[1:], -1))
                else:
                    sort_order.append((field, 1))
            options["sort"] = sort_order
            
        # Convert any objectId strings to ObjectId
        if "objectId" in query:
            try:
                query["_id"] = ObjectId(query.pop("objectId"))
            except Exception:
                pass
        
        # Execute query
        collection = db[class_name]
        results = list(collection.find(query, **options))
        
        # Serialize results
        serialized_results = [serialize_mongo_doc(doc) for doc in results]
        response_data = {"results": serialized_results}
        
        return Response(
            content=json.dumps(response_data, cls=MongoJSONEncoder),
            status_code=status.HTTP_200_OK,
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Get objects error for class {class_name}: {str(e)}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )

@parse_router.get("/classes/{class_name}/{object_id}")
async def get_object(class_name: str, object_id: str):
    """Get a specific object from a Parse class/collection by ID"""
    try:
        # Convert string ID to ObjectId
        try:
            obj_id = ObjectId(object_id)
        except Exception:
            return Response(
                content=json.dumps({"error": "Invalid object ID"}),
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="application/json"
            )
            
        # Find the object
        collection = db[class_name]
        obj = collection.find_one({"_id": obj_id})
        
        if not obj:
            return Response(
                content=json.dumps({"error": "Object not found"}),
                status_code=status.HTTP_404_NOT_FOUND,
                media_type="application/json"
            )
            
        # Serialize and return the object
        serialized_obj = serialize_mongo_doc(obj)
        
        return Response(
            content=json.dumps(serialized_obj, cls=MongoJSONEncoder),
            status_code=status.HTTP_200_OK,
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Get object error for class {class_name}, ID {object_id}: {str(e)}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )

@parse_router.post("/classes/{class_name}")
async def create_object(class_name: str, request: Request):
    """Create a new object in a Parse class/collection"""
    try:
        # Get request data
        data = await request.json()
        
        # Add createdAt and updatedAt timestamps
        now = datetime.now(timezone.utc)
        data["createdAt"] = now
        data["updatedAt"] = now
        
        # Insert the object
        collection = db[class_name]
        result = collection.insert_one(data)
        
        # Return the created object ID
        response_data = {
            "objectId": str(result.inserted_id),
            "createdAt": now.isoformat()
        }
        
        return Response(
            content=json.dumps(response_data),
            status_code=status.HTTP_201_CREATED,
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Create object error for class {class_name}: {str(e)}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )

@parse_router.put("/classes/{class_name}/{object_id}")
async def update_object(class_name: str, object_id: str, request: Request):
    """Update an object in a Parse class/collection"""
    try:
        # Get request data
        data = await request.json()
        
        # Convert string ID to ObjectId
        try:
            obj_id = ObjectId(object_id)
        except Exception:
            return Response(
                content=json.dumps({"error": "Invalid object ID"}),
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="application/json"
            )
            
        # Add updatedAt timestamp
        now = datetime.now(timezone.utc)
        data["updatedAt"] = now
        
        # Update the object
        collection = db[class_name]
        result = collection.update_one({"_id": obj_id}, {"$set": data})
        
        if result.matched_count == 0:
            return Response(
                content=json.dumps({"error": "Object not found"}),
                status_code=status.HTTP_404_NOT_FOUND,
                media_type="application/json"
            )
            
        # Return success
        response_data = {
            "updatedAt": now.isoformat()
        }
        
        return Response(
            content=json.dumps(response_data),
            status_code=status.HTTP_200_OK,
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Update object error for class {class_name}, ID {object_id}: {str(e)}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )

@parse_router.delete("/classes/{class_name}/{object_id}")
async def delete_object(class_name: str, object_id: str):
    """Delete an object from a Parse class/collection"""
    try:
        # Convert string ID to ObjectId
        try:
            obj_id = ObjectId(object_id)
        except Exception:
            return Response(
                content=json.dumps({"error": "Invalid object ID"}),
                status_code=status.HTTP_400_BAD_REQUEST,
                media_type="application/json"
            )
            
        # Delete the object
        collection = db[class_name]
        result = collection.delete_one({"_id": obj_id})
        
        if result.deleted_count == 0:
            return Response(
                content=json.dumps({"error": "Object not found"}),
                status_code=status.HTTP_404_NOT_FOUND,
                media_type="application/json"
            )
            
        # Return success
        return Response(
            content=json.dumps({}),
            status_code=status.HTTP_200_OK,
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Delete object error for class {class_name}, ID {object_id}: {str(e)}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )

# Debug endpoint to list all registered routes
@parse_router.get("/debug-routes")
async def debug_routes():
    """Debug endpoint to list all registered routes"""
    routes = []
    for route in parse_router.routes:
        routes.append({
            "path": route.path,
            "name": route.name,
            "methods": list(route.methods) if route.methods else []
        })
    return {"routes": routes}

# Handle OPTIONS requests for all Parse routes
@parse_router.options("/{path:path}")
async def parse_options(path: str):
    """Handle OPTIONS requests for all Parse routes"""
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,HEAD,OPTIONS,POST,PUT,DELETE",
        "Access-Control-Allow-Headers": "Origin, X-Requested-With, Content-Type, Accept, X-Parse-Application-Id, X-Parse-REST-API-Key, X-Parse-Session-Token, X-Parse-Master-Key",
        "Access-Control-Max-Age": "86400",  # 24 hours
    }
    return Response(
        content="",
        status_code=200,
        headers=headers
    ) 