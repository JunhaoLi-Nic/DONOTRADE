/**
 * Direct Trade Upload
 * 
 * A simplified approach to upload trade data directly to FastAPI
 */

import axios from 'axios';
import { AuthService } from '../services/auth.js';

// Make sure we have authorization headers
const getAxiosConfig = () => {
  const token = AuthService.token;
  return {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  };
};

export const DirectUpload = {
  /**
   * Upload trade data directly to the API
   * @param {Object} tradeData - The trade data to upload
   * @returns {Promise<Object>} - Response from the server
   */
  uploadTrade: async (tradeData) => {
    console.log("DirectUpload: Attempting to upload trade data");
    
    // We'll log to console but not show intrusive popups
    const logStatus = (message, isError = false) => {
      if (isError) {
        console.warn(message);
      } else {
        console.log(message);
      }
    };
    
    // Check if we already have a known working endpoint from previous uploads
    const savedEndpoint = localStorage.getItem('working_endpoint');
    if (savedEndpoint) {
      logStatus(`Using previously successful endpoint: ${savedEndpoint}`);
    }
    
    // Ensure data is in a format the API expects and never include a test flag
    const payload = {
      ...tradeData,
      // Add user_id if not present (may be required by API)
      user_id: localStorage.getItem('user_id') || AuthService.getCurrentUser()?.id
    };
    
    // Explicitly ensure we're not sending test data
    delete payload.test;
    
    try {
      // First, try to determine what endpoints are available by checking the API
      logStatus("Checking available API endpoints...");
      
      let apiAvailable = false;
      
      try {
        // Try GET /api/trades first to see if the API is responsive
        const testResponse = await axios.get('/api/trades', {
          params: { limit: 1 },
          ...getAxiosConfig()
        });
        
        apiAvailable = testResponse.status === 200;
        logStatus(`API is responsive to GET requests. Status: ${testResponse.status}`);
      } catch (testError) {
        logStatus(`API test failed: ${testError.message}`, true);
        throw new Error('API is not available. Please try again later.');
      }
      
      if (apiAvailable) {
        // Try the dedicated endpoints for trade creation
        const endpoints = [
          { method: 'post', url: '/api/trades/bulk', dataTransform: data => ({ trades: [data] }) },
          { method: 'post', url: '/api/trades/single' },
          { method: 'post', url: '/api/trades' }  // Original endpoint as last resort
        ];
        
        // If we have a saved endpoint, try it first
        if (savedEndpoint) {
          const [method, url] = savedEndpoint.split('|');
          endpoints.unshift({ method, url });
        }
        
        // Try each endpoint
        for (const endpoint of endpoints) {
          try {
            logStatus(`Trying endpoint: ${endpoint.method.toUpperCase()} ${endpoint.url}...`);
            
            // For bulk endpoint, ensure there's data to send
            if (endpoint.url.includes('/bulk')) {
              if (!payload || Object.keys(payload).length === 0) {
                logStatus(`Skipping bulk endpoint due to empty payload.`, true);
                continue; // Skip to the next endpoint
              }
            }
            
            // Transform data if needed
            const endpointData = endpoint.dataTransform ? 
              endpoint.dataTransform(payload) : payload;
            
            const response = await axios[endpoint.method](
              endpoint.url, 
              endpointData,
              getAxiosConfig()
            );
            
            logStatus(`✅ Success! ${endpoint.method.toUpperCase()} ${endpoint.url} responded with status ${response.status}`);
            
            // Save the working endpoint for future use
            localStorage.setItem('working_endpoint', `${endpoint.method}|${endpoint.url}`);
            
            return {
              success: true,
              id: response.data?.trade_id || response.data?.trade_ids?.[0] || null,
              source: 'server',
              message: 'Trade data uploaded to server'
            };
          } catch (error) {
            logStatus(`⚠️ Endpoint failed: ${error.message}`, true);
          }
        }
      }
      
      throw new Error('Failed to upload trade data after trying all endpoints');
    } catch (error) {
      logStatus(`❌ Upload failed: ${error.message}`, true);
      throw error;
    }
  },
  
  /**
   * Get trades from local storage
   * @returns {Array} Empty array as local storage is disabled
   */
  getLocalTrades: () => {
    return [];
  }
}; 