// timeZoneUtils.js - Utilities for handling timezone conversions in TradeNote

import { currentUser } from '../stores/globals';

/**
 * Get the user's configured timezone or default to New York
 * @returns {string} The timezone string to use
 */
export function getUserTimeZone() {
  const timeZone = currentUser?.value?.timeZone || 'America/New_York';
  const useDeviceTimeZone = currentUser?.value?.useDeviceTimeZone || false;
  return useDeviceTimeZone ? Intl.DateTimeFormat().resolvedOptions().timeZone : timeZone;
}

/**
 * Organize trades into day of week buckets based on the user's timezone
 * @param {Array} trades - Array of trade objects with entryTime property
 * @returns {Object} Object with day indices as keys and arrays of trades as values
 */
export function organizeTradesToDayBuckets(trades) {
  const dayBuckets = [[], [], [], [], [], [], []]; // Sunday to Saturday
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const userTimeZone = getUserTimeZone();

  if (!trades || trades.length === 0) return dayBuckets;

  trades.forEach(trade => {
    if (trade && trade.entryTime) {
      // Convert timestamp to Date object
      const tradeDate = new Date(trade.entryTime * 1000);
      
      // Get day of week in the user's timezone
      const options = { timeZone: userTimeZone, weekday: 'long' };
      const dayOfWeek = new Intl.DateTimeFormat('en-US', options).format(tradeDate);
      
      // Find the day index and add trade to the appropriate bucket
      const dayIndex = dayNames.indexOf(dayOfWeek);
      if (dayIndex !== -1) {
        dayBuckets[dayIndex].push(trade);
      }
    }
  });

  return dayBuckets;
}

/**
 * Get trades for a specific day of the week based on user's timezone
 * @param {string} dayName - The day name (Sunday through Saturday)
 * @param {Array} trades - Array of trades to filter
 * @returns {Array} Filtered trades that occur on the specified day
 */
export function getTradesForDay(dayName, trades) {
  const userTimeZone = getUserTimeZone();

  if (!trades || trades.length === 0) return [];

  return trades.filter(trade => {
    if (trade && trade.entryTime) {
      const tradeDate = new Date(trade.entryTime * 1000);
      const options = { timeZone: userTimeZone, weekday: 'long' };
      const tradeDayOfWeek = new Intl.DateTimeFormat('en-US', options).format(tradeDate);
      return tradeDayOfWeek === dayName;
    }
    return false;
  });
}

/**
 * Format a date object to a string in the user's timezone
 * @param {Date} date - The date to format
 * @param {Object} options - The formatting options
 * @returns {string} The formatted date string
 */
export function formatDateInUserTimeZone(date, options = {}) {
  if (!(date instanceof Date)) return '';
  
  const userTimeZone = getUserTimeZone();
  const defaultOptions = { 
    timeZone: userTimeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  };
  
  return date.toLocaleDateString('en-US', { ...defaultOptions, ...options });
}

/**
 * Format a time object to a string in the user's timezone
 * @param {Date} date - The date containing the time to format
 * @param {Object} options - The formatting options
 * @returns {string} The formatted time string
 */
export function formatTimeInUserTimeZone(date, options = {}) {
  if (!(date instanceof Date)) return '';
  
  const userTimeZone = getUserTimeZone();
  const defaultOptions = { 
    timeZone: userTimeZone,
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  };
  
  return date.toLocaleTimeString('en-US', { ...defaultOptions, ...options });
}

/**
 * Get the day counts for each day of the week based on user's timezone
 * @param {Array} filteredTrades - Filtered trades array from global store
 * @returns {Array} Array of trade counts for each day
 */
export function getDayCounts(filteredTrades) {
  let allTrades = [];
  
  // Flatten the trades array
  if (filteredTrades && filteredTrades.length > 0) {
    filteredTrades.forEach(day => {
      if (day && day.trades) {
        allTrades = [...allTrades, ...day.trades];
      }
    });
  }
  
  // Organize into day buckets
  const dayBuckets = organizeTradesToDayBuckets(allTrades);
  
  // Return counts
  return dayBuckets.map(bucket => bucket.length);
}

/**
 * Get the performance (P&L) for each day of the week based on user's timezone
 * @param {Array} filteredTrades - Filtered trades array from global store
 * @param {string} amountCase - The proceeds field prefix (e.g., 'gross', 'net')
 * @returns {Array} Array of P&L values for each day
 */
export function getDayPerformance(filteredTrades, amountCase) {
  let allTrades = [];
  
  // Flatten the trades array
  if (filteredTrades && filteredTrades.length > 0) {
    filteredTrades.forEach(day => {
      if (day && day.trades) {
        allTrades = [...allTrades, ...day.trades];
      }
    });
  }
  
  // Organize into day buckets
  const dayBuckets = organizeTradesToDayBuckets(allTrades);
  
  // Calculate performance for each day
  return dayBuckets.map(dayTrades => {
    let netProfit = 0;
    dayTrades.forEach(trade => {
      netProfit += trade[amountCase + 'Proceeds'] || 0;
    });
    return netProfit;
  });
} 