/**
 * FastAPI Client
 * 
 * A direct API client for connecting to FastAPI backend without Parse
 */

import axios from 'axios';
import { AuthService } from '../services/auth.js';

// Configure axios to include auth headers for all requests
axios.interceptors.request.use(function (config) {
  const token = AuthService.token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, function (error) {
  return Promise.reject(error);
});

export const FastApiClient = {
  /**
   * Simple GET request to the API
   * @param {string} url - API endpoint URL
   * @param {Object} params - URL parameters
   * @returns {Promise<Object>} Response data
   */
  get: async (url, params = {}) => {
    try {
      const response = await axios.get(url, { params });
      return response;
    } catch (error) {
      console.error(`Error fetching from ${url}:`, error);
      throw error;
    }
  },

  /**
   * Simple POST request to the API
   * @param {string} url - API endpoint URL
   * @param {Object} data - POST body
   * @returns {Promise<Object>} Response data
   */
  post: async (url, data = {}) => {
    try {
      const response = await axios.post(url, data);
      return response;
    } catch (error) {
      console.error(`Error posting to ${url}:`, error);
      throw error;
    }
  },

  /**
   * Get existing trades by date
   * @param {number} limit - Maximum number of trades to retrieve
   * @returns {Promise<Array>} Array of trade date timestamps
   */
  getExistingTrades: async (limit = 50) => {
    try {
      // Use the main trades endpoint with filtering
      const today = Math.floor(Date.now() / 1000);
      const oneYearAgo = today - (365 * 24 * 60 * 60);
      
      // Use the standard trades endpoint instead of a specific existing endpoint
      const response = await axios.get(`/api/trades`, {
        params: {
          startDate: oneYearAgo,
          endDate: today,
          sort: 'dateUnix',
          sortDirection: 'desc',
          limit: limit
        }
      });
      
      // Extract unique dates from the trades
      const uniqueDates = [];
      const dateSet = new Set();
      
      if (response.data && Array.isArray(response.data)) {
        response.data.forEach(trade => {
          if (trade.dateUnix && !dateSet.has(trade.dateUnix)) {
            dateSet.add(trade.dateUnix);
            uniqueDates.push(trade.dateUnix);
          }
        });
      }
      
      return uniqueDates;
    } catch (error) {
      console.error('Error fetching existing trades:', error);
      throw error;
    }
  },

  /**
   * Upload trades to the server
   * @param {Object} tradesData - Trade data to upload
   * @returns {Promise<Object>} Response from server
   */
  uploadTrades: async (tradesData) => {
    try {
      console.log("Attempting to upload trades using trade_upload endpoint");
      // Use PUT method instead of POST, or a specific endpoint for uploading trades
      const response = await axios.put('/api/trades/upload', tradesData);
      return response.data;
    } catch (error) {
      // If the first attempt fails, try alternative endpoint and method
      try {
        console.log("First attempt failed, trying with trades_upload endpoint");
        const response = await axios.post('/api/trades_upload', tradesData);
        return response.data;
      } catch (secondError) {
        console.error('Error uploading trades (both attempts failed):', secondError);
        throw secondError;
      }
    }
  },

  /**
   * Update user profile
   * @param {Object} profileData - Profile data to update
   * @returns {Promise<Object>} Updated user profile
   */
  updateProfile: async (profileData) => {
    try {
      const response = await axios.post('/api/updateProfile', profileData);
      return response.data;
    } catch (error) {
      console.error('Error updating profile:', error);
      throw error;
    }
  },

  /**
   * Update open position
   * @param {string} tradeId - ID of the trade
   * @param {number} tradeDate - Unix timestamp of the trade date
   * @param {number} exitTime - Exit time of the position
   * @returns {Promise<Object>} Updated position data
   */
  updateOpenPosition: async (tradeId, tradeDate, exitTime) => {
    try {
      const response = await axios.post('/api/trades/position/update', {
        tradeId,
        tradeDate,
        exitTime
      });
      return response.data;
    } catch (error) {
      console.error('Error updating open position:', error);
      throw error;
    }
  },

  /**
   * Get current user
   * @returns {Promise<Object>} Current user data
   */
  getCurrentUser: async () => {
    try {
      const response = await axios.get('/api/user/current');
      return response.data;
    } catch (error) {
      console.error('Error fetching current user:', error);
      throw error;
    }
  }
};

export default FastApiClient; 