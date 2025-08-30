import axios from 'axios';
import AuthService from './auth';
import { extractNameFromPlaybook } from '../utils/playbooks';
import { mapTagIdsToFullTags } from '../utils/tagUtils';

/**
 * Service for handling playbook-related API calls and data processing
 */
class PlaybookService {
  /**
   * Get a playbook by ID
   * @param {string} playbookId - The ID of the playbook to fetch
   * @returns {Promise<Object>} - Playbook data
   */
  static async getPlaybook(playbookId) {
    try {
      const headers = AuthService.getAuthHeaders();
      const response = await axios.get(`/api/playbooks/${playbookId}`, { headers });
      
      if (response.data) {
        // Extract name from playbook content if available
        return {
          ...response.data,
          name: extractNameFromPlaybook(response.data.playbook),
          stats: {
            netPnL: 0,
            winRate: 0,
            tradesCount: 0,
            profitFactor: 0,
            totalWins: 0,
            totalLosses: 0,
            avgWin: 0,
            avgLoss: 0,
            biggestWin: 0,
            biggestLoss: 0
          },
          tagFilterActive: false
        };
      }
      
      throw new Error('No playbook data returned from API');
    } catch (error) {
      console.error('Error fetching playbook:', error);
      throw error;
    }
  }

  /**
   * Get tags associated with a playbook
   * @param {string} playbookId - The playbook ID
   * @param {Array<Object>} globalAvailableTags - All available tags in the system
   * @returns {Promise<Array<Object>>} - Tags associated with the playbook
   */
  static async getPlaybookTags(playbookId, globalAvailableTags) {
    try {
      const headers = AuthService.getAuthHeaders();
      const response = await axios.get(`/api/playbook/${playbookId}/tags`, { headers });
      
      if (response.data && response.data.tags) {
        // Convert tag IDs to full tag objects using the utility function
        return mapTagIdsToFullTags(response.data.tags, globalAvailableTags);
      }
      
      return [];
    } catch (error) {
      console.error('Error fetching playbook tags:', error);
      return [];
    }
  }

  /**
   * Save tags for a specific playbook
   * @param {string} playbookId - The playbook ID
   * @param {Array<Object>} tags - Tags to save
   * @returns {Promise<Object>} - API response
   */
  static async savePlaybookTags(playbookId, tags) {
    try {
      const headers = AuthService.getAuthHeaders();
      const tagIds = tags.map(tag => tag.id);
      
      const response = await axios.post('/api/playbook/tags', {
        playbookId,
        tags: tagIds
      }, { headers });
      
      return response.data;
    } catch (error) {
      console.error('Error saving playbook tags:', error);
      throw error;
    }
  }

  /**
   * Calculate statistics for trades in a playbook
   * @param {Array<Object>} trades - Array of trades to calculate stats for
   * @param {Function} calculateTradeProfitFn - Function to calculate profit for a trade
   * @returns {Object} - Statistics object for the playbook
   */
  static calculatePlaybookStats(trades, calculateTradeProfitFn) {
    if (!trades || trades.length === 0) {
      return {
        netPnL: 0,
        winRate: 0,
        tradesCount: 0,
        profitFactor: 0,
        totalWins: 0,
        totalLosses: 0,
        avgWin: 0,
        avgLoss: 0,
        biggestWin: 0,
        biggestLoss: 0
      };
    }
    
    // Initialize stats variables
    let netPnL = 0;
    let wins = 0;
    let losses = 0;
    let totalWinAmount = 0;
    let totalLossAmount = 0;
    let biggestWin = 0;
    let biggestLoss = 0;
    
    // Calculate stats from trades using the provided calculation function
    trades.forEach(trade => {
      const pnl = calculateTradeProfitFn ? calculateTradeProfitFn(trade) : this.calculateTradeProfit(trade);
      netPnL += pnl;
      
      if (pnl > 0) {
        wins++;
        totalWinAmount += pnl;
        if (pnl > biggestWin) biggestWin = pnl;
      } else if (pnl < 0) {
        losses++;
        totalLossAmount += pnl;
        if (pnl < biggestLoss) biggestLoss = pnl;
      }
    });
    
    // Calculate derived stats
    const tradesCount = trades.length;
    const winRate = tradesCount > 0 ? (wins / tradesCount) * 100 : 0;
    const profitFactor = totalLossAmount !== 0 ? Math.abs(totalWinAmount / totalLossAmount) : totalWinAmount > 0 ? Infinity : 0;
    const avgWin = wins > 0 ? totalWinAmount / wins : 0;
    const avgLoss = losses > 0 ? totalLossAmount / losses : 0;
    
    // Return calculated stats
    return {
      netPnL,
      winRate,
      tradesCount,
      profitFactor,
      totalWins: totalWinAmount,
      totalLosses: totalLossAmount,
      avgWin,
      avgLoss,
      biggestWin,
      biggestLoss
    };
  }

