/**
 * Utility functions for order validation, formatting, and general order operations
 */

/**
 * Validate if an order has all required fields
 * @param {Object} order - Order object to validate
 * @returns {Object} Validation result with isValid boolean and missing fields array
 */
export function validateOrder(order) {
  const requiredFields = ['symbol', 'action', 'orderType', 'totalQuantity']
  const missingFields = []
  
  requiredFields.forEach(field => {
    if (!order[field]) {
      missingFields.push(field)
    }
  })
  
  // Additional validation rules
  if (order.totalQuantity && order.totalQuantity <= 0) {
    missingFields.push('totalQuantity (must be positive)')
  }
  
  if (order.limitPrice && order.limitPrice <= 0) {
    missingFields.push('limitPrice (must be positive)')
  }
  
  return {
    isValid: missingFields.length === 0,
    missingFields
  }
}

/**
 * Format currency value for display
 * @param {number} value - Numeric value to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted currency string
 */
export function formatCurrency(value, decimals = 2) {
  if (value === null || value === undefined || isNaN(value)) return '-'
  
  return '$' + Number(value).toFixed(decimals)
}

/**
 * Format percentage value for display
 * @param {number} value - Numeric value to format as percentage
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted percentage string
 */
export function formatPercentage(value, decimals = 2) {
  if (value === null || value === undefined || isNaN(value)) return '-'
  
  return Number(value).toFixed(decimals) + '%'
}

/**
 * Format number with thousands separators
 * @param {number} value - Numeric value to format
 * @param {number} decimals - Number of decimal places (default: 0)
 * @returns {string} Formatted number string
 */
export function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined || isNaN(value)) return '-'
  
  return Number(value).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

/**
 * Get CSS class for order status
 * @param {string} status - Order status
 * @returns {string} CSS class name
 */
export function getStatusClass(status) {
  if (!status) return 'status-default'
  
  switch (status.toLowerCase()) {
    case 'filled':
      return 'status-success'
    case 'submitted':
    case 'presubmitted':
      return 'status-processing'
    case 'cancelled':
      return 'status-error'
    case 'pendingsubmit':
      return 'status-warning'
    default:
      return 'status-default'
  }
}

/**
 * Get CSS class for positive/negative values
 * @param {number} value - Numeric value
 * @returns {string} CSS class name
 */
export function getValueClass(value) {
  if (value === null || value === undefined || isNaN(value)) return ''
  
  if (value > 0) return 'positive-value'
  if (value < 0) return 'negative-value'
  return ''
}

/**
 * Check if order is a main order (entry order for a position)
 * @param {Object} order - Order object
 * @param {Array} allOrders - Array of all orders for the same symbol
 * @returns {boolean} True if this is a main order
 */
export function isMainOrder(order, allOrders = []) {
  if (!order) return false
  
  // If order has explicit main order flag
  if (order.hasOwnProperty('isMainOrder')) {
    return order.isMainOrder
  }
  
  // Logic to determine main order based on order type and action
  const ordersBySymbol = allOrders.filter(o => o.symbol === order.symbol)
  
  // For now, consider LMT orders as main orders
  return order.orderType && order.orderType.toUpperCase() === 'LMT'
}

/**
 * Generate unique order ID
 * @param {string} prefix - Prefix for the ID (optional)
 * @returns {string} Unique order ID
 */
export function generateOrderId(prefix = 'order') {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substring(2, 8)
  return `${prefix}_${timestamp}_${random}`
}

/**
 * Parse order data from different sources (IBKR, manual entry, etc.)
 * @param {Object} rawOrder - Raw order data
 * @param {string} source - Source of the order data
 * @returns {Object} Standardized order object
 */
