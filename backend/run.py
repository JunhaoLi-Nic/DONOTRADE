#!/usr/bin/env python
import uvicorn
import logging
import os
import sys
import argparse
from app.config import PORT, NODE_ENV

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def print_separator(title):
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50)

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="TradeNote Backend Server")
    parser.add_argument("--port", type=int, default=PORT, 
                        help=f"Port to run the server on (default: {PORT})")
    args = parser.parse_args()
    
    # Use the specified port instead of the default
    server_port = args.port
    
    try:
        # Display configuration info
        print_separator("TradeNote Configuration")
        mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/tradenote")
        # Hide password in logs
        masked_uri = mongo_uri
        if "@" in mongo_uri:
            parts = mongo_uri.split("@")
            auth_part = parts[0]
            if ":" in auth_part:
                user_part = auth_part.split(":", 1)[0]
                masked_uri = f"{user_part}:***@{parts[1]}"
        
        print(f"MongoDB URI: {masked_uri}")
        print(f"App ID: {os.environ.get('APP_ID', '123456')}")
        print(f"Port: {server_port}")
        print(f"Environment: {NODE_ENV}")
        print(f"Database: {os.environ.get('MONGODB_DATABASE', 'tradenote')}")
        print("=" * 30)
        
        logger.info("\nSTARTING PYTHON SERVER")
        logger.info(f" -> TradeNote server started on http://localhost:{server_port}")
        
        # Run the server
        uvicorn.run(
            "app.main:app", 
            host="0.0.0.0", 
            port=server_port,
            reload=NODE_ENV == 'dev',
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 