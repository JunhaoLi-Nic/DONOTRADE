/**
 * Utilities for generating unique order IDs and matching orders between IBKR and MongoDB
 */

/**
 * Generates a unique order ID based on order properties
 * @param {Object} order - The order object from IBKR
 * @returns {string} A unique order ID
 */
export const generateOrderId = (order) => {
  if (!order) return null;
  
  // If the order already has a TradeNote ID, return it
  if (order.tradeNoteId) return order.tradeNoteId;
  
  // Extract key properties for generating a unique ID
  const {
    symbol,
    action,
    orderType,
    totalQuantity,
    limitPrice,
    stopPrice,
    status
  } = order;
  
  // Create a base string from order properties
  const baseString = `${symbol}-${action}-${orderType}-${totalQuantity}-${limitPrice || 0}-${stopPrice || 0}-${status || 'unknown'}`;
  
  // Add timestamp for uniqueness
  const timestamp = new Date().getTime();
  
  // Generate a hash from the base string
  const hash = simpleHash(baseString + timestamp);
  
  // Return a formatted ID
  return `TN-${symbol}-${hash}`;
};

/**
 * Simple string hashing function
 * @param {string} str - String to hash
 * @returns {string} Hashed string
 */
const simpleHash = (str) => {
  let hash = 0;
  if (!str || str.length === 0) return hash.toString(16);
  
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  
  // Convert to hex string and take last 8 characters
  return Math.abs(hash).toString(16).slice(-8).toUpperCase();
};

/**
 * Checks if two orders match based on their properties
 * @param {Object} order1 - First order to compare
 * @param {Object} order2 - Second order to compare
 * @returns {boolean} True if orders match
 */
export const ordersMatch = (order1, order2) => {
  if (!order1 || !order2) return false;
  
  // Check key properties
  return (
    order1.symbol === order2.symbol &&
    order1.action === order2.action &&
    order1.orderType === order2.orderType &&
    order1.totalQuantity === order2.totalQuantity &&
    (
      // Either both have same limit price or both don't have limit price
      (order1.limitPrice === order2.limitPrice) ||
      (!order1.limitPrice && !order2.limitPrice)
    ) &&
    (
      // Either both have same stop price or both don't have stop price
      (order1.stopPrice === order2.stopPrice) ||
      (!order1.stopPrice && !order2.stopPrice)
    )
  );
};

/**
 * Finds matching orders between two arrays based on properties
 * @param {Array} sourceOrders - Source array of orders
 * @param {Array} targetOrders - Target array to find matches in
 * @returns {Object} Object with matches and unmatched orders
 */
export const findMatchingOrders = (sourceOrders, targetOrders) => {
  if (!sourceOrders || !targetOrders) {
    return { 
      matches: [], 
      unmatchedSource: sourceOrders || [], 
      unmatchedTarget: targetOrders || [] 
    };
  }
  
  const matches = [];
  const matchedTargetIndices = new Set();
  const unmatchedSource = [];
  
  // Find matches for source orders
  sourceOrders.forEach(sourceOrder => {
    let matched = false;
    
    for (let i = 0; i < targetOrders.length; i++) {
      // Skip already matched target orders
      if (matchedTargetIndices.has(i)) continue;
      
      if (ordersMatch(sourceOrder, targetOrders[i])) {
        matches.push({
          source: sourceOrder,
          target: targetOrders[i]
        });
        matchedTargetIndices.add(i);
        matched = true;
        break;
      }
    }
    
    if (!matched) {
      unmatchedSource.push(sourceOrder);
    }
  });
  
  // Collect unmatched target orders
  const unmatchedTarget = targetOrders.filter((_, index) => !matchedTargetIndices.has(index));
  
  return { matches, unmatchedSource, unmatchedTarget };
};

/**
 * Merges order data from IBKR with stored data from MongoDB
 * @param {Object} ibkrOrder - Order data from IBKR
 * @param {Object} storedOrder - Order data from MongoDB
 * @returns {Object} Merged order object
 */
export const mergeOrderData = (ibkrOrder, storedOrder) => {
  if (!ibkrOrder) return storedOrder;
  if (!storedOrder) return ibkrOrder;
  
  // Create a new object with IBKR data as base
  const mergedOrder = { ...ibkrOrder };
  
  // Add or override with stored data from MongoDB
  mergedOrder.tradeNoteId = storedOrder.tradeNoteId || storedOrder.orderId;
  mergedOrder.catalystData = storedOrder.catalystData;
  mergedOrder.reasonData = storedOrder.reasonData;
  mergedOrder.reasonCompleted = !!storedOrder.reasonData;
  mergedOrder.isMainOrder = storedOrder.isMainOrder || storedOrder.isExecutedOrder;
  mergedOrder.subOrderIds = storedOrder.subOrderIds || [];
  mergedOrder.positionType = storedOrder.positionType;
  
  return mergedOrder;
}; 