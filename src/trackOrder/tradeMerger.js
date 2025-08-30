/**
 * Trade Merger
 * 
 * This module handles merging of multiple "bought" positions for the same symbol.
 * It creates consolidated position records and updates original records with merge references.
 */

import axios from '../config/api';
import { ORDER_ENDPOINTS } from '../config/api';

class TradeMerger {
  /**
   * Fetches existing bought positions for the given symbol
   * @param {string} symbol - Stock symbol to fetch positions for
   * @returns {Promise<Array>} Array of bought positions for the symbol
   */
  async fetchBoughtPositionsForSymbol(symbol) {
    try {
      if (!symbol) return [];
      
      console.log(`Fetching bought positions for symbol ${symbol}...`);
      // Use symbol filter parameter if available, otherwise fetch all and filter
      const response = await axios.get(`/api/orders/state/bought?symbol=${encodeURIComponent(symbol)}`);
      
      if (!Array.isArray(response.data)) {
        console.error('Invalid response format for bought positions:', response.data);
        return [];
      }
      
      const positions = response.data;
      console.log(`Found ${positions.length} bought positions for ${symbol}`);
      return positions;
    } catch (error) {
      console.error(`Error fetching bought positions for ${symbol}:`, error);
      return [];
    }
  }
  
  /**
   * Creates a new merged trade record based on multiple positions
   * @param {Array<Object>} positions - Array of positions to merge
   * @param {Object} ibkrHolding - IBKR holding data for validation (optional)
   * @returns {Promise<Object>} Created merged trade record
   */
  async createMergedTrade(positions, ibkrHolding = null) {
    if (!positions || positions.length === 0) {
      console.error('No positions provided for merging');
      return null;
    }
    
    try {
      // Extract symbol from positions
      const symbol = positions[0].symbol;
      
      if (!symbol) {
        console.error('No symbol found in positions to merge');
        return null;
      }
      
      console.log(`Creating merged trade for ${symbol} with ${positions.length} positions`);
      
      // Use the dedicated merge endpoint in the backend
      const response = await axios.post('/api/orders/merge', {
        trades: positions,
        ibkrHolding: ibkrHolding,
        symbol: symbol
      });
      
      if (response.data && response.data.success) {
        const mergedTradeId = response.data.mergedTradeId;
        
        // Fetch the newly created merged trade
        try {
          const mergedTradeResponse = await axios.get(`/api/orders?symbol=${encodeURIComponent(symbol)}`);
          
          if (Array.isArray(mergedTradeResponse.data)) {
            const mergedTrade = mergedTradeResponse.data.find(t => 
              t.orderId === mergedTradeId || t._id === mergedTradeId
            );
            
            if (mergedTrade) {
              console.log(`Created merged trade with ID: ${mergedTradeId}`);
              return mergedTrade;
            }
          }
        } catch (fetchError) {
          console.error('Error fetching newly created merged trade:', fetchError);
        }
        
        // If fetch failed, return basic info from the response
        return {
          _id: mergedTradeId,
          mongoDbId: mergedTradeId,
          orderId: mergedTradeId,
          symbol: symbol,
          totalQuantity: response.data.combinedQuantity,
          entryPrice: response.data.entryPrice,
          positionValue: response.data.combinedValue,
          isMergedPosition: true,
          currentState: "bought"
        };
      } else {
        console.error('Failed to create merged trade:', response.data);
        return null;
      }
    } catch (error) {
      console.error('Error creating merged trade:', error);
      return null;
    }
  }
  
