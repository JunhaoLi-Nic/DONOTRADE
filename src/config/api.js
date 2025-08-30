// API Configuration

// Base URL for API requests
export const API_BASE_URL = 'http://localhost:3002';

// API Prefix for backend routes
export const API_PREFIX = '/backend';

// Default headers for API requests
export const API_HEADERS = {
  'Content-Type': 'application/json'
};

// Configure Axios defaults
import axios from 'axios';

// Set base URL for all requests
axios.defaults.baseURL = API_BASE_URL;

// Set default headers
axios.defaults.headers.common = {
  ...axios.defaults.headers.common,
  ...API_HEADERS
};

// Add request interceptor for debugging
axios.interceptors.request.use((config) => {
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data);
  return config;
}, (error) => {
  console.error('API Request Error:', error);
  return Promise.reject(error);
});

// Add response interceptor for debugging
axios.interceptors.response.use((response) => {
  console.log(`API Response: ${response.status} ${response.config.url}`, response.data);
  return response;
}, (error) => {
  console.error('API Response Error:', error);
  return Promise.reject(error);
});

export default axios;

// IBKR API endpoints - use paths that match our backend routes
export const IBKR_ENDPOINTS = {
  POSITIONS: `/api/ibkr/positions`,
  OPEN_ORDERS: `/api/ibkr/open-orders`
};

// Order API endpoints
export const ORDER_ENDPOINTS = {
  ORDERS: `/api/orders`,
  EXECUTED_ORDERS: `/api/executed-orders`,
  UPDATE_ORDER: `/api/orders/update`,
  MERGE_TRADES: `/api/orders/merge`
}; 