from fastapi import APIRouter, Request, Response, Depends, HTTPException, status, Body
from fastapi.responses import JSONResponse
import httpx
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import base64
import sys
from pathlib import Path

# Add backend directory to path to enable imports
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
from .config import (
    APP_ID, MASTER_KEY, STRIPE_SK, STRIPE_PK, STRIPE_PRICE_ID, 
    STRIPE_TRIAL_PERIOD, NODE_ENV, REGISTER_OFF, ANALYTICS_OFF, 
    UPSERT_SCHEMA, TRADENOTE_PORT
)
from .database import db
from .parse_server import ParseServer
from .services.trades import get_time_zone, get_existing_trades_array, import_trades, upload_trades, globals as trade_globals

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api")

# Import stripe if available
stripe = None
if STRIPE_SK:
    try:
        import stripe as stripe_module
        stripe = stripe_module
        stripe.api_key = STRIPE_SK
    except ImportError:
        logger.warning("Stripe module not available")

# ------------------ API Routes ------------------

@router.post("/parseAppId")
async def get_parse_app_id():
    """Return the Parse App ID"""
    logger.info("API: post APP ID")
    # Ensure we return a string value, not an object
    return {"app_id": str(APP_ID)}

@router.post("/registerPage")
async def register_page():
    """Return the registration page status"""
    logger.info("API: post REGISTER_OFF")
    # Convert string to boolean
    register_off = REGISTER_OFF.lower() == "true"
    return register_off

@router.post("/posthog")
async def posthog():
    """Return PostHog analytics status"""
    logger.info("API: posthog")
    if ANALYTICS_OFF:
        return "off"
    else:
        return "phc_FxkjH1O898jKu0yiELC3aWKda3vGov7waGN0weU5kw0"

@router.post("/checkCloudPayment")
async def check_cloud_payment(current_user: Dict[str, Any] = Body(...)):
    """Check if user has valid payment/subscription"""
    if not STRIPE_SK:
        return Response(status_code=status.HTTP_200_OK)
    
    logger.info("API: checkCloudPayment")
    
    # Check if user has a payment service with subscription
    if "paymentService" in current_user and "subscriptionId" in current_user["paymentService"]:
        # If yes, check subscription status
        active_subscription_statuses = ['active', 'trialing', 'past_due']
        subscription = stripe.Subscription.retrieve(current_user["paymentService"]["subscriptionId"])
        
        if subscription.status in active_subscription_statuses:
            logger.info(" -> User has valid subscription.")
            return Response(status_code=status.HTTP_200_OK)
        else:
            logger.info(" -> User has invalid subscription.")
            return Response(status_code=status.HTTP_403_FORBIDDEN)
    else:
        # If not, check if user is within trial period
        created_at_date = datetime.fromisoformat(current_user["createdAt"].replace("Z", "+00:00"))
        current_date = datetime.utcnow()
        time_difference = current_date - created_at_date
        difference_in_days = time_difference.total_seconds() / (24 * 60 * 60)
        
        if difference_in_days > STRIPE_TRIAL_PERIOD:
            logger.info(" -> User is past trial period.")
            return Response(status_code=status.HTTP_403_FORBIDDEN)
        else:
            logger.info(" -> User is within trial period.")
            return Response(status_code=status.HTTP_200_OK)

@router.post("/create-checkout-session")
async def create_checkout_session():
    """Create a Stripe checkout session"""
    if not stripe:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, 
                           detail="Stripe integration not available")
    
    return_url = f"http://localhost:{TRADENOTE_PORT}/checkoutSuccess?session_id={{CHECKOUT_SESSION_ID}}"
    if NODE_ENV != 'dev':
        return_url = "https://app.tradenote.co/checkoutSuccess?session_id={CHECKOUT_SESSION_ID}"
    
    session = stripe.checkout.Session.create(
        ui_mode='embedded',
        line_items=[{
            "price": STRIPE_PRICE_ID,
            "quantity": 1,
        }],
        mode='subscription',
        return_url=return_url,
        automatic_tax={"enabled": True},
    )
    
    return {"clientSecret": session.client_secret}

@router.get("/getStripePk")
async def get_stripe_pk():
    """Return the Stripe public key"""
    return STRIPE_PK

@router.get("/session-status")
async def session_status(session_id: str):
    """Get Stripe session status"""
    if not stripe:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, 
                           detail="Stripe integration not available")
    
    try:
        logger.info("Getting session status")
        session = stripe.checkout.Session.retrieve(session_id)
        
        return {
            "session": session,
            "status": session.status,
            "customer_email": session.customer_details.email,
            "customer_id": session.customer
        }
    except Exception as e:
        logger.error(f"Error retrieving session: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                           detail=str(e))

@router.get("/dockerVersion")
async def docker_version():
    """Get Docker version from Docker Hub"""
    logger.info("Getting Docker Version")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://hub.docker.com/v2/namespaces/eleventrading/repositories/tradenote/tags"
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error getting Docker version: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                               detail=str(e))

