/**
 * Executed Trade Detector
 * 
 * This module detects when preorders have been executed and appear in the stock holdings.
 * It compares MongoDB orders with currentState="preorder" against current stock holdings
 * to identify executed trades and update their state to "bought".
 */

import axios from '../config/api';
import { ORDER_ENDPOINTS } from '../config/api';

class ExecutedTradeDetector {
  /**
   * Fetches all preorders from MongoDB
   * @returns {Promise<Array>} Array of orders with currentState="preorder"
   */
  async fetchPreorders() {
    try {
      console.log('Fetching preorders from MongoDB...');
      const response = await axios.get('/api/orders/state/preorder');
      
      if (!Array.isArray(response.data)) {
        console.error('Invalid response format for preorders:', response.data);
        return [];
      }
      
      const preorders = response.data;
      console.log(`Found ${preorders.length} preorders in MongoDB`);
      return preorders;
    } catch (error) {
      console.error('Error fetching preorders from MongoDB:', error);
      return [];
    }
  }
  
  /**
   * Fetches existing bought positions for the given symbols
   * @param {Array<string>} symbols - Array of stock symbols to fetch
   * @returns {Promise<Object>} Map of symbol to array of bought positions
   */
  async fetchExistingPositions(symbols) {
    try {
      if (!symbols || symbols.length === 0) return {};
      
      console.log(`Fetching existing positions for ${symbols.length} symbols...`);
      const response = await axios.get('/api/orders/state/bought');
      
      if (!Array.isArray(response.data)) {
        console.error('Invalid response format for bought positions:', response.data);
        return {};
      }
      
      // Group positions by symbol
      const positionsBySymbol = {};
      response.data.forEach(position => {
        if (symbols.includes(position.symbol)) {
          if (!positionsBySymbol[position.symbol]) {
            positionsBySymbol[position.symbol] = [];
          }
          positionsBySymbol[position.symbol].push(position);
        }
      });
      
      const symbolCount = Object.keys(positionsBySymbol).length;
      console.log(`Found existing positions for ${symbolCount} symbols`);
      
      return positionsBySymbol;
    } catch (error) {
      console.error('Error fetching existing positions:', error);
      return {};
    }
  }
  
  /**
   * Calculates total position size for a symbol from existing bought positions
   * @param {Array<Object>} positions - Array of bought positions for a symbol
   * @returns {number} Total position size (quantity)
   */
  calculateTotalPositionSize(positions) {
    if (!positions || positions.length === 0) return 0;
    
    return positions.reduce((total, position) => {
      // Handle position quantity in different formats
      const quantity = position.totalQuantity || position.quantity || position.shares || 0;
      return total + quantity;
    }, 0);
  }
  
  /**
   * Calculates weighted average entry price from existing positions
   * @param {Array<Object>} positions - Array of positions
   * @returns {number} Weighted average entry price
   */
  calculateWeightedAveragePrice(positions) {
    if (!positions || positions.length === 0) return 0;
    
    let totalQuantity = 0;
    let weightedSum = 0;
    
    positions.forEach(position => {
      const quantity = position.totalQuantity || position.quantity || position.shares || 0;
      const price = position.entryPrice || position.limitPrice || 0;
      
      totalQuantity += quantity;
      weightedSum += (quantity * price);
    });
    
    return totalQuantity > 0 ? weightedSum / totalQuantity : 0;
  }
  
  /**
   * Updates an order's state from "preorder" to "bought"
   * @param {Object} order - The order to update
   * @returns {Promise<Object>} Response from API
   */
  async updateOrderToBought(order) {
    if (!order) return null;
    
    try {
      console.log(`Updating order ${order.symbol} from preorder to bought`);
      
      const orderId = order.mongoDbId || order._id || order.tradeNoteId || order.orderId;
      if (!orderId) {
        console.error('No order ID available for update');
        return { success: false, message: 'No order ID available for update' };
      }
      
      // Prepare the data to send
      const orderData = {
        ...order,
        orderId: orderId,
        currentState: "bought",
        executedAt: new Date().toISOString(),
      };
      
      // Use the dedicated update endpoint
      const response = await axios.post(ORDER_ENDPOINTS.UPDATE_ORDER, { order: orderData });
      
      console.log(`Order update response:`, response.data);
      return response.data;
    } catch (error) {
      console.error('Error updating order to bought state:', error);
      return { success: false, message: error.message || 'Error updating order' };
    }
  }
  
