/**
 * Stock Data Service
 * 
 * Provides functions to fetch US stock tickers from backend API
 */

import { FastApiClient } from '../utils/fastapi-client';

/**
 * Get all available stock tickers from the backend
 * @returns {Promise<Array>} Array of stock objects with symbol and name properties
 */
export const getStocks = async () => {
  try {
    // Fetch tickers from the backend API
    const response = await FastApiClient.get('/api/stocks/tickers');
    
    if (response && response.data) {
      // Transform response into objects with symbol and name
      return response.data.map(ticker => ({
        symbol: ticker
      }));
    }
    
    return [];
  } catch (error) {
    console.error('Error fetching stock tickers from API:', error);
    return getFallbackStocks();
  }
};

/**
 * Search for stocks by symbol
 * @param {String} query - Search query string
 * @param {Array} stocks - Array of stock objects to search through
 * @returns {Array} Filtered array of stock objects
 */
export const searchStocks = (query, stocks) => {
  if (!query || !stocks?.length) return stocks || [];
  
  const lowerQuery = query.toLowerCase();
  return stocks.filter(stock => 
    stock.symbol.toLowerCase().includes(lowerQuery) || 
    (stock.name && stock.name.toLowerCase().includes(lowerQuery))
  );
};

/**
 * Get a fallback list of common stocks in case the API fails
 * @returns {Array} Array of stock objects with symbol and name properties
 */
const getFallbackStocks = () => {
  // Small set of common stocks as a fallback
  return [
    { symbol: 'AAPL', name: 'Apple Inc.' },
    { symbol: 'MSFT', name: 'Microsoft Corporation' },
    { symbol: 'GOOGL', name: 'Alphabet Inc.' },
    { symbol: 'AMZN', name: 'Amazon.com Inc.' },
    { symbol: 'META', name: 'Meta Platforms Inc.' },
    { symbol: 'TSLA', name: 'Tesla, Inc.' },
    { symbol: 'NVDA', name: 'NVIDIA Corporation' },
    { symbol: 'JPM', name: 'JPMorgan Chase & Co.' },
    { symbol: 'V', name: 'Visa Inc.' },
    { symbol: 'JNJ', name: 'Johnson & Johnson' }
  ];
};

/**
 * Get correlation matrix for a list of tickers and lookback period
 * @param {Array<string>} tickers - Array of ticker symbols
 * @param {number} lookbackDays - Number of days to look back
 * @returns {Promise<{matrix: number[][], tickers: string[]}>}
 */
export const getCorrelationMatrix = async (tickers, lookbackDays) => {
  try {
    // Use the correct backend path and request body keys
    const response = await FastApiClient.post('/api/stock-analysis/stocks/correlation-matrix', {
      tickers,
      lookback_days: lookbackDays // must use underscore
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching correlation matrix:', error);
    throw error;
  }
};

export default {
  getStocks,
  searchStocks,
  getCorrelationMatrix
}; 