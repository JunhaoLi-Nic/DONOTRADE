import axios from '../config/api';
import { ORDER_ENDPOINTS } from '../config/api';
import { 
  generateOrderId, 
  findMatchingOrders, 
  mergeOrderData 
} from '../utils/orderIdUtils';
import { detectIfMainOrder } from '../utils/detectmain';

/**
 * Service for synchronizing orders between IBKR and MongoDB
 */
class OrderSyncService {
  /**
   * Fetch orders from MongoDB
   * @returns {Promise<Array>} Array of orders from MongoDB
   */
  async fetchOrdersFromMongoDB() {
    try {
      console.log('Fetching orders from MongoDB...');
      const response = await axios.get('/api/orders');
      const orders = response.data || [];
      
      // Process orders to ensure all necessary fields are properly set
      const processedOrders = orders.map(order => {
        // Make sure reasonCompleted is set based on reasonData
        if (order.reasonData) {
          order.reasonCompleted = true;
        }
        
        // Set main order flag for UI compatibility
        order.isMainOrder = order.isExecutedOrder === true;
        
        // Set position type flags
        if (order.positionType) {
          order.isShort = order.positionType === 'short';
        }
        
        return order;
      });
      
      console.log(`Fetched and processed ${processedOrders.length} orders from MongoDB`);
      return processedOrders;
    } catch (error) {
      console.error('Error fetching orders from MongoDB:', error);
      // Don't throw the error, just return an empty array
      return [];
    }
  }

  /**
   * Process IBKR orders by adding TradeNote IDs and matching with MongoDB data
   * @param {Array} ibkrOrders - Orders from IBKR
   * @param {Object} positionTypes - Position types map
   * @param {Array} stockHoldings - Current stock holdings (optional)
   * @returns {Promise<Array>} Processed orders with TradeNote IDs
   */
  async processIbkrOrders(ibkrOrders, positionTypes = {}, stockHoldings = []) {
    if (!ibkrOrders || ibkrOrders.length === 0) {
      return [];
    }

    try {
      // Step 1: Fetch stored orders from MongoDB
      const storedOrders = await this.fetchOrdersFromMongoDB();
      
      // Log stored orders with MongoDB IDs for debugging
      if (storedOrders.length > 0) {
        console.log(`Found ${storedOrders.length} stored orders in MongoDB with IDs:`);
        storedOrders.forEach(order => {
          if (order._id) {
            console.log(`- ${order.symbol}: MongoDB ID = ${order._id}`);
            // Ensure mongoDbId is set
            order.mongoDbId = order._id;
          }
        });
      }
      
      // Step 2: Find matches between IBKR orders and stored orders
      const { matches, unmatchedSource } = findMatchingOrders(ibkrOrders, storedOrders);
      
      // Step 3: Process matched orders - merge data from MongoDB with IBKR data
      const processedMatches = matches.map(match => {
        // Preserve MongoDB ID when merging
        const mergedOrder = mergeOrderData(match.source, match.target);
        
        // Ensure MongoDB ID is preserved
        if (match.target._id) {
          mergedOrder._id = match.target._id;
          mergedOrder.mongoDbId = match.target._id;
          console.log(`Preserved MongoDB ID ${match.target._id} for ${mergedOrder.symbol}`);
        }
        
        return mergedOrder;
      });
      
      // Step 4: Process unmatched orders - generate new TradeNote IDs
      const processedUnmatched = unmatchedSource.map(order => {
        // Generate a new TradeNote ID
        const tradeNoteId = generateOrderId(order);
        
        // Determine if this is a main order
        const isMainOrder = detectIfMainOrder(order, ibkrOrders, positionTypes);
        
        return {
          ...order,
          tradeNoteId,
          isMainOrder
        };
      });
      
      // Step 5: Combine processed orders
      const processedOrders = [...processedMatches, ...processedUnmatched];
      
      // Step 6: Set up parent-child relationships for orders
      const ordersWithRelationships = this.setupOrderRelationships(processedOrders);
      
      // Log information about the processed orders
      console.log(`Processed ${ibkrOrders.length} IBKR orders:`);
      console.log(`- ${processedMatches.length} matched with MongoDB orders`);
      console.log(`- ${processedUnmatched.length} new orders with generated IDs`);
      console.log(`- ${ordersWithRelationships.filter(o => o.isMainOrder).length} main orders`);
      
      return ordersWithRelationships;
    } catch (error) {
      console.error('Error processing IBKR orders:', error);
      throw error;
    }
  }

