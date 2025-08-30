import axios from '../config/api';

/**
 * Service for fetching and managing stock price data
 */
class PriceService {
  constructor() {
    // Track last price fetch time to prevent excessive API calls
    this.lastPriceFetchTime = 0;
    this.MIN_PRICE_FETCH_INTERVAL = 10000; // Minimum 10 seconds between price fetches
    this.isLoading = false;
  }

  /**
   * Fetch current prices for a list of symbols
   * @param {Array} symbols - Array of stock symbols to fetch prices for
   * @param {boolean} refresh - Force refresh from broker API instead of cache
   * @param {function} onSuccess - Optional callback for success
   * @param {function} onError - Optional callback for errors
   * @returns {Promise<Object>} - Object with symbols as keys and prices as values
   */
  async fetchCurrentPrices(symbols, refresh = false, onSuccess = null, onError = null) {
    // Skip if no symbols provided
    if (!symbols || symbols.length === 0) {
      return {};
    }
    
    // Don't fetch if already loading
    if (this.isLoading) {
      console.log('Price fetch already in progress, skipping');
      return {};
    }
    
    // Rate limiting - prevent excessive API calls
    const now = Date.now();
    if (!refresh && now - this.lastPriceFetchTime < this.MIN_PRICE_FETCH_INTERVAL) {
      console.log(`Skipping price fetch - last fetch was ${now - this.lastPriceFetchTime}ms ago`);
      return {};
    }
    
    this.isLoading = true;
    this.lastPriceFetchTime = now;
    
    try {
      // Add cache-busting parameter only when explicitly refreshing
      const timestamp = refresh ? `&_t=${new Date().getTime()}` : '';
      // When refresh is true, add additional parameters to force backend to ignore cache
      const forceRefresh = refresh ? '&force_refresh=true' : '';
      
      const response = await axios.get(
        `/api/ibkr/prices?symbols=${symbols.join(',')}&refresh=${refresh}${timestamp}${forceRefresh}`
      );
      
      // Call success callback if provided
      if (onSuccess && typeof onSuccess === 'function') {
        onSuccess(response.data);
      }
      
      return response.data;
    } catch (error) {
      console.error('Error fetching current prices:', error);
      
      // Call error callback if provided
      if (onError && typeof onError === 'function') {
        onError(error);
      }
      
      return {};
    } finally {
      this.isLoading = false;
    }
  }
  
  /**
   * Check if we should fetch prices based on time since last fetch
   * @returns {boolean} - True if enough time has passed since last fetch
   */
  shouldFetchPrices() {
    const now = Date.now();
    return now - this.lastPriceFetchTime >= this.MIN_PRICE_FETCH_INTERVAL;
  }
  
  /**
   * Reset the last fetch time to force a new fetch on next request
   */
  resetFetchTimer() {
    this.lastPriceFetchTime = 0;
  }
}

// Create singleton instance
const priceService = new PriceService();

export default priceService; 