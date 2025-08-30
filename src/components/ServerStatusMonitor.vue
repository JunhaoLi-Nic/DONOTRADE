<template>
  <div class="server-status-monitor">
    <div 
      class="status-indicator"
      @click="showDetails = !showDetails"
    >
      <div :class="['status-dot', serverStatusClass]"></div>
      <span>
        API: {{ serverStatusText }}
      </span>
    </div>
    
    <div v-if="showDetails" class="status-details">
      <div class="details-header">
        <h4>API Status</h4>
        <div class="last-checked">
          Last checked: {{ formattedLastChecked }}
        </div>
      </div>
      
      <div class="endpoint-list">
        <template v-if="Object.entries(endpoints).length > 0">
          <div 
            v-for="(status, endpoint) in endpoints" 
            :key="endpoint" 
            class="endpoint-item"
          >
            <div class="endpoint-name">{{ endpoint }}</div>
            <div :class="['endpoint-status', getStatusClass(status)]">
              {{ status }}
            </div>
          </div>
        </template>
        <div v-else class="checking-message">
          Checking endpoints...
        </div>
      </div>
      
      <div class="status-message">
        <p v-if="serverStatus === 'online'">
          API server is responding normally.
        </p>
        <p v-else-if="serverStatus === 'offline'">
          API server is not responding. Data will be stored locally until the server is available again.
        </p>
        <p v-else>
          Checking API server status...
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  name: 'ServerStatusMonitor',
  
  data() {
    return {
      serverStatus: 'checking', // 'online', 'offline', 'checking'
      lastChecked: null,
      showDetails: false,
      endpoints: {}
    };
  },
  
  computed: {
    serverStatusClass() {
      return {
        'status-online': this.serverStatus === 'online',
        'status-offline': this.serverStatus === 'offline',
        'status-checking': this.serverStatus === 'checking'
      };
    },
    
    serverStatusText() {
      return this.serverStatus === 'online' ? 'Online' : 
             this.serverStatus === 'offline' ? 'Offline' : 
             'Checking...';
    },
    
    formattedLastChecked() {
      if (!this.lastChecked) return 'Never';
      
      const now = new Date();
      const diff = Math.floor((now - this.lastChecked) / 1000); // Difference in seconds
      
      if (diff < 60) {
        return `${diff} second${diff !== 1 ? 's' : ''} ago`;
      } else if (diff < 3600) {
        const minutes = Math.floor(diff / 60);
        return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
      } else {
        return this.lastChecked.toLocaleTimeString();
      }
    }
  },
  
  mounted() {
    // Check status immediately
    this.checkServerStatus();
    
    // Set up interval to check status every 60 seconds
    this.statusInterval = setInterval(this.checkServerStatus, 60000);
  },
  
  beforeUnmount() {
    clearInterval(this.statusInterval);
  },
  
  methods: {
    async checkServerStatus() {
      try {
        // Try to access the /api/trades endpoint
        const response = await axios.get('/api/trades', {
          params: { limit: 1 },
          timeout: 5000 // Timeout after 5 seconds
        });
        
        // If we get here, the server is online
        this.serverStatus = 'online';
        this.lastChecked = new Date();
        
        // Check available endpoints
        const endpointStatuses = { ...this.endpoints };
        
        // Test trade endpoints
        const endpointsToTest = [
          { method: 'get', url: '/api/trades' },
          { method: 'post', url: '/api/trades/single' },
          { method: 'post', url: '/api/trades/bulk' }
        ];
        
        for (const endpoint of endpointsToTest) {
          try {
            // Only try GET requests or with minimal data for POST
            if (endpoint.method === 'get') {
              await axios.get(endpoint.url, { params: { limit: 1 }, timeout: 3000 });
            } else {
              // For POST requests, send minimal data
              await axios.post(endpoint.url, { test: true }, { timeout: 3000 });
            }
            
            endpointStatuses[`${endpoint.method} ${endpoint.url}`] = 'available';
          } catch (error) {
            const status = error.response?.status;
            
            if (status === 401) {
              // Authentication required but endpoint exists
              endpointStatuses[`${endpoint.method} ${endpoint.url}`] = 'auth required';
            } else if (status === 404) {
              // Endpoint doesn't exist
              endpointStatuses[`${endpoint.method} ${endpoint.url}`] = 'not found';
            } else if (status === 405) {
              // Method not allowed but endpoint exists
              endpointStatuses[`${endpoint.method} ${endpoint.url}`] = 'method not allowed';
            } else {
              // Other error
              endpointStatuses[`${endpoint.method} ${endpoint.url}`] = `error (${status || 'unknown'})`;
            }
          }
        }
        
        this.endpoints = endpointStatuses;
      } catch (error) {
        console.error('Server status check failed:', error);
        this.serverStatus = 'offline';
        this.lastChecked = new Date();
      }
    },
    
    getStatusClass(status) {
      if (status === 'available') return 'status-available';
      if (status === 'auth required') return 'status-warning';
      return 'status-error';
    }
  }
};
</script>

<style scoped>
.server-status-monitor {
  position: fixed;
  bottom: 20px;
  left: 20px;
  z-index: 50;
  font-family: sans-serif;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  font-size: 12px;
}

.status-indicator {
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
}

.server-status-monitor:deep(.status-online) ~ .status-indicator {
  background-color: #ecfdf5;
  border: 1px solid #a7f3d0;
}

.server-status-monitor:deep(.status-offline) ~ .status-indicator {
  background-color: #fef2f2;
  border: 1px solid #fecaca;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #9ca3af;
}

.status-dot.status-online {
  background-color: #10b981;
}

.status-dot.status-offline {
  background-color: #ef4444;
}

.status-details {
  position: absolute;
  bottom: 40px;
  left: 0;
  width: 280px;
  background-color: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  padding: 12px;
  font-size: 12px;
}

.details-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  border-bottom: 1px solid #f3f4f6;
  padding-bottom: 8px;
}

.details-header h4 {
  margin: 0;
  font-size: 14px;
}

.last-checked {
  color: #6b7280;
  font-size: 11px;
}

.endpoint-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  border-bottom: 1px solid #f9fafb;
}

.endpoint-name {
  font-family: monospace;
}

.endpoint-status.status-available {
  color: #10b981;
}

.endpoint-status.status-warning {
  color: #f59e0b;
}

.endpoint-status.status-error {
  color: #ef4444;
}

.checking-message {
  color: #6b7280;
  text-align: center;
  padding: 8px 0;
}

.status-message {
  margin-top: 12px;
  font-size: 11px;
  color: #6b7280;
}

.status-message p {
  margin: 0;
}
</style> 