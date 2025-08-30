import os
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime
from .data_utils import read_and_prepare_data


def analyze_consecutive_patterns(df, min_days=2, max_days=10):
    """Analyze consecutive price movements and their follow-on behavior."""
    results = {}
    
    # Validate and clean input data
    if len(df) < min_days + 5:  # Need at least min_days + some buffer for analysis
        print(f"Warning: Dataframe length ({len(df)}) may be too short for meaningful analysis")
    
    # Ensure we have is_target_day column and it's valid
    if "is_target_day" not in df.columns:
        print("Error: is_target_day column not found in dataframe")
        return {}
    
    # Ensure there are no NaN values in is_target_day
    nan_count = df["is_target_day"].isna().sum()
    if nan_count > 0:
        print(f"Warning: Found {nan_count} NaN values in is_target_day column")
        # Fill NaNs before continuing
        df["is_target_day"] = df["is_target_day"].fillna(False)
    
    # Fill NAs in is_target_day to ensure continuity
    movement = df["is_target_day"].fillna(False)
    
    # Count consecutive days with the same movement
    df["streak"] = 0
    current_streak = 0
    
    # Safely iterate and update streak column
    try:
        for i in range(len(df)):
            if movement.iloc[i]:  # If this is a target day (up or down)
                current_streak += 1
            else:
                current_streak = 0
            df.iloc[i, df.columns.get_loc("streak")] = current_streak
    except Exception as e:
        print(f"Error while calculating streaks: {e}")
        return {}
    
    # Analyze streaks of different lengths
    for n_days in range(min_days, max_days + 1):
        # Find days that end a streak of exactly n_days
        streak_ends = df[df["streak"] == n_days].index
        
        if len(streak_ends) == 0:
            print(f"No {n_days}-day streaks found")
            continue
            
        print(f"Found {len(streak_ends)} {n_days}-day streaks")
        
        # Store information about what happens after these streaks
        sequences = []
        
        # Convert index to integer positions for safe manipulation
        try:
            idx_positions = [df.index.get_loc(idx) for idx in streak_ends]
        except Exception as e:
            print(f"Error getting index positions: {e}")
            # Try an alternative approach for non-standard indices
            idx_positions = []
            for i, idx in enumerate(df.index):
                if idx in streak_ends:
                    idx_positions.append(i)
            
            if len(idx_positions) == 0:
                print(f"Could not find positions for streak ends, skipping {n_days}-day analysis")
                continue
        
        for pos in idx_positions:
            try:
                if pos + 1 < len(df):  # Make sure there's at least one more day
                    next_pos = pos + 1
                    
                    # Make sure all required columns exist and are valid
                    if "date" not in df.columns or "daily_return" not in df.columns:
                        print(f"Missing required columns in dataframe")
                        continue
                    
                    # Record information about this sequence
                    sequence = {
                        "end_date": df.iloc[pos]["date"],  # Date of the nth consecutive day
                        "next_day_return": float(df.iloc[next_pos]["daily_return"]),
                        "next_day_same_direction": bool(df.iloc[next_pos]["is_target_day"]),
                        "next_5_days": []
                    }
                    
                    # Get the next 5 days data (if available)
                    for i in range(1, 6):
                        if pos + i < len(df):
                            future_pos = pos + i
                            sequence["next_5_days"].append({
                                "day": i,
                                "date": df.iloc[future_pos]["date"],
                                "return": float(df.iloc[future_pos]["daily_return"]),
                                "same_direction": bool(df.iloc[future_pos]["is_target_day"])
                            })
                    
                    sequences.append(sequence)
            except Exception as seq_error:
                print(f"Error processing sequence at position {pos}: {seq_error}")
                continue
        
        if sequences:  # Only add to results if we found valid sequences
            results[n_days] = sequences
    
    return results


def calculate_continuation_probabilities(consecutive_moves):
    """Calculate probability of continued moves in the same direction."""
    probabilities = {}
    
    # Handle empty input
    if not consecutive_moves:
        print("Warning: No consecutive moves provided for probability calculation")
        return probabilities
    
    for n_days, sequences in consecutive_moves.items():
        if not sequences:
            print(f"No sequences for {n_days}-day streaks, skipping")
            continue
            
        try:
            # Calculate next day probability
            next_day_same_count = 0
            valid_sequences = 0
            
            for seq in sequences:
                # Make sure the next_day_same_direction field exists and is a valid boolean
                if "next_day_same_direction" in seq:
                    try:
                        if bool(seq["next_day_same_direction"]):
                            next_day_same_count += 1
                        valid_sequences += 1
                    except (ValueError, TypeError) as e:
                        print(f"Invalid next_day_same_direction value: {seq.get('next_day_same_direction')}, error: {e}")
            
            next_day_prob = next_day_same_count / valid_sequences if valid_sequences > 0 else 0
            
            # Calculate probabilities for the next 5 days
            next_days_probs = []
            for day in range(1, 6):
                try:
                    # Get sequences that have data for this day
                    day_sequences = [seq for seq in sequences if "next_5_days" in seq and 
                                   len(seq["next_5_days"]) >= day]
                    
                    if not day_sequences:
                        print(f"No valid data for day {day} in {n_days}-day sequences")
                        # Add placeholder with 0 probability
                        next_days_probs.append({"day": day, "probability": 0})
                        continue
                    
                    # Count same direction moves
                    try:
                        same_count = sum(1 for seq in day_sequences if 
                                       seq["next_5_days"][day-1].get("same_direction", False))
                        prob = same_count / len(day_sequences)
                        next_days_probs.append({"day": day, "probability": prob})
                    except Exception as count_error:
                        print(f"Error counting for day {day}: {count_error}")
                        # Add placeholder with 0 probability
                        next_days_probs.append({"day": day, "probability": 0})
                        
                except Exception as day_error:
                    print(f"Error processing day {day}: {day_error}")
                    # Add placeholder with 0 probability
                    next_days_probs.append({"day": day, "probability": 0})
            
            # Calculate average next day return, safely handling invalid values
            next_day_returns = []
            for seq in sequences:
                try:
                    if "next_day_return" in seq and isinstance(seq["next_day_return"], (int, float)):
                        # Filter out NaN and infinite values
                        return_value = float(seq["next_day_return"])
                        if not np.isnan(return_value) and not np.isinf(return_value):
                            next_day_returns.append(return_value)
                except (ValueError, TypeError) as e:
                    print(f"Invalid next_day_return value: {seq.get('next_day_return')}, error: {e}")
            
            avg_next_day_return = np.mean(next_day_returns) if next_day_returns else 0
            
            # Store probabilities
            probabilities[n_days] = {
                "count": len(sequences),
                "next_day_probability": next_day_prob,
                "next_days_probabilities": next_days_probs,
                "avg_next_day_return": avg_next_day_return
            }
            
        except Exception as e:
            print(f"Error calculating probabilities for {n_days}-day sequences: {e}")
            # Add minimal information for this streak length
            probabilities[n_days] = {
                "count": len(sequences),
                "next_day_probability": 0,
                "next_days_probabilities": [{"day": i, "probability": 0} for i in range(1, 6)],
                "avg_next_day_return": 0
            }
    
    return probabilities