  /**
   * Set up parent-child relationships between orders
   * @param {Array} orders - Processed orders
   * @returns {Array} Orders with parent-child relationships
   */
  setupOrderRelationships(orders) {
    // Create a map of orders by symbol and order type (new position vs exit position)
    const ordersBySymbolAndType = {};
    
    // Group orders by symbol and order type
    orders.forEach(order => {
      const isExitOrder = order.isExitPositionOrder === true;
      const key = `${order.symbol}-${isExitOrder ? 'exit' : 'new'}`;
      
      if (!ordersBySymbolAndType[key]) {
        ordersBySymbolAndType[key] = [];
      }
      ordersBySymbolAndType[key].push(order);
    });
    
    // For each group, set up relationships
    Object.values(ordersBySymbolAndType).forEach(groupOrders => {
      if (groupOrders.length === 0) return;
      
      // Find the main order for this group
      const mainOrder = groupOrders.find(order => order.isMainOrder);
      
      if (mainOrder) {
        // Get sub-orders for this group
        const subOrders = groupOrders.filter(order => 
          order.tradeNoteId !== mainOrder.tradeNoteId && !order.isMainOrder
        );
        
        // Update main order with sub-order IDs
        mainOrder.subOrderIds = subOrders.map(order => order.tradeNoteId || order.orderId);
        
        // Update sub-orders with parent ID
        subOrders.forEach(subOrder => {
          subOrder.parentOrderId = mainOrder.tradeNoteId || mainOrder.orderId;
        });
      }
    });
    
    return orders;
  }

