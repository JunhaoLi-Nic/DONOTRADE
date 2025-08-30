import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import axios from 'axios'
import { parseId } from './stores/globals'
import { AuthService } from './services/auth'

// Import FastAPI compatibility layer
import Parse from './utils/auth-fastapi'

// Make Parse available globally for backward compatibility
window.Parse = Parse;

// Import styles
import './assets/base.css'
import './assets/style-dark.css'

// Import layouts
import LoginRegisterLayout from './layouts/LoginRegister.vue'
import DashboardLayout from './layouts/Dashboard.vue'

// Import global state values that might have timestamps
import { validateDateTimestamp } from './utils/utils.js'
import { selectedMonth, selectedDateRange, selectedPeriodRange } from './stores/globals'

// Setup token expiration monitoring to warn user instead of automatic logout
const setupTokenMonitoring = () => {
  // Check token validity every 60 seconds (increased from 30 to reduce frequency)
  const tokenCheckInterval = setInterval(() => {
    // Only run checks if user is supposed to be logged in
    if (localStorage.getItem('auth_token')) {
      if (AuthService.isTokenExpired()) {
        console.warn("Token expired detected by monitor - showing warning instead of automatic logout");
        
        // Instead of automatically redirecting, just show a warning in console
        // This prevents UI freezing when modals or other interactions are happening
        // AuthService.logout();
        // window.location.href = '/';
      }
    } else {
      // No token, no need to keep checking
      clearInterval(tokenCheckInterval);
    }
  }, 60000); // Check every 60 seconds (reduced frequency)

  // Also check whenever the user becomes active after being idle
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && localStorage.getItem('auth_token')) {
      if (AuthService.isTokenExpired()) {
        console.warn("Token expired detected on page visibility change - showing warning instead of logout");
        
        // Instead of automatically redirecting, just show a warning
        // This prevents UI freezing when modals or other interactions are happening
        // AuthService.logout();
        // window.location.href = '/';
      }
    }
  });
}

// Check for invalid timestamps in localStorage and reset them if needed
const checkForInvalidTimestamps = () => {
  const currentTime = Math.floor(Date.now()/1000);
  let resetPerformed = false;
  
  // Force reset all timestamp-related localStorage items to prevent any issues
  const timestampKeys = ['selectedMonth', 'selectedDateRange', 'selectedPeriodRange'];
  
  timestampKeys.forEach(key => {
    try {
      // Remove the item - we'll let the app recreate it with default values
      localStorage.removeItem(key);
      resetPerformed = true;
    } catch (e) {
      console.error(`Error resetting ${key}:`, e);
    }
  });
  
  if (resetPerformed) {
    console.log("Reset timestamp-related localStorage items to prevent future date issues");
  }
}

// Run this check on app start
checkForInvalidTimestamps();

// Run timestamp check before setting up auth
if (!checkForInvalidTimestamps()) {
  // Only proceed with normal initialization if we didn't need to reset
  // Set up axios with authentication token
  const token = localStorage.getItem('auth_token');
  if (token) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    console.log('Global axios headers set with auth token');
    
    // Initialize user data
    const userData = localStorage.getItem('current_user');
    if (!userData) {
      console.log('Token exists but no user data found - will try to refresh user data');
      // We have a token but missing user data - attempt to refresh
      AuthService.refreshUser()
        .then(user => {
          console.log('User data refreshed successfully');
        })
        .catch(err => {
          console.error('Failed to refresh user data:', err);
          // If we can't refresh user data, the token may be invalid
          AuthService.logout();
        });
    }
  }

  // Add global axios error handling
  axios.interceptors.response.use(
    response => response,
    error => {
      console.error('API Error:', error.message)
      
      // Only consider logout for 401 errors from non-auth endpoints
      if (error.response?.status === 401 && 
          !error.config.url.includes('/auth/') && 
          localStorage.getItem('auth_token')) {
          
        // Get timestamps to prevent login loops
        const lastLoginAttempt = parseInt(sessionStorage.getItem('last_login_attempt') || '0');
        const lastNavigation = parseInt(sessionStorage.getItem('last_navigation') || '0');
        const now = Date.now();
        
        // Don't logout if we just tried to login or navigate (within 2 seconds)
        const recentLogin = (now - lastLoginAttempt) < 2000;
        const recentNavigation = (now - lastNavigation) < 2000;
        
        if (!recentLogin && !recentNavigation) {
          console.error('Authentication session expired - redirecting to login');
          AuthService.logout();
          
          // Use window.location instead of router to ensure complete app reload
          window.location.href = '/';
        } else {
          console.log('Ignoring 401 during login/navigation flow');
        }
      }
      
      return Promise.reject(error);
    }
  )

  // Get Parse App ID from API
  console.log('Checking stored Parse App ID:', localStorage.getItem('parseAppId'))
  if (!localStorage.getItem('parseAppId')) {
    axios.post('/api/parseAppId')
      .then(response => {
        const id = response.data
        localStorage.setItem('parseAppId', id)
        parseId.value = id
        console.log('Fetched and stored Parse App ID:', id)
      })
      .catch(error => {
        console.error('Error fetching Parse App ID:', error)
        // Set a default if we can't get it from the API
        localStorage.setItem('parseAppId', '123456')
        parseId.value = '123456'
      })
  } else {
    parseId.value = localStorage.getItem('parseAppId')
  }

  // Initialize app
  const app = createApp(App)

  // Use router
  app.use(router)

  // Start token expiration monitoring
  setupTokenMonitoring();

  // Mount app
  app.mount('#app')
}