def analyze_consecutive_moves(ticker, direction="down", min_days=2, max_days=10, 
                             date_from=None, date_to=None, visualize=False):
    """
    Main function to analyze consecutive price moves and their continuation probability.
    
    Parameters:
        ticker (str): Stock ticker symbol to analyze
        direction (str): "up" for price increases, "down" for price drops
        min_days (int): Minimum number of consecutive days to analyze
        max_days (int): Maximum number of consecutive days to analyze
        date_from (str): Optional start date for analysis (YYYY-MM-DD)
        date_to (str): Optional end date for analysis (YYYY-MM-DD)
        visualize (bool): Whether to display visualization (kept for compatibility)
        
    Returns:
        tuple: (DataFrame, consecutive_moves_dict, probabilities_dict)
    """
    try:
        # Validate direction
        if direction.lower() not in ["up", "down"]:
            raise ValueError("Direction must be either 'up' or 'down'")
            
        direction = direction.lower()
        direction_label = "Up" if direction == "up" else "Down"
        move_label = "increases" if direction == "up" else "drops"
        
        print(f"Analyzing {ticker} consecutive price {move_label}")
        
        # Read and prepare data
        try:
            df = read_and_prepare_data(ticker, date_from, date_to)
            
            # Filter out future dates
            today = pd.Timestamp.today()
            if any(df.index > today):
                print(f"Warning: Found future dates in data, filtering them out")
                df = df[df.index <= today]
                if len(df) == 0:
                    raise ValueError(f"No historical data available for {ticker} after filtering future dates")
            
            # Add columns for analysis
            if direction == "up":
                df["is_target_day"] = df["close"] > df["close"].shift(1)
            else:
                df["is_target_day"] = df["close"] < df["close"].shift(1)
                
            df["daily_return"] = df["close"].pct_change()
            df = df.dropna()
            
            # Add date column for output
            df["date"] = df.index.strftime("%Y-%m-%d")
            
        except Exception as data_error:
            print(f"Error reading data: {data_error}")
            raise ValueError(f"Error reading price data for {ticker}: {data_error}")
        
        # Find all consecutive price move sequences
        consecutive_moves = analyze_consecutive_patterns(df, min_days, max_days)
        
        # Calculate continuation probabilities
        probabilities = calculate_continuation_probabilities(consecutive_moves)
        
        # Print results
        print(f"\n=== Consecutive {direction_label} Day Analysis for {ticker} ===")
        for n_days, stats in sorted(probabilities.items()):
            print(f"\nAfter {n_days} consecutive {direction_label.lower()} days ({stats['count']} occurrences):")
            print(f"  Next day {direction_label.lower()} probability: {stats['next_day_probability']:.2%}")
            print(f"  Average next day return: {stats['avg_next_day_return']:.2%}")
            
            print(f"  Probability of {direction_label.lower()} day for next 5 days:")
            for day_prob in stats['next_days_probabilities']:
                print(f"    Day +{day_prob['day']}: {day_prob['probability']:.2%}")
        
        return df, consecutive_moves, probabilities
    
    except Exception as e:
        print(f"Error analyzing consecutive {direction} days: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


if __name__ == "__main__":
    # ─── CONFIG ──────────────────────────────────────────────────────────────────
    TICKER    = "AAPL"                                     # Ticker to analyze
    DIRECTION = "down"                                     # "up" for price increases, "down" for price drops
    MIN_DAYS  = 2                                          # Min consecutive days to analyze
    MAX_DAYS  = 10                                         # Max consecutive days to analyze
    DATE_FROM = None                                       # Optional start date (e.g., "2020-01-01")
    DATE_TO   = None                                       # Optional end date (e.g., "2023-12-31")
    
    df, consecutive_moves, probabilities = analyze_consecutive_moves(
        TICKER, DIRECTION, MIN_DAYS, MAX_DAYS, DATE_FROM, DATE_TO, visualize=False
    ) 