export function parseOrderData(rawOrder, source = 'unknown') {
  if (!rawOrder) return null
  
  // Base order structure
  const standardOrder = {
    orderId: rawOrder.orderId || generateOrderId(),
    symbol: rawOrder.symbol || rawOrder.Symbol || '',
    action: rawOrder.action || rawOrder.Action || '',
    orderType: rawOrder.orderType || rawOrder.OrderType || '',
    totalQuantity: rawOrder.totalQuantity || rawOrder.TotalQuantity || rawOrder.quantity || 0,
    limitPrice: rawOrder.limitPrice || rawOrder.LimitPrice || null,
    stopPrice: rawOrder.stopPrice || rawOrder.StopPrice || null,
    status: rawOrder.status || rawOrder.Status || 'unknown',
    source: source,
    timestamp: rawOrder.timestamp || new Date().toISOString()
  }
  
  // Add any additional fields from the original order
  Object.keys(rawOrder).forEach(key => {
    if (!standardOrder.hasOwnProperty(key)) {
      standardOrder[key] = rawOrder[key]
    }
  })
  
  return standardOrder
}

/**
 * Group orders by symbol
 * @param {Array} orders - Array of order objects
 * @returns {Object} Object with symbols as keys and order arrays as values
 */
export function groupOrdersBySymbol(orders) {
  if (!Array.isArray(orders)) return {}
  
  return orders.reduce((groups, order) => {
    const symbol = order.symbol
    if (!groups[symbol]) {
      groups[symbol] = []
    }
    groups[symbol].push(order)
    return groups
  }, {})
}

/**
 * Sort orders by priority (main orders first, then by timestamp)
 * @param {Array} orders - Array of order objects
 * @returns {Array} Sorted array of orders
 */
export function sortOrdersByPriority(orders) {
  if (!Array.isArray(orders)) return []
  
  return [...orders].sort((a, b) => {
    // Main orders first
    const aIsMain = isMainOrder(a, orders)
    const bIsMain = isMainOrder(b, orders)
    
    if (aIsMain && !bIsMain) return -1
    if (!aIsMain && bIsMain) return 1
    
    // Then by timestamp (newest first)
    const aTime = new Date(a.timestamp || 0).getTime()
    const bTime = new Date(b.timestamp || 0).getTime()
    
    return bTime - aTime
  })
}

/**
 * Calculate order execution quality metrics
 * @param {Object} order - Executed order object
 * @returns {Object} Execution quality metrics
 */
export function calculateExecutionMetrics(order) {
  if (!order || !order.limitPrice || !order.executedPrice) {
    return { slippage: 0, slippagePercent: 0, executionQuality: 'unknown' }
  }
  
  const slippage = order.executedPrice - order.limitPrice
  const slippagePercent = (slippage / order.limitPrice) * 100
  
  let executionQuality = 'good'
  if (Math.abs(slippagePercent) > 1) {
    executionQuality = 'poor'
  } else if (Math.abs(slippagePercent) > 0.5) {
    executionQuality = 'fair'
  }
  
  return {
    slippage,
    slippagePercent,
    executionQuality
  }
}

/**
 * Determines if an order is a profit order (target)
 * @param {Object} order - Order object
 * @param {boolean} isShort - Whether position is short
 * @returns {boolean} True if it's a profit order
 */
export function isProfitOrder(order, isShort) {
  if (!order.currentPrice) return false;
  
  if (isShort) {
    // For short positions, BUY LMT orders below current price are profit targets
    return order.action.toUpperCase() === 'BUY' && 
           order.orderType.toUpperCase() === 'LMT' &&
           order.limitPrice < order.currentPrice;
  } else {
    // For long positions, SELL LMT orders above current price are profit targets
    return order.action.toUpperCase() === 'SELL' && 
           order.orderType.toUpperCase() === 'LMT' &&
           order.limitPrice > order.currentPrice;
  }
}

/**
 * Determines if an order is a risk order (stop loss)
 * @param {Object} order - Order object
 * @param {boolean} isShort - Whether position is short
 * @returns {boolean} True if it's a risk order
 */
