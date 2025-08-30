import { reactive } from 'vue';

// Store position types globally (symbol -> isShort boolean)
export const positionTypes = reactive({});

/**
 * Detects if a position is likely to be short based on available data
 * @param {Object} position - The position object
 * @returns {boolean} True if the position is likely short, false if likely long
 */
export const detectPositionType = (position) => {
  // If we already have a stored preference, use that
  if (positionTypes.hasOwnProperty(position.symbol)) {
    return positionTypes[position.symbol];
  }
  
  // Debug log to see all position data for troubleshooting
  console.log(`Detecting position type for ${position.symbol}:`, {
    shares: position.shares,
    strategy: position.strategy,
    side: position.side,
    entryPrice: position.entryPrice,
    currentPrice: position.currentPrice,
    profitLoss: position.profitLoss,
    value: position.value
  });
  
  // Detection priority 1: Negative shares is a strong indicator of a short position
  if (position.shares < 0) {
    console.log(`${position.symbol}: Detected as SHORT based on negative shares`);
    return true;
  }
  
  // Detection priority 2: Check if explicitly marked as short in strategy field
  if (position.strategy && position.strategy.toLowerCase() === 'short') {
    console.log(`${position.symbol}: Detected as SHORT based on strategy field`);
    return true;
  }
  
  // Detection priority 3: Check side/action (but only if shares are not explicitly positive)
  if (position.side) {
    const isShortSide = position.side === 'SS' || position.side === 'BC'; 
    if (isShortSide) {
      console.log(`${position.symbol}: Detected as SHORT based on side field`);
      return true;
    }
  }
  
  // Don't consider the following criteria if shares are explicitly positive
  // (unless overridden by one of the stronger indicators above)
  if (position.shares > 0) {
    console.log(`${position.symbol}: Detected as LONG based on positive shares`);
    return false;
  }
  
  // Only consider these secondary indicators if shares count is unavailable or zero
  
  // Detection priority 4: Check for P/L direction vs. price movement
  if (position.entryPrice && position.currentPrice && position.profitLoss !== undefined) {
    const priceMovement = position.currentPrice - position.entryPrice;
    const isProfitable = position.profitLoss > 0;
    
    // If price went up but P/L is negative, or price went down but P/L is positive, likely short
    if ((priceMovement > 0 && !isProfitable) || (priceMovement < 0 && isProfitable)) {
      console.log(`${position.symbol}: Detected as SHORT based on price movement vs P/L`);
      return true;
    }
  }
  
  // Detection priority 5: Check for value vs. profit mismatch
  if (position.profitLoss !== undefined && position.value !== undefined) {
    // If profit is positive when value is negative or vice versa, likely short
    const valueProfitMismatch = (position.value < 0 && position.profitLoss > 0) || 
                              (position.value > 0 && position.profitLoss < 0);
    if (valueProfitMismatch) {
      console.log(`${position.symbol}: Detected as SHORT based on value/profit mismatch`);
      return true;
    }
  }
  
  // Default to long position if we can't determine
  console.log(`${position.symbol}: Defaulting to LONG position`);
  return false;
};

/**
 * Toggles a position between long and short
 * @param {string} symbol - The symbol to toggle
 */
export const togglePositionType = (symbol) => {
  positionTypes[symbol] = !positionTypes[symbol];
}; 