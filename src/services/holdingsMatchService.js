import { ordersMatch } from '../utils/orderIdUtils';

/**
 * Service for matching orders with stock holdings
 */
class HoldingsMatchService {
  /**
   * Match orders with stock holdings to identify exit position orders
   * @param {Array} orders - Orders from IBKR or MongoDB
   * @param {Array} holdings - Stock holdings
   * @returns {Object} Object with matched and unmatched orders
   */
  matchOrdersWithHoldings(orders, holdings) {
    if (!orders || !holdings) {
      return {
        exitPositionOrders: [],
        newPositionOrders: orders || []
      };
    }

    const exitPositionOrders = [];
    const newPositionOrders = [];

    // Process each order
    orders.forEach(order => {
      // Find matching holding for this order
      const matchingHolding = this.findMatchingHolding(order, holdings);
      
      if (matchingHolding ) {
        // This is an exit position order
        exitPositionOrders.push({
          ...order,
          matchedHolding: matchingHolding,
          isExitPositionOrder: true
        });
      } else {
        // This is a new position order
        newPositionOrders.push({
          ...order,
          isExitPositionOrder: false
        });
      }
    });

    return { exitPositionOrders, newPositionOrders };
  }

  /**
   * Find matching holding for an order
   * @param {Object} order - Order to match
   * @param {Array} holdings - Stock holdings
   * @returns {Object|null} Matching holding or null
   */
  findMatchingHolding(order, holdings) {
    if (!order || !holdings) return null;

    // Find holding with same symbol
    const symbolHolding = holdings.find(holding => holding.symbol === order.symbol);
    if (!symbolHolding) return null;

    // Check if this is potentially an exit order
    const shares = symbolHolding.shares || 0;
    
    // For long positions (positive shares), a SELL order could be an exit
    if (shares > 0 && order.action.toLowerCase() === 'sell') {
      // Check if quantities match for a full exit or partial exit
      if (order.totalQuantity <= Math.abs(shares)) {
        console.log(`Exit position match found: ${order.symbol} SELL ${order.totalQuantity} (holding: ${shares})`);
        return symbolHolding;
      }
    }
    // For short positions (negative shares), a BUY order could be an exit
    else if (shares < 0 && order.action.toLowerCase() === 'buy') {
      // Check if quantities match for a full exit or partial exit
      if (order.totalQuantity <= Math.abs(shares)) {
        console.log(`Exit position match found: ${order.symbol} BUY ${order.totalQuantity} (holding: ${shares})`);
        return symbolHolding;
      }
    }

    // Log when we don't consider an order as an exit position
    console.log(`Not an exit position: ${order.symbol} ${order.action} ${order.totalQuantity} (holding shares: ${shares})`);
    
    // No match found
    return null;
  }

  /**
   * Update orders with holding information
   * @param {Array} orders - Orders to update
   * @param {Array} holdings - Stock holdings
   * @returns {Array} Updated orders
   */
  updateOrdersWithHoldingInfo(orders, holdings) {
    if (!orders || !holdings) return orders || [];

    // Match orders with holdings
    const { exitPositionOrders, newPositionOrders } = this.matchOrdersWithHoldings(orders, holdings);

    // Combine and return updated orders
    return [...exitPositionOrders, ...newPositionOrders];
  }
}

export default new HoldingsMatchService(); 