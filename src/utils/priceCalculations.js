/**
 * Utility functions for price-related calculations
 * Handles target prices, stop prices, and price analysis
 */

/**
 * Find target price from the symbolData's sub-orders
 * @param {Object} symbolData - Object containing mainOrder and subOrders
 * @param {Function} getPositionType - Function to determine if position is short
 * @returns {number|null} Target price or null if not found
 */
export function getTargetPrice(symbolData, getPositionType) {
  if (!symbolData || !symbolData.subOrders || symbolData.subOrders.length === 0) return null
  
  // Filter out PendingCancel orders
  const activeSubOrders = symbolData.subOrders.filter(order => order.status !== 'PendingCancel');
  if (activeSubOrders.length === 0) return null;
  
  const isShort = getPositionType(symbolData.symbol || symbolData.mainOrder?.symbol)
  const entryPrice = symbolData.mainOrder?.limitPrice
  
  if (!entryPrice) return null
  
  if (isShort) {
    // For short positions, look for BUY LMT orders (target price is lower than entry)
    const targetOrders = activeSubOrders.filter(order => {
      return order.action.toUpperCase() === 'BUY' && order.orderType.toUpperCase() === 'LMT' &&
             order.limitPrice < entryPrice // Only include orders with price below entry for shorts
    })
    
    if (targetOrders.length > 0) {
      // Calculate weighted average if multiple profit targets
      if (targetOrders.length > 1) {
        let totalQuantity = 0
        let weightedSum = 0
        
        targetOrders.forEach(order => {
          const qty = order.totalQuantity || 0
          totalQuantity += qty
          weightedSum += (order.limitPrice * qty)
        })
        
        return totalQuantity > 0 ? weightedSum / totalQuantity : null
      } else {
        // For short positions, target is the lowest price (best profit)
        return Math.min(...targetOrders.map(o => o.limitPrice).filter(Boolean))
      }
    }
  } else {
    // For long positions, look for SELL LMT orders
    const targetOrders = activeSubOrders.filter(order => {
      return order.action.toUpperCase() === 'SELL' && order.orderType.toUpperCase() === 'LMT' &&
             order.limitPrice > entryPrice // Only include orders with price above entry for longs
    })
    
    // If multiple SELL LMT orders exist, calculate weighted average
    if (targetOrders.length > 0) {
      // Calculate weighted average if multiple profit targets
      if (targetOrders.length > 1) {
        let totalQuantity = 0
        let weightedSum = 0
        
        targetOrders.forEach(order => {
          const qty = order.totalQuantity || 0
          totalQuantity += qty
          weightedSum += (order.limitPrice * qty)
        })
        
        return totalQuantity > 0 ? weightedSum / totalQuantity : null
      } else {
        // For long positions, target is the highest price (best profit)
        return Math.max(...targetOrders.map(o => o.limitPrice).filter(Boolean))
      }
    }
  }
  
  return null
}

/**
 * Find stop price from the symbolData's sub-orders
 * @param {Object} symbolData - Object containing mainOrder and subOrders
 * @param {Function} getPositionType - Function to determine if position is short
 * @returns {number|null} Stop price or null if not found
 */
export function getStopPrice(symbolData, getPositionType) {
  if (!symbolData || !symbolData.subOrders || symbolData.subOrders.length === 0) return null
  
  // Filter out PendingCancel orders
  const activeSubOrders = symbolData.subOrders.filter(order => order.status !== 'PendingCancel');
  if (activeSubOrders.length === 0) return null;
  
  const isShort = getPositionType(symbolData.symbol || symbolData.mainOrder?.symbol)
  const entryPrice = symbolData.mainOrder?.limitPrice
  
  if (!entryPrice) return null
  
  if (isShort) {
    // For short positions, first look for BUY STP orders
    let stopOrders = activeSubOrders.filter(order => {
      return order.action.toUpperCase() === 'BUY' && order.orderType.toUpperCase() === 'STP'
    })
    
    // If no STP orders, check for BUY LMT orders above entry price (potential stops)
    if (stopOrders.length === 0) {
      stopOrders = activeSubOrders.filter(order => {
        return order.action.toUpperCase() === 'BUY' && 
               order.orderType.toUpperCase() === 'LMT' && 
               order.limitPrice > entryPrice
      })
    }
    
    if (stopOrders.length > 0) {
      // Calculate weighted average if multiple stop orders
      if (stopOrders.length > 1) {
        let totalQuantity = 0
        let weightedSum = 0
        
        stopOrders.forEach(order => {
          const qty = order.totalQuantity || 0
          totalQuantity += qty
          weightedSum += ((order.stopPrice || order.limitPrice) * qty)
        })
        
        return totalQuantity > 0 ? weightedSum / totalQuantity : null
      } else {
        // For short positions, stop is the highest price (worst loss)
        return Math.max(...stopOrders.map(o => o.stopPrice || o.limitPrice).filter(Boolean))
      }
    }
  } else {
    // For long positions, first look for SELL STP orders
    let stopOrders = activeSubOrders.filter(order => {
      return order.action.toUpperCase() === 'SELL' && order.orderType.toUpperCase() === 'STP'
    })
    
    // If no STP orders, check for SELL LMT orders below entry price (potential stops)
    if (stopOrders.length === 0) {
      stopOrders = activeSubOrders.filter(order => {
        return order.action.toUpperCase() === 'SELL' && 
               order.orderType.toUpperCase() === 'LMT' && 
               order.limitPrice < entryPrice
      })
    }
    
    if (stopOrders.length > 0) {
      // Calculate weighted average if multiple stop orders
      if (stopOrders.length > 1) {
        let totalQuantity = 0
        let weightedSum = 0
        
        stopOrders.forEach(order => {
          const qty = order.totalQuantity || 0
          totalQuantity += qty
          weightedSum += ((order.stopPrice || order.limitPrice) * qty)
        })
        
        return totalQuantity > 0 ? weightedSum / totalQuantity : null
      } else {
        // For long positions, stop is the lowest price (worst loss)
        return Math.min(...stopOrders.map(o => o.stopPrice || o.limitPrice).filter(Boolean))
      }
    }
  }
  
  return null
}

/**
 * Calculate price difference as percentage
 * @param {number} price1 - First price
 * @param {number} price2 - Second price
 * @param {number} basePrice - Base price for percentage calculation
 * @returns {number|null} Percentage difference or null if invalid
 */
export function calculatePricePercentage(price1, price2, basePrice) {
  if (!price1 || !price2 || !basePrice || basePrice === 0) return null
  
  return ((price1 - price2) / basePrice) * 100
}

/**
 * Get current market price for a symbol
 * @param {string} symbol - Stock symbol
 * @param {Object} currentPrices - Object containing current price data
 * @returns {number|null} Current price or null if not available
 */
export function getCurrentPrice(symbol, currentPrices) {
  if (!symbol || !currentPrices || !currentPrices[symbol]) return null
  
  return currentPrices[symbol].price || null
}

/**
 * Calculate price movement direction and magnitude
 * @param {number} currentPrice - Current stock price
 * @param {number} entryPrice - Entry price
 * @returns {Object} Object containing direction and percentage change
 */
export function calculatePriceMovement(currentPrice, entryPrice) {
  if (!currentPrice || !entryPrice) {
    return { direction: 'neutral', percentage: 0 }
  }
  
  const difference = currentPrice - entryPrice
  const percentage = (difference / entryPrice) * 100
  
  return {
    direction: difference > 0 ? 'up' : difference < 0 ? 'down' : 'neutral',
    percentage: Math.abs(percentage),
    rawPercentage: percentage
  }
}