  /**
   * Updates original positions to mark them as merged
   * @param {Array<Object>} positions - Original positions to update
   * @param {string} mergedToId - ID of the merged position
   * @returns {Promise<Array>} Array of update results
   */
  async updatePositionsAsMerged(positions, mergedToId) {
    // Note: This function is now mostly handled by the backend merge endpoint
    // We keep it for compatibility but it will only be used in special cases
    if (!positions || positions.length === 0 || !mergedToId) {
      console.error('Missing required parameters for updating positions as merged');
      return [];
    }
    
    try {
      const updatePromises = positions.map(position => {
        const orderId = position.mongoDbId || position._id || position.orderId || position.tradeNoteId;
        if (!orderId) {
          console.error('No ID available for position update', position);
          return Promise.resolve({ success: false, message: 'No order ID available' });
        }
        
        // Prepare update data
        const updateData = {
          orderId: orderId,
          currentState: "merged", // Changed from "merge" to "merged" for clarity
          mergeToId: mergedToId,
          mergedAt: new Date().toISOString()
        };
        
        return axios.post(ORDER_ENDPOINTS.UPDATE_ORDER, { order: updateData })
          .then(response => {
            console.log(`Updated position ${position.symbol} (${orderId}) as merged`);
            return response.data;
          })
          .catch(error => {
            console.error(`Error updating position ${orderId} as merged:`, error);
            return { success: false, message: error.message || 'Error updating position' };
          });
      });
      
      const results = await Promise.all(updatePromises);
      console.log(`Updated ${results.filter(r => r.success).length} of ${positions.length} positions as merged`);
      return results;
    } catch (error) {
      console.error('Error updating positions as merged:', error);
      return [];
    }
  }
  
  /**
   * Processes a newly bought position to check for merge opportunities
   * @param {Object} newBoughtPosition - Newly bought position
   * @param {Object} ibkrHolding - IBKR holding data for validation (optional)
   * @returns {Promise<Object>} Result of merge operation
   */
  async processNewBoughtPosition(newBoughtPosition, ibkrHolding = null) {
    if (!newBoughtPosition || !newBoughtPosition.symbol) {
      console.error('Invalid position provided for merge processing');
      return { success: false, message: 'Invalid position' };
    }
    
    try {
      const symbol = newBoughtPosition.symbol;
      console.log(`Processing newly bought position for ${symbol} for potential merge`);
      
      // Step 1: Fetch all other bought positions for this symbol
      const existingPositions = await this.fetchBoughtPositionsForSymbol(symbol);
      
      // Filter out the current position if it's already in the list
      const otherPositions = existingPositions.filter(pos => {
        const posId = pos._id || pos.mongoDbId || pos.orderId || pos.tradeNoteId;
        const newPosId = newBoughtPosition._id || newBoughtPosition.mongoDbId || 
                        newBoughtPosition.orderId || newBoughtPosition.tradeNoteId;
        return posId !== newPosId;
      });
      
      if (otherPositions.length === 0) {
        console.log(`No existing bought positions found for ${symbol}, no merge needed`);
        return { success: true, merged: false, message: 'No merge needed' };
      }
      
      console.log(`Found ${otherPositions.length} existing positions for ${symbol}, initiating merge`);
      
      // Step 2: Merge all positions including the new position using the backend API
      // This handles both creating the merged position and updating originals in one call
      const allPositions = [...otherPositions, newBoughtPosition];
      const response = await axios.post('/api/orders/merge', {
        trades: allPositions,
        ibkrHolding: ibkrHolding,
        symbol: symbol
      });
      
      if (!response.data || !response.data.success) {
        console.error('Failed to merge positions:', response.data);
        return { 
          success: false, 
          merged: false, 
          message: response.data?.message || 'Failed to create merged position' 
        };
      }
      
      // Step 3: Return success result with merged position info from the API
      return {
        success: true,
        merged: true,
        message: response.data.message || `Successfully merged ${allPositions.length} positions for ${symbol}`,
        mergedPosition: {
          _id: response.data.mergedTradeId,
          mongoDbId: response.data.mergedTradeId,
          orderId: response.data.mergedTradeId,
          symbol: symbol,
          totalQuantity: response.data.combinedQuantity,
          entryPrice: response.data.entryPrice,
          positionValue: response.data.combinedValue,
          isMergedPosition: true,
          currentState: "bought"
        },
        originalPositions: allPositions.map(p => ({
          id: p._id || p.mongoDbId || p.orderId,
          symbol: p.symbol,
          quantity: p.totalQuantity || p.quantity || p.shares
        }))
      };
    } catch (error) {
      console.error(`Error processing position for merge:`, error);
      return { success: false, merged: false, message: error.message || 'Error processing merge' };
    }
  }
}

export default new TradeMerger(); 