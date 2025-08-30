from fastapi import APIRouter, HTTPException, Depends, Body, Response, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId

from ..database import db
from ..auth import (
    hash_password, verify_password, create_jwt_token, 
    get_current_user, serialize_user
)

import logging
logger = logging.getLogger(__name__)

# Create router without prefix (prefix is set in main.py)
auth_router = APIRouter()

@auth_router.post("/register")
async def register(user_data: Dict[str, Any] = Body(...)):
    """Register a new user"""
    logger.info(f"Register request received")
    
    # Extract fields from request
    email = user_data.get("email")
    password = user_data.get("password")
    username = user_data.get("username", email)  # Use email as username if not provided
    
    # Validate required fields
    if not email or not password:
        logger.warning(f"Missing required fields for registration")
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    # Check if user already exists
    existing_user = db["users"].find_one({"email": email})
    if existing_user:
        logger.warning(f"User already exists: {email}")
        raise HTTPException(status_code=409, detail="Email already registered")
        
    # Create user object
    now = datetime.now(timezone.utc)
    new_user = {
        "email": email,
        "username": username,
        "password": hash_password(password),
        "timeZone": user_data.get("timeZone", "America/New_York"),
        "created_at": now,
        "updated_at": now
    }
    
    # Insert user
    try:
        result = db["users"].insert_one(new_user)
        user_id = str(result.inserted_id)
        logger.info(f"Created user with ID: {user_id}")
        
        # Create token
        token = create_jwt_token(user_id)
        
        # Get the created user
        user = db["users"].find_one({"_id": ObjectId(user_id)})
        
        # Return user data and token
        return {
            "token": token,
            "user": serialize_user(user)
        }
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@auth_router.post("/login")
async def login(credentials: Dict[str, Any] = Body(...)):
    """Login a user"""
    logger.info(f"Login request received")
    
    # Extract credentials
    email = credentials.get("email")
    password = credentials.get("password")
    
    if not email or not password:
        logger.warning("Missing email or password")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Email and password are required"}
        )
    
    # Find user
    user = db["users"].find_one({"email": email})
    if not user:
        logger.warning(f"User not found: {email}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid email or password"}
        )
    
    # Verify password
    if not verify_password(password, user["password"]):
        logger.warning(f"Invalid password for user: {email}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid email or password"}
        )
    
    # Create token
    user_id = str(user["_id"])
    token = create_jwt_token(user_id)
    
    # Update last login
    db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )
    
    logger.info(f"User logged in: {email}")
    
    # Return user data and token
    return {
        "token": token,
        "user": serialize_user(user)
    }

@auth_router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user profile"""
    user_id = current_user["user_id"]
    
    user = db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return serialize_user(user)

@auth_router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Logout a user - clears the session server-side"""
    # Note: JWT tokens can't be invalidated directly
    # For a real implementation, you'd use a token blocklist or short-lived tokens + refresh tokens
    
    return {"message": "Logged out successfully"}

@auth_router.post("/change-password")
async def change_password(
    password_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Change user's password"""
    user_id = current_user["user_id"]
    old_password = password_data.get("old_password")
    new_password = password_data.get("new_password")
    
    if not old_password or not new_password:
        raise HTTPException(
            status_code=400, 
            detail="Old password and new password are required"
        )
    
    # Get user
    user = db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify old password
    if not verify_password(old_password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid old password")
    
    # Update password
    hashed_new_password = hash_password(new_password)
    db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password": hashed_new_password, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Password updated successfully"} 