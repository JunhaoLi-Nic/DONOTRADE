import logging
import os
from pathlib import Path
from fastapi import FastAPI, Request, Response, HTTPException, Depends, APIRouter
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="TradeNote API", version="2.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response

# Import routers directly
from .routes.api import api_router
from .routes.auth import auth_router
from .routes.ibkr import router as ibkr_router
try:
    from .routes.catalysts import router as catalysts_router
except ImportError as e:
    logger.warning(f"Catalysts router not found: {e}")
    catalysts_router = APIRouter()
try:
    from .routes.orders import router as orders_router
except ImportError as e:
    logger.warning(f"Orders router not found: {e}")
    orders_router = APIRouter()
try:
    from .parse_server import parse_router
except ImportError as e:
    logger.warning(f"Parse router not found: {e}")
    parse_router = APIRouter()

# Import the trades router
from .routes.trades import trades_router

# Import the stock analysis router
try:
    from .routes.stock_analysis import router as stock_analysis_router
except ImportError as e:
    logger.warning(f"Stock analysis router not found: {e}")
    stock_analysis_router = APIRouter()

from .config import NODE_ENV, PORT
from .database import db

# Include routers with proper prefixes
app.include_router(api_router, prefix="/api")
app.include_router(auth_router, prefix="/api/auth")
app.include_router(ibkr_router, prefix="/api/ibkr")
app.include_router(catalysts_router, prefix="/api")  # Add catalysts router under /api
app.include_router(orders_router, prefix="/api")  # Add orders router under /api
app.include_router(parse_router)  # Parse router already has prefix in parse_server.py
app.include_router(trades_router, prefix="/api")  # Include trades router under /api
app.include_router(stock_analysis_router, prefix="/api")  # Include stock analysis router under /api

# Add backend/api routes that redirect to /api routes for frontend compatibility
app.include_router(api_router, prefix="/backend/api")

# Debug endpoint to list all routes
@app.get("/debug/routes")
async def debug_routes():
    """List all registered routes"""
    routes = []
    for route in app.routes:
        routes.append({
            "path": route.path,
            "name": route.name,
            "methods": route.methods if hasattr(route, "methods") else None
        })
    return {"routes": routes}

# Setup static files and frontend routes
@app.get("/", response_class=HTMLResponse)
async def read_root():
    return "<html><head><title>TradeNote API</title></head><body><h1>TradeNote API Server</h1><p>API is running successfully. Frontend is served separately in development mode.</p></body></html>"

# Display test connection page
@app.get("/test-connection", response_class=HTMLResponse)
async def test_connection():
    html_path = Path("test_connection.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<html><body><h1>Test page not found</h1></body></html>")

# Handle frontend files in production
if NODE_ENV == 'production':
    static_dir = Path(__file__).parent.parent / ".." / "dist"
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
        
        @app.get("/{path:path}")
        async def serve_frontend(path: str):
            if path == "" or not os.path.exists(static_dir / path):
                return FileResponse(str(static_dir / "index.html"))
            return FileResponse(str(static_dir / path))
    else:
        logger.warning(f"Running in production mode but dist directory not found at {static_dir}")
        logger.warning("Frontend files will not be served.")

# Run the application
if __name__ == "__main__":
    logger.info("\nSTARTING PYTHON SERVER")
    logger.info(f" -> TradeNote server started on http://localhost:{PORT}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=NODE_ENV == 'dev') 