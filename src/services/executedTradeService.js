/**
 * Executed Trade Service
 * 
 * This service provides an interface for other components to access
 * the trade tracking and merging functionality.
 */

import tradeTracker from '../trackOrder';

class ExecutedTradeService {
  /**
   * Process stock holdings to detect executed trades and perform merges
   * @param {Array<Object>} stockHoldings - Current stock holdings from IBKR
   * @returns {Promise<Object>} Processing results with executed and merged trades
   */
  async processStockHoldings(stockHoldings) {
    if (!stockHoldings || stockHoldings.length === 0) {
      return { 
        success: true, 
        executed: [], 
        merged: [],
        message: 'No stock holdings to process' 
      };
    }
    
    try {
      return await tradeTracker.processHoldings(stockHoldings);
    } catch (error) {
      console.error('Error processing stock holdings:', error);
      return {
        success: false,
        executed: [],
        merged: [],
        message: error.message || 'Error processing stock holdings'
      };
    }
  }
  
  /**
   * Manually process a bought position for potential merging
   * @param {Object} position - Position to check for merging
   * @param {Object} ibkrHolding - Matching IBKR holding (optional)
   * @returns {Promise<Object>} Merge result
   */
  async processBoughtPosition(position, ibkrHolding = null) {
    if (!position) {
      return { success: false, message: 'No position provided' };
    }
    
    try {
      return await tradeTracker.processBoughtPosition(position, ibkrHolding);
    } catch (error) {
      console.error('Error processing bought position:', error);
      return {
        success: false,
        merged: false,
        message: error.message || 'Error processing bought position'
      };
    }
  }
}

export default new ExecutedTradeService(); 