  /**
   * Save main orders to MongoDB (only from new position orders)
   * @param {Array} orders - Processed orders
   * @returns {Promise<Array>} Saved orders
   */
  async saveMainOrdersToMongoDB(orders) {
    if (!orders || orders.length === 0) {
      return [];
    }

    try {
      // Strictly filter for main orders from new position orders only
      const mainNewPositionOrders = orders.filter(order => {
        // Must be a main order
        if (!order.isMainOrder) return false;
        
        // Must NOT be explicitly marked as an exit position order
        if (order.isExitPositionOrder === true) return false;
        
        // For additional safety, check action type against position type
        // For new positions: BUY for long positions, SELL for short positions
        const isLongPosition = order.positionType !== 'short';
        const isBuyAction = order.action && order.action.toUpperCase() === 'BUY';
        const isSellAction = order.action && order.action.toUpperCase() === 'SELL';
        
        // Only include orders that match the expected action for a new position
        const isValidNewPosition = (isLongPosition && isBuyAction) || (!isLongPosition && isSellAction);
        
        // Log the decision for debugging
        console.log(`Order ${order.symbol}: isMainOrder=${order.isMainOrder}, isExitPositionOrder=${order.isExitPositionOrder}, ` +
                    `positionType=${order.positionType}, action=${order.action}, isValidNewPosition=${isValidNewPosition}`);
        
        return isValidNewPosition;
      });
      
      if (mainNewPositionOrders.length === 0) {
        console.log("No valid main orders from new positions found to save");
        return [];
      }
      
      // Log the orders we're about to save
      console.log(`Found ${mainNewPositionOrders.length} valid main orders from new positions:`);
      mainNewPositionOrders.forEach(order => {
        console.log(`- ${order.symbol} (${order.action} ${order.orderType}): ${order.totalQuantity} @ ${order.limitPrice || order.stopPrice}`);
        // Log if this is an update to an existing order
        if (order.mongoDbId || order._id) {
          console.log(`  This is an update to existing order with ID: ${order.mongoDbId || order._id}`);
        }
        // Log source field
        if (order.source) {
          console.log(`  Order source: ${order.source}`);
        }
      });
      
      // Prepare orders for saving with all table column data
      const ordersToSave = mainNewPositionOrders.map(order => {
        // Ensure potential profit values are positive
        const potentialProfit = order.potentialProfit ? Math.abs(order.potentialProfit) : null;
        const potentialProfitPercent = order.potentialProfitPercent ? Math.abs(order.potentialProfitPercent) : null;
        
        // Calculate position value if not already present
        let positionValue = order.positionValue;
        if (!positionValue && order.limitPrice && order.totalQuantity) {
          positionValue = order.limitPrice * order.totalQuantity;
        }
        
        // Calculate allocation percent if not already present
        let allocationPercent = order.positionSizePercent || order.allocationPercent;
        
        // Use MongoDB ID if available for updates
        const mongoDbId = order.mongoDbId || order._id;
        
        // Preserve source field for duplicate detection
        const source = order.source || null;
        
        return {
          ...order,
          orderId: order.tradeNoteId, // Use TradeNote ID as the MongoDB ID
          mongoDbId: mongoDbId, // Include mongoDbId if it exists for updates
          source: source, // Preserve source field for duplicate detection
          isExecutedOrder: true,
          timestamp: new Date(),
          // Mark as preorder for duplicate detection
          currentState: "preorder",
          // Ensure reasonCompleted is set if reasonData exists
          reasonCompleted: order.reasonData ? true : order.reasonCompleted,
          // Ensure all table column data is included
          symbol: order.symbol,
          action: order.action,
          orderType: order.orderType,
          totalQuantity: order.totalQuantity,
          limitPrice: order.limitPrice,
          stopPrice: order.stopPrice,
          currentPrice: order.currentPrice,
          positionValue: positionValue,
          allocationPercent: allocationPercent,
          stopLossRisk: order.stopLossRisk,
          stopLossPercent: order.stopLossPercent,
          potentialProfit: potentialProfit,
          potentialProfitPercent: potentialProfitPercent,
          riskRewardRatio: order.riskRewardRatio,
          status: order.status
        };
      });
      
      console.log(`Saving ${ordersToSave.length} main orders from new positions to MongoDB`);
      
      // Log the metrics for each order being saved
      ordersToSave.forEach(order => {
        console.log(`Order ${order.symbol} metrics:
          Position Value: $${order.positionValue?.toFixed(2)}
          Allocation: ${order.allocationPercent?.toFixed(2)}%
          Stop Loss Risk: $${order.stopLossRisk?.toFixed(2)}
          Stop Loss %: ${order.stopLossPercent?.toFixed(2)}%
          Potential Profit: $${order.potentialProfit?.toFixed(2)}
          Profit %: ${order.potentialProfitPercent?.toFixed(2)}%
          Risk/Reward: ${order.riskRewardRatio?.toFixed(2)}
        `);
      });
      
      // Save to MongoDB
      const response = await axios.post('/api/orders', { orders: ordersToSave });
      
      // Check the response format
      console.log('MongoDB response:', response.data);
      
      // Handle different response formats
      if (response.status === 200) {
        // Check if the response contains information about duplicate preorders
        if (response.data && response.data.duplicates) {
          console.log(`Server found ${response.data.duplicates} duplicate preorders`);
        }
        
        // If the response is empty but status is 200, the orders were likely saved
        if (!response.data || (Array.isArray(response.data) && response.data.length === 0)) {
          // Return a success indicator with count
          return { 
            success: true, 
            count: ordersToSave.length,
            message: `${ordersToSave.length} orders saved successfully`
          };
        }
        // Return the actual data if available
        return response.data;
      }
      
      return [];
    } catch (error) {
      console.error('Error saving orders to MongoDB:', error);
      throw error;
    }
  }

  /**
   * Update an existing order, primarily for reasonData
   * @param {Object} order - The order to update
   * @returns {Promise<Object>} Response from API
   */
  async updateOrderReasonData(order) {
    if (!order) return null;
    
    try {
      console.log(`Updating order ${order.symbol} with reasonData`);
      
      // Make sure we have an orderId to update - try multiple possible ID fields
      const orderId = order.mongoDbId || order._id || order.tradeNoteId || order.orderId;
      if (!orderId) {
        console.error('No order ID available for update');
        return { success: false, message: 'No order ID available for update' };
      }
      
      // Log the ID we're using
      console.log(`Using ID for update: ${orderId}`);
      
      // Prepare the data to send
      const orderData = {
        ...order,
        orderId: orderId
      };
      
      // Use the dedicated update endpoint
      const response = await axios.post(ORDER_ENDPOINTS.UPDATE_ORDER, { order: orderData });
      
      console.log(`Order update response:`, response.data);
      return response.data;
    } catch (error) {
      console.error('Error updating order reasonData:', error);
      throw error;
    }
  }

