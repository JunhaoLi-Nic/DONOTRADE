/**
 * Trade Order Tracking System
 * 
 * This is the main entry point for the trade order tracking system.
 * It integrates the executed trade detection and merge functionality.
 */

import ExecutedTradeDetector from './executedTradeDetector';
import TradeMerger from './tradeMerger';

class TradeTracker {
  /**
   * Processes current stock holdings to detect executed trades and perform merges
   * @param {Array<Object>} stockHoldings - Current stock holdings from IBKR
   * @returns {Promise<Object>} Processing results
   */
  async processHoldings(stockHoldings) {
    if (!stockHoldings || stockHoldings.length === 0) {
      return { 
        success: true, 
        executed: [], 
        merged: [],
        message: 'No stock holdings to process' 
      };
    }
    
    try {
      console.log(`Processing ${stockHoldings.length} holdings for executed trades and merges`);
      
      // Step 1: Detect executed trades
      const updatedOrders = await ExecutedTradeDetector.detectExecutedTrades(stockHoldings);
      
      // Step 2: Process merges for any newly bought positions
      const mergeResults = [];
      
      for (const order of updatedOrders) {
        // Find the corresponding IBKR holding for this order
        const ibkrHolding = stockHoldings.find(holding => holding.symbol === order.symbol);
        
        // Process for potential merge
        const mergeResult = await TradeMerger.processNewBoughtPosition(order, ibkrHolding);
        
        if (mergeResult.success && mergeResult.merged) {
          mergeResults.push(mergeResult);
        }
      }
      
      // Return combined results
      return {
        success: true,
        executed: updatedOrders,
        merged: mergeResults,
        message: `Processed ${updatedOrders.length} executed trades and ${mergeResults.length} merges`
      };
    } catch (error) {
      console.error('Error processing holdings:', error);
      return {
        success: false,
        executed: [],
        merged: [],
        message: `Error processing holdings: ${error.message || 'Unknown error'}`
      };
    }
  }
  
  /**
   * Manually process a newly bought position for merging
   * @param {Object} position - Position to process
   * @param {Object} ibkrHolding - IBKR holding data (optional)
   * @returns {Promise<Object>} Merge result
   */
  async processBoughtPosition(position, ibkrHolding = null) {
    if (!position || position.currentState !== 'bought') {
      return { 
        success: false, 
        message: 'Position must be in bought state for merge processing' 
      };
    }
    
    return await TradeMerger.processNewBoughtPosition(position, ibkrHolding);
  }
}

export default new TradeTracker();

// Also export individual services for direct access if needed
export { ExecutedTradeDetector, TradeMerger }; 