  /**
   * Update statistics for a playbook based on trades
   * @param {Object} playbook - Playbook object to update
   * @param {Array<Object>} trades - Trades to base statistics on
   * @returns {Object} - Updated playbook object with statistics
   */
  static updatePlaybookStats(playbook, trades) {
    if (!trades || trades.length === 0) {
      // Set default stats if no trades
      playbook.stats = {
        netPnL: 0,
        winRate: 0,
        tradesCount: 0,
        profitFactor: 0,
        totalWins: 0,
        totalLosses: 0,
        avgWin: 0,
        avgLoss: 0,
        biggestWin: 0,
        biggestLoss: 0
      };
      return playbook;
    }
    
    // Initialize stats variables
    let netPnL = 0;
    let wins = 0;
    let losses = 0;
    let totalWinAmount = 0;
    let totalLossAmount = 0;
    let biggestWin = 0;
    let biggestLoss = 0;
    
    // Calculate stats from trades
    trades.forEach(trade => {
      const pnl = this.calculateTradeProfit(trade);
      netPnL += pnl;
      
      if (pnl > 0) {
        wins++;
        totalWinAmount += pnl;
        if (pnl > biggestWin) biggestWin = pnl;
      } else if (pnl < 0) {
        losses++;
        totalLossAmount += pnl;
        if (pnl < biggestLoss) biggestLoss = pnl;
      }
    });
    
    // Calculate derived stats
    const tradesCount = trades.length;
    const winRate = tradesCount > 0 ? (wins / tradesCount) * 100 : 0;
    const profitFactor = totalLossAmount !== 0 ? Math.abs(totalWinAmount / totalLossAmount) : totalWinAmount > 0 ? Infinity : 0;
    const avgWin = wins > 0 ? totalWinAmount / wins : 0;
    const avgLoss = losses > 0 ? totalLossAmount / losses : 0;
    
    // Update playbook stats object
    playbook.stats = {
      netPnL,
      winRate,
      tradesCount,
      profitFactor,
      totalWins: totalWinAmount,
      totalLosses: totalLossAmount,
      avgWin,
      avgLoss,
      biggestWin,
      biggestLoss
    };
    
    return playbook;
  }
  
  /**
   * Calculate profit/loss for a trade
   * Utility function for statistical calculations
   * @param {Object} trade - Trade object
   * @returns {number} - Calculated profit/loss
   */
  static calculateTradeProfit(trade) {
    // This follows the same calculation as in TradeService
    if (!trade) return 0;
    
    // First check for existing profit/PnL values
    if (trade.netPnL && trade.netPnL !== 0) {
      return trade.netPnL;
    }
    
    if (trade.profit && trade.profit !== 0) {
      return trade.profit;
    }
    
    // If trade has buy/sell info, calculate using that approach
    if (trade.buyQuantity !== undefined && trade.sellQuantity !== undefined) {
      return trade.netProceeds || 0;
    }
    
    // If we need to calculate it from scratch:
    if (trade.entryPrice && trade.exitPrice) {
      // Default quantity to 100 shares if not specified
      const quantity = trade.quantity || 100;
      
      // Determine if it's a long or short trade based on available info
      const isLong = trade.side ? trade.side.toLowerCase() === 'long' : 
                    (trade.status === 'WIN' ? trade.exitPrice > trade.entryPrice : 
                                            trade.exitPrice < trade.entryPrice);
                                            
      let profit = 0;
      
      if (isLong) {
        profit = (trade.exitPrice - trade.entryPrice) * quantity;
      } else {
        profit = (trade.entryPrice - trade.exitPrice) * quantity;
      }
      
      // Subtract fees if available
      if (trade.commission) profit -= trade.commission;
      if (trade.fees) profit -= trade.fees;
      if (trade.locateFees) profit -= trade.locateFees;
      
      return profit;
    }
    
    // If all else fails, try to infer from trade status
    if (trade.status) {
      const defaultValue = trade.status.toUpperCase() === 'WIN' ? 100 : 
                          trade.status.toUpperCase() === 'LOSS' ? -100 : 0;
      return defaultValue;
    }
    
    return 0;
  }

  /**
   * Filter trades by tags
   * @param {Array<Object>} allTrades - All available trades
   * @param {Array<Object>} selectedTags - Tags to filter by
   * @returns {Array<Object>} - Filtered trades
   */
  static filterTradesByTags(allTrades, selectedTags) {
    if (!selectedTags || selectedTags.length === 0) {
      // If no tags selected, show all trades
      return [...allTrades];
    }
    
    // Get the IDs of the selected tags
    const selectedTagIds = selectedTags.map(tag => tag.id);
    
    // Filter trades that have AT LEAST ONE of the selected tags
    // This implements an OR filter logic (any trade with any selected tag is shown)
    return allTrades.filter(trade => {
      // If the trade has no tags array or it's empty, it can't match
      if (!trade.tags || !Array.isArray(trade.tags) || trade.tags.length === 0) return false;
      
      // Check if any of the trade's tags match the selected tags
      return trade.tags.some(tagId => selectedTagIds.includes(tagId));
    });
  }
}

export default PlaybookService;