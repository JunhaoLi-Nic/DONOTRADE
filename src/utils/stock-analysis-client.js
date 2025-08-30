/**
 * Stock Analysis API Client
 * 
 * Client for interacting with the backend stock analysis tools
 */

import axios from 'axios';
import { AuthService } from '../services/auth.js';

export const StockAnalysisClient = {
  /**
   * Get ticker data from the API
   * @param {string} ticker - Stock ticker symbol
   * @param {string} startDate - Optional start date in YYYY-MM-DD format
   * @param {string} endDate - Optional end date in YYYY-MM-DD format
   * @returns {Promise<Object>} Ticker data
   */
  getTickerData: async (ticker, startDate = null, endDate = null) => {
    try {
      const params = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      
      const response = await axios.get(`/api/stock-analysis/ticker-data/${ticker}`, { params });
      return response.data;
    } catch (error) {
      console.error(`Error fetching ticker data for ${ticker}:`, error);
      throw error;
    }
  },

  /**
   * Get available tickers
   * @param {number} limit - Maximum number of tickers to retrieve
   * @returns {Promise<Array>} List of available tickers
   */
  getAvailableTickers: async (limit = 100) => {
    try {
      const response = await axios.get('/api/stock-analysis/tickers', { params: { limit } });
      return response.data;
    } catch (error) {
      console.error('Error fetching available tickers:', error);
      throw error;
    }
  },

  /**
   * Get ticker data in DataFrame format
   * @param {string} ticker - Stock ticker symbol
   * @param {string} startDate - Optional start date in YYYY-MM-DD format
   * @param {string} endDate - Optional end date in YYYY-MM-DD format
   * @returns {Promise<Object>} DataFrame-formatted ticker data
   */
  getTickerDataframe: async (ticker, startDate = null, endDate = null) => {
    try {
      const params = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      
      const response = await axios.get(`/api/stock-analysis/dataframe/${ticker}`, { params });
      return response.data;
    } catch (error) {
      console.error(`Error fetching dataframe for ${ticker}:`, error);
      throw error;
    }
  },

  /**
   * Get consecutive price movement analysis
   * @param {string} ticker - Stock ticker symbol
   * @param {string} direction - "up" or "down"
   * @param {number} minDays - Minimum consecutive days
   * @param {number} maxDays - Maximum consecutive days
   * @param {string} startDate - Optional start date in YYYY-MM-DD format
   * @param {string} endDate - Optional end date in YYYY-MM-DD format
   * @returns {Promise<Object>} Consecutive movement analysis
   */
  getConsecutiveAnalysis: async (ticker, direction = "down", minDays = 2, maxDays = 10, startDate = null, endDate = null) => {
    try {
      const params = {
        direction,
        min_days: minDays,
        max_days: maxDays
      };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      
      const response = await axios.get(`/api/stock-analysis/consecutive/${ticker}`, { params });
      return response.data;
    } catch (error) {
      console.error(`Error fetching consecutive analysis for ${ticker}:`, error);
      throw error;
    }
  },

  /**
   * Get Hurst exponent analysis
   * @param {string} ticker - Stock ticker symbol
   * @param {number} windowSize - Window size for rolling calculation
   * @param {number} step - Step size for rolling window
   * @param {string} startDate - Optional start date in YYYY-MM-DD format
   * @param {string} endDate - Optional end date in YYYY-MM-DD format
   * @returns {Promise<Object>} Hurst exponent analysis
   */
  getHurstExponent: async (ticker, windowSize = 252, step = 63, startDate = null, endDate = null) => {
    try {
      const params = {
        window_size: windowSize,
        step
      };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      
      const response = await axios.get(`/api/stock-analysis/hurst/${ticker}`, { params });
      return response.data;
    } catch (error) {
      console.error(`Error fetching Hurst exponent for ${ticker}:`, error);
      throw error;
    }
  },

  /**
   * Get volatility analysis
   * @param {string} ticker - Stock ticker symbol
   * @param {string} startDate - Optional start date in YYYY-MM-DD format
   * @param {string} endDate - Optional end date in YYYY-MM-DD format
   * @param {number} bandwidth - Bandwidth for KDE calculation (0.01-1.0)
   * @param {number} gridSize - Number of points in KDE grid (100-1000)
   * @returns {Promise<Object>} Volatility analysis
   */
  getVolatility: async (ticker, startDate = null, endDate = null, bandwidth = 0.15, gridSize = 500) => {
    try {
      console.log(`API call: getVolatility for ${ticker} from ${startDate || 'none'} to ${endDate || 'none'}`);
      
      const params = {
        bandwidth,
        grid_size: gridSize
      };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      
      console.log('API parameters:', params);
      
      const response = await axios.get(`/api/stock-analysis/volatility/${ticker}`, { params });
      
      // Log the number of data points received
      if (response.data && response.data.price_data) {
        console.log(`API response: ${response.data.price_data.dates.length} price points received`);
      }
      
      return response.data;
    } catch (error) {
      console.error(`Error fetching volatility for ${ticker}:`, error);
      throw error;
    }
  },

  /**
   * Get next day statistics
   * @param {string} ticker - Stock ticker symbol
   * @param {number} threshold - Price movement threshold
   * @param {number} lookAheadDays - Number of days to look ahead
   * @param {string} movement - "up", "down", or null for both
   * @param {string} startDate - Optional start date in YYYY-MM-DD format
   * @param {string} endDate - Optional end date in YYYY-MM-DD format
   * @returns {Promise<Object>} Next day statistics
   */
  getNextDayStats: async (ticker, threshold = 0.10, lookAheadDays = 10, movement = null, startDate = null, endDate = null) => {
    try {
      console.log(`API call: getNextDayStats for ${ticker}, threshold=${threshold}, lookAhead=${lookAheadDays}`);
      
      const params = {
        threshold,
        look_ahead_days: lookAheadDays,
        sync_yfinance: true // Always sync with yfinance to ensure we have the latest data
      };
      if (movement) params.movement = movement;
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      
      console.log('API parameters:', params);
      
      const response = await axios.get(`/api/stock-analysis/next-day-stats/${ticker}`, { params });
      
      // Log the response
      console.log(`Next-day stats response:`, response.data);
      
      return response.data;
    } catch (error) {
      console.error(`Error fetching next day stats for ${ticker}:`, error);
      throw error;
    }
  },

  /**
   * Get price distribution data
   * @param {string} ticker - Stock ticker symbol
   * @param {string} method - "hist", "kde", or "mc_kde"
   * @param {number} binSize - Bin size for histogram
   * @param {number} smoothWindow - Smoothing window size
   * @param {number} simulations - Number of simulations for Monte Carlo
   * @param {number} horizonDays - Horizon days for Monte Carlo
   * @param {string} startDate - Optional start date in YYYY-MM-DD format
   * @param {string} endDate - Optional end date in YYYY-MM-DD format
   * @param {number} bwMethod - Bandwidth for KDE (0.01-1.0)
   * @param {number} gridSize - Number of points in KDE grid (100-1000)
   * @returns {Promise<Object>} Price distribution data
   */
  getPriceDistribution: async (ticker, method = "kde", binSize = 5, smoothWindow = 3, 
                              simulations = 10000, horizonDays = 1, startDate = null, endDate = null,
                              bwMethod = 0.15, gridSize = 500) => {
    try {
      const params = {
        method,
        bin_size: binSize,
        smooth_window: smoothWindow,
        simulations,
        horizon_days: horizonDays,
        bw_method: bwMethod,
        grid_size: gridSize
      };
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      
      const response = await axios.get(`/api/stock-analysis/price-distribution/${ticker}`, { params });
      return response.data;
    } catch (error) {
      console.error(`Error fetching price distribution for ${ticker}:`, error);
      throw error;
    }
  },

  /**
   * Get current price for a ticker
   * @param {string} ticker - Stock ticker symbol
   * @returns {Promise<Object>} Current price data
   */
  getCurrentPrice: async (ticker) => {
    try {
      const response = await axios.get(`/api/stock-analysis/current-price/${ticker}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching current price for ${ticker}:`, error);
      throw error;
    }
  }
};

export default StockAnalysisClient; 