<script setup>
import { useRoute } from 'vue-router';
import TradeUploadManager from './components/TradeUploadManager.vue';
import ServerStatusMonitor from './components/ServerStatusMonitor.vue';
import { ref } from 'vue';

// Only show debug UI when in development or debug mode is enabled
const showDebug = ref(import.meta.env.DEV || localStorage.getItem('debug_mode') === 'true');

const route = useRoute();
</script>
<template>
    <component :is="$route.meta.layout || 'div'">
        <RouterView :key="route.fullPath" />
    </component>
    
    <!-- Trade Upload Manager Component -->
    <TradeUploadManager />
    
    <!-- Server Status Monitor - only show in debug mode -->
    <ServerStatusMonitor v-if="showDebug" />
    
    <!-- Auth error modal -->
    <div v-if="showAuthError" class="auth-error-modal">
        <div class="auth-error-content">
            <h3>Session Expired</h3>
            <p>Your session has expired. Please log in again to continue.</p>
            
            <div v-if="loginError" class="alert alert-danger">
                {{ loginError }}
            </div>
            
            <form @submit.prevent="handleLogin">
                <div class="form-group mb-3">
                    <label for="email">Email</label>
                    <input 
                        type="email" 
                        class="form-control" 
                        id="email" 
                        v-model="loginEmail" 
                        placeholder="Enter your email"
                        required
                    >
                </div>
                
                <div class="form-group mb-3">
                    <label for="password">Password</label>
                    <input 
                        type="password" 
                        class="form-control" 
                        id="password" 
                        v-model="loginPassword" 
                        placeholder="Enter your password"
                        required
                    >
                </div>
                
                <div class="d-grid">
                    <button 
                        type="submit" 
                        class="btn btn-primary" 
                        :disabled="isLoggingIn"
                    >
                        {{ isLoggingIn ? 'Logging in...' : 'Login' }}
                    </button>
                </div>
            </form>
        </div>
    </div>
</template>

<script>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import LoginRegisterLayout from './layouts/LoginRegister.vue'
import DashboardLayout from './layouts/Dashboard.vue'
import { AuthService } from './services/auth'

// For handling expired sessions
const showAuthError = ref(false);
const loginEmail = ref('');
const loginPassword = ref('');
const loginError = ref('');
const isLoggingIn = ref(false);

// Listen for authentication events
window.addEventListener('auth:expired', () => {
    showAuthError.value = true;
});

export default {
    components: {
        LoginRegisterLayout,
        DashboardLayout,
        TradeUploadManager,
        ServerStatusMonitor
    },
    setup() {
        const route = useRoute()
        
        const layout = computed(() => {
            return route.meta.layout === 'login-register' ? LoginRegisterLayout : DashboardLayout
        })
        
        const handleLogin = async () => {
            if (!loginEmail.value || !loginPassword.value) {
                loginError.value = "Please enter both email and password";
                return;
            }
            
            try {
                isLoggingIn.value = true;
                loginError.value = '';
                
                await AuthService.login(loginEmail.value, loginPassword.value);
                
                // Reset form and hide modal
                loginEmail.value = '';
                loginPassword.value = '';
                showAuthError.value = false;
                
                // Reload the page to refresh all data
                window.location.reload();
            } catch (error) {
                loginError.value = error.message || "Login failed. Please try again.";
            } finally {
                isLoggingIn.value = false;
            }
        };
        
        return {
            layout,
            // Auth error handling
            showAuthError,
            loginEmail,
            loginPassword,
            loginError,
            isLoggingIn,
            handleLogin
        }
    }
}
</script>

<style>
/* Auth modal styling */
.auth-error-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

.auth-error-content {
  background-color: white;
  padding: 2rem;
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

/* Override any conflicts with Bootstrap modals */
.auth-error-modal .form-group label {
  display: block;
  margin-bottom: 0.5rem;
}

.auth-error-modal input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ced4da;
  border-radius: 0.25rem;
}

.auth-error-modal .btn {
  width: 100%;
  padding: 0.5rem;
  margin-top: 1rem;
}

/* React component wrappers for consistent styling */
.server-status-monitor,
.trade-upload-manager {
  font-family: 'Nunito Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* Ensure main content appears below the navbar and its dropdowns */
#app {
  z-index: 1;
  position: relative;
}

/* Global dropdown fixes */
.dropdown-menu {
  z-index: 99999 !important;
  position: absolute !important;
}

/* Fix specifically for the navbar dropdowns */
#navbarDropdown + .dropdown-menu,
button[data-bs-toggle="dropdown"] + .dropdown-menu, 
#step11 .dropdown-menu,
#step12 .dropdown-menu {
  z-index: 99999 !important;
  position: fixed !important;
  inset: auto !important;
}

/* Make sure Daily and Calendar content stays beneath dropdowns */
.dailyCard, .calendar-container, 
[data-bs-toggle="tab"], .tab-content, .tab-pane {
  z-index: 1 !important;
  position: relative !important;
}
</style>
