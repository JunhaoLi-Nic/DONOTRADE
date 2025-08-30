# Dontrade Project Overview

This project is a full-stack web application named DONTRADE.

## Development Commands

### Recommended Startup (Full Stack)
- `python run_Dontrade.py` - **Primary command** - Starts both backend and frontend servers with monitoring and auto-browser opening

### Individual Commands
#### Frontend (Vue.js + Vite)
- `npm run start:frontend` or `vite` - Start only the frontend development server (http://localhost:5173)
- `npm run build` - Build the frontend for production
- `npm run preview` - Preview the production build

#### Backend (FastAPI + Python)
- `npm run start:backend` - Start the backend server from npm
- `cd backend && python run.py` - Start the backend server directly (http://localhost:3002)
- `cd backend && pip install -r requirements.txt` - Install Python dependencies

### Development Setup
- Frontend dev server: http://localhost:5173
- Backend API server: http://localhost:3002
- API endpoints accessible at `/api/*` (proxied through Vite)

## Architecture Overview

### Tech Stack
- **Frontend**: Vue 3 + Vite + Vue Router + Pinia (state management)
- **Backend**: FastAPI + Python + JWT authentication
- **Database**: MongoDB
- **UI Framework**: Ant Design Vue + Bootstrap 5
- **Charts**: Chart.js + ECharts
- **Build Tool**: Vite with hot module reloading

### Project Structure
```
├── src/                    # Vue.js frontend
│   ├── components/         # Reusable Vue components
│   ├── views/             # Page-level components
│   ├── services/          # API service layers
│   ├── utils/             # Utility functions and helpers
│   ├── stores/            # Pinia state management
│   ├── router/            # Vue Router configuration
│   └── layouts/           # Layout components (Dashboard, LoginRegister)
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── main.py        # FastAPI application entry point
│   │   ├── config.py      # Configuration and environment variables
│   │   ├── database.py    # MongoDB connection and utilities
│   │   ├── routes/        # API route handlers
│   │   └── services/      # Business logic services
│   ├── requirements.txt   # Python dependencies
│   └── run.py            # Backend server startup script
```

### Authentication System
- **JWT-based authentication** replacing previous Parse Server integration
- Frontend auth service: `src/services/auth.js`
- Backend auth routes: `backend/app/routes/auth.py`
- Token stored in localStorage with automatic axios header injection
- Route-level authentication guards in Vue Router

### API Architecture
- **RESTful API** with FastAPI backend
- Base URL: `/api/*` (proxied through Vite in development)
- **Complete API Endpoint Reference:**

#### Authentication Routes (`/api/auth/*`)
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user profile
- `POST /api/auth/logout` - User logout
- `POST /api/auth/change-password` - Change user password

#### General API Routes (`/api/*`)
- `POST /api/parseAppId` - Get Parse App ID configuration
- `POST /api/registerPage` - Check registration enabled/disabled status
- `POST /api/posthog` - Get analytics configuration
- `GET /api/dockerVersion` - Get application version
- `GET /api/user-profile` - Get current user profile
- `POST /api/updateProfile` - Update user profile (timezone, etc.)
- `POST /api/updateAPIs` - Update user API keys
- `GET /api/apis` - Get user API keys
- `GET /api/tags` - Get user tags with date filtering
- `GET /api/excursions` - Get excursions with date filtering
- `GET /api/satisfactions` - Get satisfaction records with filters
- `GET /api/availableTags` - Get available tag groups
- `POST /api/updateSchemas` - Legacy endpoint for Parse schema updating
- `POST /api/checkCloudPayment` - Legacy endpoint for subscription status
- `GET /api/notes` - Get notes with date filtering
- `POST /api/updateNote` - Update or create a note
- `POST /api/updateSatisfaction` - Update or create a satisfaction record
- `POST /api/updateTags` - Update or create tag mappings
- `POST /api/updateAvailableTags` - Update user's available tag groups
- `GET /api/patterns` - Get patterns with date filtering
- `GET /api/stocks/tickers` - Get all available stock tickers

#### Trade Data Routes (`/api/trades/*`)
- `GET /api/trades` - Get user trades with filters
- `POST /api/trades/single` - Create single trade
- `POST /api/trades/bulk` - Create multiple trades
- `DELETE /api/trades` - Delete trades by IDs
- `GET /api/trades/debug` - Diagnostic endpoint for trades

#### Order Management Routes (`/api/orders/*`)
- `GET /api/orders` - Get user orders with filters
- `POST /api/orders` - Save orders to database
- `DELETE /api/orders/{order_id}` - Delete specific order
- `GET /api/executed-orders` - Get executed orders
- `PUT /api/orders/{order_id}/checklist` - Update order checklist
- `POST /api/orders/update` - Update existing order
- `GET /api/orders/state/{state}` - Get orders by state (preorder, etc.)
- `POST /api/orders/fix-missing-fields` - Fix orders missing required fields
- `POST /api/orders/merge` - Merge multiple trades for same symbol
- `GET /api/orders-debug` - Debug endpoint

#### Interactive Brokers Routes (`/api/ibkr/*`)
- `GET /api/ibkr/positions` - Get positions from IBKR
- `GET /api/ibkr/open-orders` - Get open orders
- `GET /api/ibkr/account` - Get account information
- `GET /api/ibkr/prices` - Get current prices for symbols
- `GET /api/ibkr/cache/status` - Get price cache status
- `DELETE /api/ibkr/cache/clear` - Clear price cache
- `POST /api/ibkr/reconnect` - Force IBKR reconnection
- `GET /api/ibkr/diagnostics/connection` - Check IBKR connection
- `GET /api/ibkr/diagnostics/orders` - Diagnose order retrieval
- `GET /api/ibkr/diagnostics/check-orders` - Check order issues
- `GET /api/ibkr/diagnostics/ibkr-settings` - Check IBKR settings
- `GET /api/ibkr/toggle-capture` - Toggle data capture to dummy files
- Order reason endpoints:
  - `POST /api/ibkr/orders/{order_id}/reason` - Save order reason data
  - `GET /api/ibkr/orders/reasons` - Get all order reasons
  - `GET /api/ibkr/orders/{order_id}/reason` - Get specific order reason
  - `DELETE /api/ibkr/orders/{order_id}/reason` - Delete order reason

#### Data Management Routes (`/api/*`)
- **Tags:**
  - `GET /api/tags` - Get user tags with date filtering
  - `POST /api/updateTags` - Update/create tag mappings
  - `GET /api/availableTags` - Get available tag groups
  - `POST /api/updateAvailableTags` - Update user tag groups

- **Notes:**
  - `GET /api/notes` - Get user notes with date filtering
  - `POST /api/updateNote` - Create/update notes

- **Satisfactions:**
  - `GET /api/satisfactions` - Get satisfaction records
  - `POST /api/updateSatisfaction` - Create/update satisfaction records

- **Excursions:**
  - `GET /api/excursions` - Get excursions with date filtering

- **Patterns:**
  - `GET /api/patterns` - Get patterns with date filtering

#### Diary Management Routes (`/api/diaries/*`)
- `GET /api/diaries` - Get diary entries with filters
- `GET /api/diaries/{diary_id}` - Get specific diary entry
- `POST /api/diaries` - Create new diary entry
- `PUT /api/diaries/{diary_id}` - Update diary entry
- `DELETE /api/diaries/{diary_id}` - Delete diary entry

#### Screenshot Management Routes (`/api/screenshots/*`)
- `GET /api/screenshots` - Get screenshots with filters
- `POST /api/screenshots` - Create new screenshot
- `PUT /api/screenshots/{screenshot_id}` - Update screenshot
- `DELETE /api/screenshots/{screenshot_id}` - Delete screenshot

#### Playbook Management Routes (`/api/playbooks/*`)
- `GET /api/playbooks` - Get playbooks with filters
- `GET /api/playbooks/{playbook_id}` - Get specific playbook
- `POST /api/playbooks` - Create new playbook
- `PUT /api/playbooks/{playbook_id}` - Update playbook
- `DELETE /api/playbooks/{playbook_id}` - Delete playbook
- `POST /api/playbook/tags` - Save playbook tags
- `GET /api/playbook/{playbook_id}/tags` - Get playbook tags

#### Market Catalyst Routes (`/api/catalysts/*`)
- `GET /api/catalysts` - Get market catalysts with filters
- `POST /api/catalysts` - Add new catalyst
- `PUT /api/catalysts/{catalyst_id}` - Update catalyst
- `DELETE /api/catalysts/{catalyst_id}` - Delete catalyst

#### Stock Analysis Routes (`/api/stock-analysis/*`)
- `GET /api/stock-analysis/ticker-data/{ticker}` - Get ticker data
- `GET /api/stock-analysis/tickers` - Get available tickers
- `GET /api/stock-analysis/tickers/search` - Search tickers
- `GET /api/stock-analysis/dataframe/{ticker}` - Get ticker dataframe
- `GET /api/stock-analysis/consecutive/{ticker}` - Get consecutive price movement analysis
- `GET /api/stock-analysis/hurst/{ticker}` - Get Hurst exponent analysis
- `GET /api/stock-analysis/volatility/{ticker}` - Get volatility analysis
- `GET /api/stock-analysis/next-day-stats/{ticker}` - Get next day statistics
- `GET /api/stock-analysis/price-distribution/{ticker}` - Get price distribution analysis
- `GET /api/stock-analysis/sync-yfinance/{ticker}` - Sync ticker data with yfinance
- `POST /api/stock-analysis/backtest-strategy` - Backtest trading strategy
- `GET /api/stock-analysis/current-price/{ticker}` - Get current price for a ticker

#### Legacy/Compatibility Routes (`/api/*`)
- `POST /api/updateSchemas` - Legacy Parse schema endpoint (no-op)
- `POST /api/checkCloudPayment` - Legacy subscription endpoint

### Database Design
- **MongoDB** with direct driver (no ORM)
- Database name: configurable via `Dontrade_DATABASE` (default: "Dontrade")
- Collections for users, trades, diary entries, screenshots, playbooks, catalysts
- Connection handled in `backend/app/database.py`

### Frontend State Management
- **Pinia stores** in `src/stores/`
- Global state for authentication, user preferences, selected date ranges
- Reactive state management with Vue 3 composition API

### Development Workflow
1. **Environment Setup**: Ensure MongoDB is running locally
2. **Backend**: Start with `npm run start:backend` or direct Python execution
3. **Frontend**: Start with `npm run start:frontend` or use `npm run dev` for both
4. **Proxy Configuration**: Vite automatically proxies `/api/*` requests to backend

### Key Components
- **Dashboard Layout** (`src/layouts/Dashboard.vue`) - Main authenticated layout
- **Login/Register Layout** (`src/layouts/LoginRegister.vue`) - Authentication pages
- **Router Guards** - Automatic authentication checking and redirects
- **API Services** - Centralized HTTP client logic in `src/services/`
- **Utility Functions** - Common helpers in `src/utils/`

### Trading Platform Integration
- **Interactive Brokers (IBKR)** integration via API
- **CSV Import Support** for multiple brokers
- **Real-time Price Data** via yfinance and direct broker APIs
- **Order Synchronization** between platform and application

### Configuration
- **Environment Variables**: Managed in `backend/app/config.py`
- **Development Mode**: Set `NODE_ENV=dev` for development features
- **Database**: Configure via `MONGO_URI` environment variable
- **JWT Settings**: Configure secret and expiration via environment variables

### Port Configuration
- Frontend dev server: 5173 (Vite default)
- Backend API server: 3002 (configurable via `Dontrade_PORT`)
- MongoDB: 27017 (standard MongoDB port)

### RUN 
- `python run_tradenote.py` to start the app 