  /**
   * Detects if a preorder has been executed by comparing with current holdings
   * @param {Object} preorder - Preorder from MongoDB
   * @param {Array<Object>} stockHoldings - Current stock holdings
   * @param {Object} existingPositionsBySymbol - Map of existing bought positions by symbol
   * @returns {boolean} True if preorder appears to be executed
   */
  isPreorderExecuted(preorder, stockHoldings, existingPositionsBySymbol) {
    if (!preorder || !stockHoldings) return false;
    
    // Find matching holding for this preorder
    const matchingHolding = stockHoldings.find(holding => holding.symbol === preorder.symbol);
    if (!matchingHolding) return false;
    
    // Get existing positions for this symbol
    const existingPositions = existingPositionsBySymbol[preorder.symbol] || [];
    
    // Calculate total quantity from existing positions
    const existingQuantity = this.calculateTotalPositionSize(existingPositions);
    
    // Get preorder quantity (could be named differently in different contexts)
    const preorderQuantity = preorder.totalQuantity || preorder.quantity || 0;
    
    // Get current holding quantity
    const holdingQuantity = Math.abs(matchingHolding.shares || 0);
    
    // Position type check (long/short)
    const isShortPreorder = (preorder.action === 'SELL' || preorder.action === 'SS');
    const isShortHolding = matchingHolding.isShort || (matchingHolding.shares < 0);
    
    // Position type should match
    if (isShortPreorder !== isShortHolding) {
      console.log(`Position type mismatch for ${preorder.symbol}: Preorder=${isShortPreorder}, Holding=${isShortHolding}`);
      return false;
    }
    
    // Check if holding quantity >= (existing quantity + preorder quantity)
    // Allow for some tolerance in case of rounding issues
    const tolerance = 0.01; // 1% tolerance
    const expectedMinQuantity = existingQuantity + preorderQuantity;
    const quantityRatio = holdingQuantity / expectedMinQuantity;
    
    const isQuantityMatch = quantityRatio >= (1 - tolerance);
    
    console.log(`Quantity check for ${preorder.symbol}: Holding=${holdingQuantity}, Expected=${expectedMinQuantity}, Ratio=${quantityRatio.toFixed(2)}`);
    
    return isQuantityMatch;
  }
  
  /**
   * Processes current stock holdings to detect and update executed preorders
   * @param {Array<Object>} stockHoldings - Current stock holdings
   * @returns {Promise<Array>} List of updated orders
   */
  async detectExecutedTrades(stockHoldings) {
    if (!stockHoldings || stockHoldings.length === 0) {
      console.log('No stock holdings to check for executed trades');
      return [];
    }

    try {
      // Step 1: Fetch all preorders from MongoDB
      const preorders = await this.fetchPreorders();
      if (preorders.length === 0) {
        console.log('No preorders to check for execution');
        return [];
      }

      // Step 2: Get list of unique symbols from preorders
      const preorderSymbols = [...new Set(preorders.map(order => order.symbol))];
      
      // Step 3: Fetch existing bought positions for these symbols
      const existingPositionsBySymbol = await this.fetchExistingPositions(preorderSymbols);
      
      // Step 4: Check each preorder against holdings to detect execution
      const updatedOrders = [];
      
      for (const preorder of preorders) {
        const isExecuted = this.isPreorderExecuted(preorder, stockHoldings, existingPositionsBySymbol);
        
        if (isExecuted) {
          console.log(`Detected executed trade: ${preorder.symbol} (${preorder.action} ${preorder.totalQuantity})`);
          
          // Update the preorder to "bought" state
          const updateResult = await this.updateOrderToBought(preorder);
          
          if (updateResult && updateResult.success) {
            updatedOrders.push({
              ...preorder,
              currentState: "bought",
              executedAt: new Date().toISOString()
            });
          }
        }
      }
      
      console.log(`Detected and updated ${updatedOrders.length} executed trades`);
      return updatedOrders;
    } catch (error) {
      console.error('Error detecting executed trades:', error);
      return [];
    }
  }
}

export default new ExecutedTradeDetector(); 