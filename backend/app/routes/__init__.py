"""Routes module for the FastAPI application."""

from fastapi import APIRouter

# Create a router to export
router = APIRouter(prefix="/api/v1")

# Import and include all route modules
from . import auth, api, trades, ibkr, catalysts, stock_analysis

# Export for convenience
__all__ = ["router"] 