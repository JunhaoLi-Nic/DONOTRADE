import axios from 'axios';
import AuthService from './auth';

/**
 * Service for handling trade-related API calls and data processing
 */
class TradeService {
  /**
   * Get trades with optional filters
   * @param {Object} options - Options for trade retrieval
   * @param {number} [options.limit=1000] - Maximum number of trades to fetch
   * @param {Object} [options.filters] - Additional filters for trades
   * @returns {Promise<Array<Object>>} - Processed trade data
   */
  static async getTrades(options = {}) {
    try {
      // Get auth headers
      const headers = AuthService.getAuthHeaders();
      
      // Set up parameters for API call
      const params = {
        limit: options.limit || 1000,
        ...options.filters
      };
      
      // Make API call
      const response = await axios.get('/api/trades', { params, headers });
      
      if (response.data && Array.isArray(response.data)) {
        // Process trade data
        return this.processTradeData(response.data);
      }
      
      // Return empty array if no data
      return [];
    } catch (error) {
      console.error('Error fetching trades:', error);
      // Return mock data in case of error for development
      return options.useMockData ? this.getMockTradeData() : [];
    }
  }

  /**
   * Process raw trade data from API into consistent format
   * @param {Array<Object>} trades - Raw trade data from API
   * @returns {Array<Object>} - Processed trades with consistent properties
   */
  static processTradeData(trades) {
    if (!Array.isArray(trades)) return [];
    
    return trades.map(trade => {
      // Calculate net P&L based on available data
      const calculatedNetPnL = this.calculateTradeProfit(trade);
      
      // Calculate ROI if not present
      let calculatedROI = trade.roi;
      if (!calculatedROI && calculatedNetPnL && trade.entryPrice && trade.quantity) {
        const investment = trade.entryPrice * (trade.quantity || 100);
        if (investment !== 0) {
          calculatedROI = (calculatedNetPnL / investment) * 100;
        }
      }
      
      // Determine trade status based on P&L if not present
      let tradeStatus = trade.status;
      if (!tradeStatus) {
        if (calculatedNetPnL > 0) tradeStatus = 'WIN';
        else if (calculatedNetPnL < 0) tradeStatus = 'LOSS';
        else tradeStatus = 'EVEN';
      }
      
      // Map API trade data to our display format with consistent properties
      return {
        id:  trade.id,
        openDate:trade.entryTime,
        symbol: trade.symbol,
        status: tradeStatus,
        closeDate: trade.exitTime,
        entryPrice: trade.entryPrice || trade.entry,
        exitPrice: trade.exitPrice || trade.exit,
        quantity: trade.quantity || (trade.buyQuantity + trade.sellQuantity) || 100,
        netPnL: calculatedNetPnL,
        netROI: calculatedROI || 0,
        side: trade.side || trade.strategy || 'long',
        setups: trade.setups || '',
        accountName: trade.account || 'Default',
        buyQuantity: trade.buyQuantity,
        sellQuantity: trade.sellQuantity,
        commission: trade.commission,
        fees: trade.fees,
        tags: trade.tags || []
      };
    });
  }

  /**
   * Calculate profit/loss for a trade
   * @param {Object} trade - Trade object
   * @returns {number} - Calculated profit/loss
   */
  static calculateTradeProfit(trade) {
    // This follows the same calculation as in the daily view
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
   * Get mock trade data for development/testing
   * @returns {Array<Object>} - Mock trade data
   */
  static getMockTradeData() {
    return [
      {
        id: 1,
        openDate: '12/19/2022',
        symbol: 'SPY',
        status: 'WIN',
        closeDate: '12/19/2022',
        entryPrice: 391.12,
        exitPrice: 391.74,
        netPnL: 28359.45,
        netROI: 50.64,
        setups: 'morning top reversal',
        accountName: 'Umar2022 UAT',
        tags: ['tag_1', 'tag_3']
      },
      {
        id: 2,
        openDate: '12/01/2022',
        symbol: 'SPY',
        status: 'WIN',
        closeDate: '12/01/2022',
        entryPrice: 391.07,
        exitPrice: 392.77,
        netPnL: 77471.72,
        netROI: 109.16,
        setups: 'morning top reversal',
        accountName: 'Umar2022 UAT',
        tags: ['tag_2', 'tag_4']
      },
      {
        id: 3,
        openDate: '12/01/2022',
        symbol: 'SPY',
        status: 'LOSS',
        closeDate: '12/01/2022',
        entryPrice: 391.26,
        exitPrice: 390.84,
        netPnL: -17122.44,
        netROI: -33.89,
        setups: 'morning top reversal',
        accountName: 'Umar2022 UAT',
        tags: ['tag_1', 'tag_5']
      },
      {
        id: 4,
        openDate: '11/14/2022',
        symbol: 'SPY',
        status: 'LOSS',
        closeDate: '11/14/2022',
        entryPrice: 391.33,
        exitPrice: 391.10,
        netPnL: -711.76,
        netROI: -17.84,
        setups: 'high of the day',
        accountName: 'Umar2022 UAT',
        tags: ['tag_3', 'tag_6']
      },
      {
        id: 5,
        openDate: '06/13/2023',
        symbol: 'AAPL',
        status: 'LOSS',
        closeDate: '06/13/2023',
        entryPrice: 180.50,
        exitPrice: 179.25,
        netPnL: -79.13,
        netROI: -0.7,
        setups: 'gap fill',
        accountName: 'Demo Account',
        tags: ['random-test']
      }
    ];
  }

  /**
   * Extracts tags from trades based on trade IDs
   * @param {Array<Object>} trades - Trade objects
   * @param {Array<Object>} tagEntries - Tag entries from global tags store
   * @returns {Array<Object>} - Trades with tag arrays added
   */
  static matchTradeTagsFromGlobal(trades, tagEntries) {
    if (!Array.isArray(trades) || !Array.isArray(tagEntries)) return trades;
    
    return trades.map(trade => {
      // Start with existing tags or empty array
      let tradeTags = trade.tags || [];
      
      // Use trade.id directly from backend data
      const tradeId = trade.id;
      
      if (tradeId) {
        // Find tags for this trade by ID
        const tagEntry = tagEntries.find(tag => tag.tradeId === tradeId);
        if (tagEntry && Array.isArray(tagEntry.tags)) {
          tradeTags = tagEntry.tags;
          console.log(`Found tags for trade ${trade.symbol} using ID: ${tradeId}`);
        }
      }
      
      // Log trade tags for debugging
      if (tradeTags.length > 0 && trade.symbol) {
        console.log(`Tags for trade ${trade.symbol}: ${tradeTags.join(', ')}`);
      }
      
      // Return trade with updated tags
      return {
        ...trade,
        tags: tradeTags
      };
    });
  }
}

export default TradeService;