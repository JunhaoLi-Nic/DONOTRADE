from fastapi import APIRouter, HTTPException
import logging
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# Initialize the router
router = APIRouter()

# Define the path for storing catalyst data
CATALYSTS_FILE = Path("data/catalysts.json")

# Ensure the data directory exists
os.makedirs(CATALYSTS_FILE.parent, exist_ok=True)

# Initialize the file if it doesn't exist
if not CATALYSTS_FILE.exists():
    with open(CATALYSTS_FILE, "w") as f:
        json.dump([], f)

def load_catalysts() -> List[Dict[str, Any]]:
    """Load catalysts from the JSON file."""
    try:
        with open(CATALYSTS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading catalysts: {e}")
        return []

def save_catalysts(catalysts: List[Dict[str, Any]]) -> bool:
    """Save catalysts to the JSON file."""
    try:
        with open(CATALYSTS_FILE, "w") as f:
            json.dump(catalysts, f, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving catalysts: {e}")
        return False

@router.get("/catalysts")
async def get_catalysts(symbol: Optional[str] = None):
    """
    Get all catalysts or filter by symbol.
    
    Args:
        symbol: Optional symbol to filter catalysts
    
    Returns:
        List of catalysts
    """
    catalysts = load_catalysts()
    
    if symbol:
        # Filter catalysts by symbol
        return [
            catalyst for catalyst in catalysts
            if (symbol.upper() in [s.upper() for s in catalyst.get("relatedSymbols", [])] or
                symbol.upper() in catalyst.get("keyFact", "").upper() or 
                symbol.upper() in catalyst.get("currentMarketTheme", "").upper())
        ]
    
    return catalysts

@router.post("/catalysts")
async def add_catalyst(catalyst: Dict[str, Any]):
    """
    Add a new catalyst.
    
    Args:
        catalyst: Catalyst data to add
    
    Returns:
        Success message
    """
    # Load existing catalysts
    catalysts = load_catalysts()
    
    # Add timestamp if not provided
    if "date" not in catalyst:
        catalyst["date"] = datetime.now().strftime("%Y-%m-%d")
    
    # Add the new catalyst
    catalysts.append(catalyst)
    
    # Save back to file
    if save_catalysts(catalysts):
        return {"message": "Catalyst added successfully", "catalyst": catalyst}
    else:
        raise HTTPException(status_code=500, detail="Failed to save catalyst")

@router.put("/catalysts/{catalyst_id}")
async def update_catalyst(catalyst_id: int, catalyst: Dict[str, Any]):
    """
    Update an existing catalyst.
    
    Args:
        catalyst_id: Index of the catalyst to update
        catalyst: Updated catalyst data
    
    Returns:
        Success message
    """
    # Load existing catalysts
    catalysts = load_catalysts()
    
    # Check if the catalyst_id is valid
    if catalyst_id < 0 or catalyst_id >= len(catalysts):
        raise HTTPException(status_code=404, detail="Catalyst not found")
    
    # Update the catalyst
    catalysts[catalyst_id] = catalyst
    
    # Save back to file
    if save_catalysts(catalysts):
        return {"message": "Catalyst updated successfully", "catalyst": catalyst}
    else:
        raise HTTPException(status_code=500, detail="Failed to update catalyst")

@router.delete("/catalysts/{catalyst_id}")
async def delete_catalyst(catalyst_id: int):
    """
    Delete a catalyst.
    
    Args:
        catalyst_id: Index of the catalyst to delete
    
    Returns:
        Success message
    """
    # Load existing catalysts
    catalysts = load_catalysts()
    
    # Check if the catalyst_id is valid
    if catalyst_id < 0 or catalyst_id >= len(catalysts):
        raise HTTPException(status_code=404, detail="Catalyst not found")
    
    # Remove the catalyst
    deleted_catalyst = catalysts.pop(catalyst_id)
    
    # Save back to file
    if save_catalysts(catalysts):
        return {"message": "Catalyst deleted successfully", "catalyst": deleted_catalyst}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete catalyst") 