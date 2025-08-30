# TradeNote Python Backend

This is the Python FastAPI backend for TradeNote, migrated from the original Node.js implementation.

## Setup and Running

### Prerequisites
- Python 3.8+
- MongoDB running locally (or update configuration to point to your MongoDB instance)

### Installation
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (optional):
   - Create a `.env` file in the `backend` directory
   - Set any of the following variables:
     - `MONGO_URI`: MongoDB connection string (default: `mongodb://localhost:27017/tradenote`)
     - `APP_ID`: Parse Server Application ID (default: `123456`)
     - `TRADENOTE_PORT`: Port for the server (default: `3000`)
     - `NODE_ENV`: Environment (`dev` or `production`, default: `production`)

### Running the Server

#### Standard Start
```bash
python run.py
```

#### Comprehensive Start (with MongoDB checking)
```bash
python run_all.py
```

#### Testing
```bash
# Test all API endpoints
python test_api_endpoints.py

# Test authentication endpoints
python test_auth.py

# Detailed debugging of all endpoints
python debug_test.py
```

## API Endpoints

### API Routes
- `POST /api/parseAppId` - Get Parse App ID
- `POST /api/registerPage` - Check if registration is enabled
- `POST /api/posthog` - Get PostHog configuration
- `POST /api/updateSchemas` - Legacy endpoint for schema updates
- `POST /api/checkCloudPayment` - Legacy endpoint for subscription status

### Authentication Routes
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login a user
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout a user
- `POST /api/auth/change-password` - Change user password

### Parse Server Compatible Routes
- `POST /parse/login` - Parse login
- `POST /parse/users` - Create user
- `GET /parse/users/me` - Get current user
- `POST /parse/logout` - Logout
- `GET /parse/classes/{class_name}` - Get objects
- `GET /parse/classes/{class_name}/{object_id}` - Get object
- `POST /parse/classes/{class_name}` - Create object
- `PUT /parse/classes/{class_name}/{object_id}` - Update object
- `DELETE /parse/classes/{class_name}/{object_id}` - Delete object

## Fixed Issues

1. **Router Prefix Issue**: Fixed issue with double prefixing of routes in `main.py` by ensuring prefixes are only set once.

2. **Response Format**: Updated `/api/registerPage` endpoint to return a JSON object instead of a raw boolean value.

3. **MongoDB Connection**: Improved MongoDB connection handling and error reporting.

4. **Debug Tools**: Added debugging endpoints and tools to help diagnose issues:
   - `/debug/routes` - Lists all registered routes
   - `debug_test.py` - Detailed endpoint testing

5. **Server Startup**: Created comprehensive server startup script (`run_all.py`) that checks MongoDB availability before starting the server.

6. **Parse Server Compatibility**: Ensured all Parse Server endpoints work correctly for compatibility with the existing frontend.