  // Track last fetch time for rate limiting
  #lastPreviousBuyOrdersFetch = 0;
  #minFetchInterval = 3000; // 3 seconds minimum between fetches
  
  // Function to fetch previous buy orders from MongoDB
  async fetchPreviousBuyOrders(currentOpenOrders) {
    try {
      // Implement rate limiting
      const now = Date.now();
      if (now - this.#lastPreviousBuyOrdersFetch < this.#minFetchInterval) {
        console.log(`Rate limiting: Skipping fetch, last fetch was ${now - this.#lastPreviousBuyOrdersFetch}ms ago`);
        return []; // Return empty array when rate limited
      }
      
      console.log('Fetching previous buy orders with state=preorder');
      this.#lastPreviousBuyOrdersFetch = now;
      
      // Add cache-busting parameter to prevent browser caching
      const timestamp = new Date().getTime();
      const response = await axios.get(`/api/orders/state/preorder?_t=${timestamp}`);
      const allOrders = response.data;

      console.log(`Retrieved ${allOrders.length} orders with state=preorder from MongoDB`);

      // Create a more robust way to check if orders exist in the IBKR feed
      // by comparing symbol, action, quantity and price, not just orderId
      const previousBuyOrders = allOrders.filter(preorder => {
        // Skip if order doesn't have required fields for comparison
        if (!preorder.symbol || !preorder.action || !preorder.totalQuantity) {
          return false;
        }
        
        // Check if this preorder exists in any of the current open orders
        const existsInOpenOrders = (currentOpenOrders || []).some(openOrder => {
          // First try matching by orderId if available
          if (preorder.orderId && openOrder.orderId === preorder.orderId) {
            return true;
          }
          
          // Then try matching by a combination of symbol, action, and quantity
          if (openOrder.symbol === preorder.symbol && 
              openOrder.action === preorder.action &&
              Math.abs(openOrder.totalQuantity - preorder.totalQuantity) < 0.001) {
            return true;
          }
          
          return false;
        });
        
        // Include orders that are in "PendingCancel" status
        const isPendingCancel = preorder.status === "PendingCancel";
        
        // Return orders that:
        // 1. Don't exist in open orders OR
        // 2. Have a status of "PendingCancel"
        return !existsInOpenOrders || isPendingCancel;
      });

      console.log(`Found ${previousBuyOrders.length} previous buy orders not in the current open orders table`);

      // Process these orders with price data, timestamps, etc.
      const processedOrders = previousBuyOrders.map(order => {
        // Ensure these fields exist
        return {
          ...order,
          mongoDbId: order._id || order.mongoDbId || order.orderId,
          isMainOrder: true, // Treat all previous buy orders as main orders
          currentState: order.currentState || 'preorder',
          savedAt: order.savedAt || order.timestamp || new Date().toISOString()
        };
      });

      return processedOrders;
    } catch (error) {
      console.error('Error fetching previous buy orders:', error);
      return []; // Return empty array instead of throwing to prevent cascading errors
    }
  }

  // Update an order's state (e.g., to cancel)
  async updateOrderState(orderId, newState) {
    try {
      console.log(`Updating order ${orderId} to state ${newState}`);
      
      // Instead of trying to find the order first, just send the update with the orderId
      // This is more efficient and avoids the issue of not finding the order
      const orderData = {
        orderId: orderId,
        currentState: newState,
        updatedAt: new Date().toISOString()
      };

      // Send update to API - the backend will find the order by ID
      const updateResponse = await axios.post('/api/orders/update', { order: orderData });
      console.log('Update response:', updateResponse.data);
      return updateResponse.data;
    } catch (error) {
      console.error(`Error updating order ${orderId} to state ${newState}:`, error);
      return { success: false, message: error.message || 'Error updating order' };
    }
  }

  // Fix orders in MongoDB that are missing required fields
  async fixMissingOrderFields() {
    try {
      console.log('Fixing orders with missing fields in MongoDB...');
      const response = await axios.post('/api/orders/fix-missing-fields');
      
      if (response.data && response.data.success) {
        console.log(`Fixed ${response.data.updated_count} orders with missing fields`);
        return response.data;
      } else {
        console.error('Failed to fix orders with missing fields');
        return { success: false, message: 'Failed to fix orders with missing fields' };
      }
    } catch (error) {
      console.error('Error fixing orders with missing fields:', error);
      throw error;
    }
  }
}

export default new OrderSyncService(); 