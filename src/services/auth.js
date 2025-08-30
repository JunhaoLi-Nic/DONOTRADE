import axios from 'axios';
import { jwtDecode } from 'jwt-decode';

// Constants
const TOKEN_KEY = 'auth_token';
const USER_KEY = 'current_user';

// Create axios instance with auth header support
const api = axios.create({
  baseURL: '/api'
});

// Add auth token to requests
api.interceptors.request.use(config => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    // Check if token is expired
    try {
      const decoded = jwtDecode(token);
      const currentTime = Date.now() / 1000;
      
      if (decoded.exp && decoded.exp < currentTime) {
        console.warn("Token expired, but continuing with request");
        // Don't automatically redirect - this might be causing the freeze
        // Just add the token anyway and let the server handle the rejection properly
        config.headers.Authorization = `Bearer ${token}`;
      } else {
        config.headers.Authorization = `Bearer ${token}`;
        
        // Also update global axios for other components
        if (!axios.defaults.headers.common['Authorization']) {
          axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        }
      }
    } catch (e) {
      // If token can't be decoded, still use it (might be a session token)
      config.headers.Authorization = `Bearer ${token}`;
      
      // Also update global axios for other components
      if (!axios.defaults.headers.common['Authorization']) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      }
    }
  }
  
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`, config.data || {});
  return config;
});

// Add response logging
api.interceptors.response.use(
  response => {
    return response;
  },
  error => {
    console.error(`API Error (${error.response?.status || 'Network Error'}):`, error.config?.url);
    
    // Handle auth errors (try to refresh if token expired)
    if (error.response?.status === 401) {
      console.warn("401 Unauthorized response received - token may be invalid");
      // Will be handled in the specific auth methods
    }
    
    return Promise.reject(error);
  }
);

// Authentication methods
export const AuthService = {
  // Token property to access token directly
  get token() {
    return localStorage.getItem(TOKEN_KEY);
  },

  // Get auth headers for API requests
  getAuthHeaders() {
    const token = localStorage.getItem(TOKEN_KEY);
    
    if (!token) {
      console.warn("Auth token is missing when trying to make an API request");
      
      // Attempt to debug and fix auth issues
      AuthService.debug();
      
      // If we're in development, provide a way to recover
      if (window.location.hostname === 'localhost') {
        console.info("You may need to log out and log back in. Run AuthService.logout() in the console.");
      }
      
      return {};
    }
    
    // Check if token is expired
    if (AuthService.isTokenExpired()) {
      console.warn("Token is expired when trying to get auth headers");
      // Still return the token, let the server decide what to do
    }
    
    // Force update global axios headers too
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    
    return { Authorization: `Bearer ${token}` };
  },

  // Check if token is expired
  isTokenExpired() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return true;
    
    try {
      const decoded = jwtDecode(token);
      const currentTime = Date.now() / 1000;
      
      // Check if exp exists and token is expired
      if (decoded.exp && decoded.exp < currentTime) {
        console.warn("Token is expired");
        return true;
      }
      
      return false;
    } catch (e) {
      // If we can't decode, assume it's a session token and not expired
      return false;
    }
  },

  // Debug function to help troubleshoot auth issues
  debug: () => {
    const token = localStorage.getItem(TOKEN_KEY);
    const user = localStorage.getItem(USER_KEY);
    const hasAxiosAuth = !!axios.defaults.headers.common['Authorization'];
    const isExpired = AuthService.isTokenExpired();
    
    console.log("Auth Debug Info:");
    console.log("- Token exists:", !!token);
    console.log("- Token length:", token?.length || 0);
    console.log("- Token expired:", isExpired);
    console.log("- User data exists:", !!user);
    console.log("- Global axios auth header set:", hasAxiosAuth);
    
    // Fix headers if token exists but header doesn't
    if (token && !hasAxiosAuth && !isExpired) {
      console.log("- Fixing missing axios auth header");
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    }
    
    // Try to refresh token if expired
    if (isExpired) {
      console.log("- Token is expired, trying to refresh");
      AuthService.refreshUser().catch(e => {
        console.error("Failed to refresh token:", e);
      });
    }
    
    return { hasToken: !!token, hasUser: !!user, hasAxiosAuth, isExpired };
  },

  // Login a user
  login: async (email, password) => {
    try {
      if (!email || !password) {
        throw new Error('Email and password are required');
      }
      
      console.log("Attempting login for:", email);
      
      const response = await api.post('/auth/login', { 
        email, 
        password 
      });
      
      // Check if we got a valid response with token
      if (!response.data || !response.data.token) {
        throw new Error('Invalid server response - no token received');
      }
      
      console.log("Login successful, storing token and user data");
      
      // Store token and user data
      localStorage.setItem(TOKEN_KEY, response.data.token);
      localStorage.setItem(USER_KEY, JSON.stringify(response.data.user));
      
      // Set global axios header for all other components
      axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.token}`;
      
      return response.data.user;
    } catch (error) {
      console.error('Login error details:', error);
      
      // Clear any existing tokens on login failure
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      delete axios.defaults.headers.common['Authorization'];
      
      if (error.response) {
        // Server responded with an error
        console.error('Server response error:', error.response.status, error.response.data);
        throw new Error(error.response.data?.detail || 'Invalid email or password');
      } else if (error.request) {
        // Request made but no response
        console.error('No server response received:', error.request);
        throw new Error('Server not responding. Please try again later.');
      } else {
        // Other errors
        console.error('Other login error:', error.message);
        throw new Error(error.message || 'Login failed');
      }
    }
  },
  
  // Register a new user
  register: async (userData) => {
    try {
      if (!userData.email || !userData.password) {
        throw new Error('Email and password are required');
      }
      
      const response = await api.post('/auth/register', userData);
      
      // Store token and user data
      localStorage.setItem(TOKEN_KEY, response.data.token);
      localStorage.setItem(USER_KEY, JSON.stringify(response.data.user));
      
      // Set global axios header for all other components
      axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.token}`;
      
      return response.data.user;
    } catch (error) {
      console.error('Registration error:', error);
      if (error.response) {
        // Server responded with an error
        throw new Error(error.response.data?.detail || 'Registration failed');
      } else if (error.request) {
        // Request made but no response
        throw new Error('Server not responding. Please try again later.');
      } else {
        // Other errors
        throw new Error(error.message || 'Registration failed');
      }
    }
  },
  
  // Get current user from local storage
  getCurrentUser: () => {
    const userJson = localStorage.getItem(USER_KEY);
    return userJson ? JSON.parse(userJson) : null;
  },
  
  // Refresh user data from the server
  refreshUser: async () => {
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      if (!token) return null;
      
      // If we've tried to refresh recently, don't try again
      const lastRefresh = parseInt(sessionStorage.getItem('last_user_refresh') || '0');
      const now = Date.now();
      if ((now - lastRefresh) < 5000) {
        console.log("Skipping user refresh - attempted too recently");
        return JSON.parse(localStorage.getItem(USER_KEY));
      }
      
      // Mark that we're trying to refresh
      sessionStorage.setItem('last_user_refresh', now.toString());
      
      const response = await api.get('/auth/me');
      localStorage.setItem(USER_KEY, JSON.stringify(response.data));
      return response.data;
    } catch (error) {
      console.error('Failed to refresh user data:', error);
      // Only logout on explicit 401 unauthorized errors
      // But don't logout if we just logged in or navigated
      if (error.response?.status === 401) {
        const lastLoginAttempt = parseInt(sessionStorage.getItem('last_login_attempt') || '0');
        const lastNavigation = parseInt(sessionStorage.getItem('last_navigation') || '0');
        const now = Date.now();
        
        // Only logout if we haven't tried to login or navigate recently
        if ((now - lastLoginAttempt) > 2000 && (now - lastNavigation) > 2000) {
          console.warn('Auth token invalid - logging out');
          AuthService.logout();
        } else {
          console.log("Skipping logout during authentication flow");
        }
      }
      return null;
    }
  },
  
  // Check if user is logged in
  isAuthenticated: () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return false;
    
    // Check if token is expired
    if (AuthService.isTokenExpired()) {
      console.warn("Token expired during authentication check - user will be logged out");
      AuthService.logout();
      return false;
    }
    
    return true;
  },
  
  // Logout user
  logout: () => {
    // Call logout endpoint if needed
    api.post('/auth/logout').catch(() => {
      // Ignore errors on logout
    });
    
    // Clear local storage
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    
    // Remove auth header from axios
    delete axios.defaults.headers.common['Authorization'];
    
    return true;
  },
  
  // Change password
  changePassword: async (oldPassword, newPassword) => {
    try {
      const response = await api.post('/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword
      });
      return response.data;
    } catch (error) {
      console.error('Password change error:', error);
      throw new Error(error.response?.data?.detail || 'Failed to change password');
    }
  }
};

export default AuthService; 