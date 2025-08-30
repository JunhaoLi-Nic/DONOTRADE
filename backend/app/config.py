import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# but use hardcoded defaults if environment variables are not set
try:
    load_dotenv()
except:
    pass

# Parse Server configuration
APP_ID = os.getenv("APP_ID", "123456")
MASTER_KEY = os.getenv("MASTER_KEY", "123456")

# MongoDB configuration - Use direct connection to localhost by default
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/tradenote")
MONGO_USER = os.getenv("MONGO_USER", "")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_URL = os.getenv("MONGO_URL", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
TRADENOTE_DATABASE = os.getenv("TRADENOTE_DATABASE", "tradenote")

# Stripe configuration
STRIPE_SK = os.getenv("STRIPE_SK", "")
STRIPE_PK = os.getenv("STRIPE_PK", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
STRIPE_TRIAL_PERIOD = int(os.getenv("STRIPE_TRIAL_PERIOD", "0"))

# Application settings
PORT = int(os.getenv("TRADENOTE_PORT", 3002))  # Changed from 3001 to 3002
NODE_ENV = os.getenv("NODE_ENV", "production")  # Default to production mode for serving frontend
REGISTER_OFF = os.getenv("REGISTER_OFF", "false")
ANALYTICS_OFF = os.getenv("ANALYTICS_OFF", "true")
UPSERT_SCHEMA = os.getenv("UPSERT_SCHEMA", "true")
PARSE_DASHBOARD = os.getenv("PARSE_DASHBOARD", "false")

# JWT Authentication
JWT_SECRET = os.environ.get("JWT_SECRET", "YOUR_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", 60 * 24 * 7))  # 7 days by default

# Registration
REGISTRATION_ENABLED = os.environ.get("REGISTRATION_ENABLED", "true").lower() == "true"

# Analytics
POSTHOG_API_KEY = os.environ.get("POSTHOG_API_KEY", "")
POSTHOG_HOST = os.environ.get("POSTHOG_HOST", "https://app.posthog.com")

# Construct database URI if not provided directly
if not MONGO_URI or MONGO_URI == "mongodb://localhost:27017/tradenote":
    if os.getenv("MONGO_ATLAS"):
        MONGO_URI = f"mongodb+srv://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_URL}/{TRADENOTE_DATABASE}?authSource=admin"
    elif MONGO_USER and MONGO_PASSWORD:
        MONGO_URI = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_URL}:{MONGO_PORT}/{TRADENOTE_DATABASE}?authSource=admin"
    else:
        # Use simple connection without authentication
        MONGO_URI = f"mongodb://{MONGO_URL}:{MONGO_PORT}/{TRADENOTE_DATABASE}"

# Print configuration for debugging
print("\n--- TradeNote Configuration ---")
print(f"MongoDB URI: {MONGO_URI.replace('://', '://***@') if '://' in MONGO_URI else MONGO_URI}")
print(f"App ID: {APP_ID}")
print(f"Port: {PORT}")
print(f"Environment: {NODE_ENV}")
print(f"Database: {TRADENOTE_DATABASE}")
print("------------------------------\n") 