/**
 * API Analyzer
 * 
 * A utility to discover and test available API endpoints in the backend
 */

import axios from 'axios';
import { AuthService } from '../services/auth.js';

export const ApiAnalyzer = {
  /**
   * Discover available API endpoints by testing known patterns
   */
  discoverEndpoints: async () => {
    // Make sure we're authenticated
    if (!AuthService.token) {
      console.error('Authentication required to discover endpoints');
      return {
        success: false,
        error: 'Authentication required'
      };
    }

    const results = {
      success: true,
      workingEndpoints: [],
      failedEndpoints: []
    };

    // Common endpoint patterns to test
    const endpointPatterns = [
      // GET endpoints
      { method: 'get', url: '/api/trades' },
      { method: 'get', url: '/api/user/current' },
      { method: 'get', url: '/api/user/me' },
      
      // POST/PUT endpoints for trades
      { method: 'post', url: '/api/trades' },
      { method: 'post', url: '/api/trades/upload' },
      { method: 'put', url: '/api/trades' },
      { method: 'put', url: '/api/trades/upload' }
    ];

    // Test each endpoint
    for (const endpoint of endpointPatterns) {
      try {
        console.log(`Testing ${endpoint.method.toUpperCase()} ${endpoint.url}...`);
        
        // For GET requests, we can just make the request
        if (endpoint.method === 'get') {
          const response = await axios[endpoint.method](endpoint.url);
          results.workingEndpoints.push({
            ...endpoint,
            status: response.status,
            message: 'Success',
            dataType: Array.isArray(response.data) ? 'array' : typeof response.data
          });
        } 
        // For POST/PUT, we need to send some minimal test data
        else {
          // Create minimal valid test data to avoid actually modifying anything
          const testData = { test: true, _testOnly: true };
          
          try {
            const response = await axios[endpoint.method](endpoint.url, testData);
            results.workingEndpoints.push({
              ...endpoint,
              status: response.status,
              message: 'Success',
              dataType: Array.isArray(response.data) ? 'array' : typeof response.data
            });
          } catch (error) {
            // Check if it's just rejecting our test data (which is expected)
            // but accepting the endpoint itself
            if (error.response && (error.response.status === 400 || error.response.status === 422)) {
              results.workingEndpoints.push({
                ...endpoint,
                status: error.response.status,
                message: 'Endpoint exists but rejected test data (expected)',
                dataType: 'unknown'
              });
            } else {
              throw error; // Re-throw to be caught by the outer catch
            }
          }
        }
      } catch (error) {
        results.failedEndpoints.push({
          ...endpoint,
          status: error.response?.status || 'unknown',
          message: error.response?.statusText || error.message
        });
      }
    }

    console.log('API Discovery Results:', results);
    return results;
  }
};

export default ApiAnalyzer; 