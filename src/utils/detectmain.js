/**
 * Detects if an order is a main order based on price relationships and order types
 * @param {Object} order - The order to check
 * @param {Array} allOrders - All orders to compare against
 * @param {Object} [externalPositionTypes] - Optional external position types mapping
 * @returns {boolean} - True if the order is a main order
 */
export const detectIfMainOrder = (order, allOrders, externalPositionTypes = {}) => {
  // Get all orders for this symbol
  const symbolOrders = allOrders.filter(o => o.symbol === order.symbol);
  
  if (symbolOrders.length <= 1) {
    return true; // If only one order for this symbol, it's the main order
  }

  // Determine position type from external mapping if available
  let isShort = false;
  if (externalPositionTypes.hasOwnProperty(order.symbol)) {
    isShort = externalPositionTypes[order.symbol];
  } else {
    // Try to determine position type based on order pattern
    // Count buy and sell orders
    const buyOrders = symbolOrders.filter(o => o.action.toUpperCase() === 'BUY');
    const sellOrders = symbolOrders.filter(o => o.action.toUpperCase() === 'SELL');
    
    // For long positions: typically 1 BUY and 2 SELL orders
    // For short positions: typically 1 SELL and 2 BUY orders
    if (buyOrders.length === 1 && sellOrders.length >= 1) {
      isShort = false; // Long position
    } else if (sellOrders.length === 1 && buyOrders.length >= 1) {
      isShort = true; // Short position
    }
  }
  
  // For a long position:
  // - Main order is the BUY LMT order (entry)
  // - Target is the higher SELL LMT order
  // - Stop is the lower SELL STP order
  // Price relationship: stop < entry < target (110.23 < 116.32 < 135.12)
  
  // For a short position:
  // - Main order is the SELL LMT order (entry)
  // - Target is the lower BUY LMT order
  // - Stop is the higher BUY STP order
  // Price relationship: target < entry < stop (25.53 < 29.73 < 30.64)
  
  if (isShort) {
    // For short positions, main order is SELL LMT
    if (order.action.toUpperCase() === 'SELL' && order.orderType.toUpperCase() === 'LMT') {
      return true;
    }
  } else {
    // For long positions, main order is BUY LMT
    if (order.action.toUpperCase() === 'BUY' && order.orderType.toUpperCase() === 'LMT') {
      // If there are multiple BUY LMT orders, need to determine which is the main entry
      const buyLmtOrders = symbolOrders.filter(o => 
        o.action.toUpperCase() === 'BUY' && o.orderType.toUpperCase() === 'LMT'
      );
      
      if (buyLmtOrders.length > 1) {
        // In case of multiple BUY LMT orders, the one with the largest quantity is likely the main order
        const mainOrder = buyLmtOrders.reduce((prev, curr) => 
          (curr.totalQuantity > prev.totalQuantity) ? curr : prev
        );
        
        return order.orderId === mainOrder.orderId;
      }
      
      return true;
    }
  }
  
  return false;
};

export default {
  detectIfMainOrder
}; 