export function isRiskOrder(order, isShort) {
  if (!order.currentPrice) return false;
  
  if (isShort) {
    // For short positions, BUY STP orders or BUY LMT orders above current price are stop losses
    return order.action.toUpperCase() === 'BUY' && 
           (order.orderType.toUpperCase() === 'STP' ||
           (order.orderType.toUpperCase() === 'LMT' && order.limitPrice > order.currentPrice));
  } else {
    // For long positions, SELL STP orders or SELL LMT orders below current price are stop losses
    return order.action.toUpperCase() === 'SELL' && 
           (order.orderType.toUpperCase() === 'STP' ||
           (order.orderType.toUpperCase() === 'LMT' && order.limitPrice < order.currentPrice));
  }
}

/**
 * Gets the percentage distance to target for an order
 * @param {Object} order - Order object
 * @param {boolean} isShort - Whether position is short
 * @param {number} currentPrice - Current price reference
 * @returns {number} Percentage distance or Infinity if not applicable
 */
export function getOrderPercentToTarget(order, isShort, currentPrice) {
  if (!order.limitPrice || !currentPrice) return Infinity;
  
  if (isShort) {
    // For short positions, target is below current price
    return isProfitOrder(order, isShort) ? 
      ((currentPrice - order.limitPrice) / currentPrice) * 100 : Infinity;
  } else {
    // For long positions, target is above current price
    return isProfitOrder(order, isShort) ?
      ((order.limitPrice - currentPrice) / currentPrice) * 100 : Infinity;
  }
}

/**
 * Gets the percentage distance to stop for an order
 * @param {Object} order - Order object
 * @param {boolean} isShort - Whether position is short
 * @param {number} currentPrice - Current price reference
 * @returns {number} Percentage distance or Infinity if not applicable
 */
export function getOrderPercentToStop(order, isShort, currentPrice) {
  if (!order.stopPrice && !order.limitPrice) return Infinity;
  
  const stopPrice = order.stopPrice || order.limitPrice;
  
  if (isShort) {
    // For short positions, stop is above current price
    return isRiskOrder(order, isShort) ?
      ((stopPrice - currentPrice) / currentPrice) * 100 : Infinity;
  } else {
    // For long positions, stop is below current price
    return isRiskOrder(order, isShort) ?
      ((currentPrice - stopPrice) / currentPrice) * 100 : Infinity;
  }
}

/**
 * Sorts orders by type (profit vs loss) and proximity to being hit
 * @param {Array} orders - Array of order objects
 * @param {boolean} isShort - Whether position is short
 * @param {number} currentPrice - Current price reference
 * @returns {Array} Sorted array of orders
 */
export function getSortedOrders(orders, isShort, currentPrice) {
  if (!orders || !orders.length) return [];
  
  // Make a copy to avoid mutating original
  const ordersCopy = [...orders];
  
  return ordersCopy.sort((a, b) => {
    // We need current price for accurate sorting
    if (!a.currentPrice) a.currentPrice = currentPrice;
    if (!b.currentPrice) b.currentPrice = currentPrice;
    
    // First group: profit orders (targets)
    const aIsProfit = isProfitOrder(a, isShort);
    const bIsProfit = isProfitOrder(b, isShort);
    
    // If one is profit and other is not, profit comes first
    if (aIsProfit && !bIsProfit) return -1;
    if (!aIsProfit && bIsProfit) return 1;
    
    // If both are profit orders, sort by % to target (lowest first)
    if (aIsProfit && bIsProfit) {
      const aPercent = getOrderPercentToTarget(a, isShort, currentPrice);
      const bPercent = getOrderPercentToTarget(b, isShort, currentPrice);
      return aPercent - bPercent; // Lower % (closer to target) comes first
    }
    
    // If both are risk/stop orders, sort by % to stop (lowest first)
    const aPercent = getOrderPercentToStop(a, isShort, currentPrice);
    const bPercent = getOrderPercentToStop(b, isShort, currentPrice);
    return aPercent - bPercent; // Lower % (closer to stop) comes first
  });
}