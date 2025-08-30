"""
Option Rolling Analysis Module

Provides functions to calculate option rolling strategies: roll out, roll up, and roll down.
"""
import numpy as np
from typing import Dict, Any

# Example logic, replace with real option pricing/rolling logic as needed

def roll_out(symbol: str, expiry: str, strike: float) -> Dict[str, Any]:
    """Calculate rolling out (extend expiry) for an option."""
    # Placeholder: In real use, fetch option chain and calculate new expiry
    return {
        'action': 'roll_out',
        'symbol': symbol,
        'old_expiry': expiry,
        'new_expiry': '2024-12-31',
        'strike': strike,
        'note': 'Rolled out to next available expiry.'
    }

def roll_up(symbol: str, expiry: str, strike: float) -> Dict[str, Any]:
    """Calculate rolling up (increase strike) for an option."""
    return {
        'action': 'roll_up',
        'symbol': symbol,
        'expiry': expiry,
        'old_strike': strike,
        'new_strike': strike + 5,  # Example increment
        'note': 'Rolled up to higher strike.'
    }

def roll_down(symbol: str, expiry: str, strike: float) -> Dict[str, Any]:
    """Calculate rolling down (decrease strike) for an option."""
    return {
        'action': 'roll_down',
        'symbol': symbol,
        'expiry': expiry,
        'old_strike': strike,
        'new_strike': strike - 5,  # Example decrement
        'note': 'Rolled down to lower strike.'
    }

def calculate_option_rolling(symbol: str, expiry: str, strike: float, direction: str) -> Dict[str, Any]:
    """
    Calculate profit curves and BEP for option rolling scenarios (out, up, down).
    Returns arrays for plotting and key values for chart annotations.
    """
    # Stock price range for plotting
    S = np.linspace(strike - 45, strike + 45, 200)

    # --- Before Roll ---
    strike_old = strike
    credit_old = 20.0  # Example, should be parameterized or fetched
    BEP_old = strike_old - credit_old
    profit_old = np.where(S >= strike_old, credit_old, S - BEP_old)

    # --- After Roll (simulate all three directions) ---
    results = {}
    for dir_label, (strike_new, btc_cost, new_credit) in {
        'out': (strike_old, 5.0, 18.0),
        'up': (strike_old + 30, 17.0, 23.0),
        'down': (strike_old - 30, 2.0, 13.0)
    }.items():
        credit_new_total = credit_old - btc_cost + new_credit
        BEP_new = strike_old - credit_new_total
        profit_new = np.where(
            S >= strike_new,
            (strike_new - strike_old) + credit_new_total,
            S - BEP_new
        )
        results[dir_label] = {
            'strike_new': strike_new,
            'credit_new_total': credit_new_total,
            'BEP_new': BEP_new,
            'profit_new': profit_new.tolist()
        }

    return {
        'S': S.tolist(),
        'profit_old': profit_old.tolist(),
        'BEP_old': BEP_old,
        'strike_old': strike_old,
        'credit_old': credit_old,
        'scenarios': results
    } 