@router.post("/updateSchemas")
async def update_schemas():
    """Update schemas from requiredClasses.json file"""
    if STRIPE_SK and not UPSERT_SCHEMA:
        return Response(status_code=status.HTTP_200_OK)
    
    logger.info("API: post update schema")
    result = await ParseServer.update_schemas("requiredClasses.json")
    return result

# Middleware to validate API key
async def validate_api_key(request: Request):
    """Validate the API key from headers or query parameters"""
    users = await ParseServer.get_all_users()
    target_key = request.headers.get('api-key') or request.query_params.get('api-key')
    
    logger.info(f" -> target Key {target_key}")
    
    # Check if key exists in any user's APIs
    current_user = None
    for user in users:
        if "apis" in user:
            for api in user["apis"]:
                if api.get("key") == target_key:
                    current_user = user
                    break
        if current_user:
            break
    
    if current_user:
        logger.info(" -> Valid api key found :)")
        return current_user
    else:
        logger.info(" -> Invalid api key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

@router.post("/trades")
async def trades(data: Dict[str, Any], current_user: Dict = Depends(validate_api_key)):
    """API endpoint to import trades"""
    try:
        if not data or not data.get("data") or len(data.get("data", [])) == 0:
            return " -> No trades to import"
        
        # Set global variables
        trade_globals.current_user = current_user
        trade_globals.upload_mfe_prices = data.get("uploadMfePrices", False)
        
        # Call the trade processing functions
        await get_time_zone()
        await get_existing_trades_array("api")
        await import_trades(data["data"], "api", data.get("selectedBroker", "default"))
        result = await upload_trades("api")
        
        return " -> Saved Trades to MongoDB"
    except Exception as e:
        logger.error(f"Error creating executions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating executions: {str(e)}"
        )

@router.post("/databento")
async def databento(data: Dict[str, Any]):
    """API endpoint to proxy requests to Databento API"""
    try:
        username = data.get("username", "")
        password = ''
        
        auth_header = f"Basic {base64.b64encode(f'{username}:{password}'.encode()).decode()}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://hist.databento.com/v0/timeseries.get_range",
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': auth_header
                },
                data=data
            )
            return response.json()
    except Exception as e:
        logger.error(f"Error with Databento API: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 

@router.post("/create-test-user")
async def create_test_user():
    """Create a test user in the database"""
    logger.info("API: create test user")
    
    # Check if user already exists
    existing_user = db["_User"].find_one({"username": "test@example.com"})
    if existing_user:
        logger.info(" -> Test user already exists")
        return {"status": "exists", "message": "Test user already exists"}
    
    # Create user with hashed password
    from .parse_server import ParseServer
    hashed_password = ParseServer.hash_password("password123")
    user = {
        "username": "test@example.com",
        "email": "test@example.com",
        "password": hashed_password,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    
    # Insert the user
    result = db["_User"].insert_one(user)
    logger.info(f" -> Created test user with id {result.inserted_id}")
    
    return {"status": "created", "userId": str(result.inserted_id)}

@router.get("/connection-test")
async def connection_test():
    """Simple endpoint to test connection between frontend and backend"""
    logger.info("API: connection test endpoint called")
    return {"status": "success", "message": "Backend connection is working!"}

@router.get("/test-mongodb")
async def test_mongodb():
    """Test MongoDB connection and operations"""
    logger.info("API: testing MongoDB operations")
    
    try:
        # Test writing to MongoDB
        test_collection = db["_test_collection"]
        test_id = str(datetime.now().timestamp())
        write_result = test_collection.insert_one({
            "test_id": test_id,
            "created_at": datetime.now(timezone.utc),
            "message": "Test document"
        })
        
        # Test reading from MongoDB
        read_result = test_collection.find_one({"test_id": test_id})
        
        # Check if user collection exists and has documents
        user_count = db["_User"].count_documents({})
        
        return {
            "status": "success",
            "write_result": {
                "acknowledged": write_result.acknowledged,
                "inserted_id": str(write_result.inserted_id)
            },
            "read_result": {
                "found": read_result is not None,
                "test_id": read_result.get("test_id") if read_result else None
            },
            "collections": {
                "users": {
                    "count": user_count
                }
            }
        }
    except Exception as e:
        logger.error(f"MongoDB test error: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

@router.get("/debug-parse-server")
async def debug_parse_server():
    """Debug endpoint for Parse Server connection"""
    logger.info("API: debug Parse Server connection")
    try:
        # Check app configuration
        parse_config = {
            "app_id": str(APP_ID),
            "app_id_type": type(APP_ID).__name__,
        }
        
        # Check database connection
        db_status = "connected" if db.client.admin.command('ping').get('ok') == 1.0 else "disconnected"
        
        # Check user collection
        user_count = db["_User"].count_documents({})
        
        return {
            "status": "success",
            "parse_config": parse_config,
            "db_status": db_status,
            "user_count": user_count
        }
    except Exception as e:
        logger.error(f"Debug Parse Server error: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        } 