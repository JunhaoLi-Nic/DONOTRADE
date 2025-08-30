import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
import secrets
import string
import logging
from .config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from .database import db
from bson import ObjectId

# Configure logging
logger = logging.getLogger(__name__)

# Settings 
SECRET_KEY = JWT_SECRET
ALGORITHM = JWT_ALGORITHM
TOKEN_EXPIRE_MINUTES = JWT_EXPIRE_MINUTES

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme for token extraction
security = HTTPBearer(auto_error=False)

# Helper functions
def hash_password(password: str) -> str:
    """Hash a password for storage"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False

def create_jwt_token(user_id: str) -> str:
    """Create a JWT token for authentication"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def generate_random_string(length=32):
    """Generate a random string for secure tokens"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Dependency for protected routes
async def get_current_user(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    """
    Extract and validate the user from JWT token or session token.
    Supports both formats to ease migration:
    1. Bearer JWT tokens
    2. Session tokens stored in user document (Parse Server compatibility)
    """
    try:
        # First check for standard Authorization header
        token = None
        if credentials:
            token = credentials.credentials
            logger.info(f"Token from credentials: {token[:10]}...")
        else:
            # Get from Authorization header as fallback
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                logger.info(f"Token from Authorization header: {token[:10]}...")
            
        if not token:
            logger.warning("No token provided in request")
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Try JWT token first
        try:
            logger.info(f"Attempting to decode JWT token")
            payload = decode_jwt_token(token)
            user_id = payload.get("sub")
            if user_id:
                # Valid JWT token, verify user exists
                logger.info(f"JWT token valid, looking up user: {user_id}")
                user = db["users"].find_one({"_id": ObjectId(user_id)})
                if not user:
                    logger.warning(f"User not found for id: {user_id}")
                    raise HTTPException(status_code=401, detail="User not found")
                logger.info(f"User authenticated: {user.get('email', 'unknown')}")
                return {"user_id": user_id, "token": token, "user": user}
        except HTTPException:
            # Re-raise HTTP exceptions from decode_jwt_token
            raise
        except Exception as e:
            logger.info(f"JWT decode failed, trying session token: {str(e)}")
            # Not a valid JWT token, try session token (Parse Server compatibility)
            user = db["users"].find_one({"sessionToken": token})
            if not user:
                logger.warning("Invalid token - not a valid JWT or session token")
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Convert ObjectId to string for consistent handling
            user_id = str(user["_id"])
            logger.info(f"User authenticated via session token: {user.get('email', 'unknown')}")
            return {"user_id": user_id, "token": token, "user": user}
            
        # If we reach here, neither authentication worked
        logger.warning("Authentication failed after trying both JWT and session token")
        raise HTTPException(status_code=401, detail="Authentication failed")
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication error")

# Dependency for optional authentication
async def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user if token exists, otherwise return None"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
            
        token = auth_header.split(" ")[1]
        
        # Try JWT token first
        try:
            payload = decode_jwt_token(token)
            user_id = payload.get("sub")
            if user_id:
                user = db["users"].find_one({"_id": ObjectId(user_id)})
                if user:
                    return {"user_id": user_id, "token": token, "user": user}
        except Exception:
            # Try session token
            user = db["users"].find_one({"sessionToken": token})
            if user:
                return {"user_id": str(user["_id"]), "token": token, "user": user}
                
        return None
    except Exception:
        return None

def serialize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """Convert user document to API response format"""
    result = {
        "id": str(user["_id"]),
        "email": user.get("email", ""),
        "username": user.get("username", ""),
        "timeZone": user.get("timeZone", "America/New_York"),
        "createdAt": user.get("created_at", datetime.now(timezone.utc)).isoformat(),
    }
    
    # Add any additional fields (but exclude sensitive ones)
    for key, value in user.items():
        if key not in ["_id", "password", "created_at", "email", "username", "timeZone"]:
            result[key] = value
            
    return result