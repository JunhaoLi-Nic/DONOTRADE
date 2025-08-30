<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
import { AuthService } from '../services/auth.js';

const apiLogs = ref([]);
const debugVisible = ref(false);
const endpoints = ref([]);
const testEndpoint = ref('/api/trades');
const testMethod = ref('get');
const testRequestBody = ref('{}');
const testResponse = ref('');

// Toggle debug console visibility
const toggleDebug = () => {
  debugVisible.value = !debugVisible.value;
};

// Check available endpoints
const discoverEndpoints = async () => {
  try {
    addLog('Discovering endpoints...');
    // Try to get OpenAPI schema
    try {
      const schemaResponse = await axios.get('/openapi.json');
      endpoints.value = Object.keys(schemaResponse.data.paths);
      addLog(`Found ${endpoints.value.length} endpoints in OpenAPI schema`);
    } catch (e) {
      addLog('OpenAPI schema not available, trying common endpoints');
      
      // Try common endpoints
      const commonEndpoints = [
        '/api/trades', 
        '/api/user/current', 
        '/api/user/me',
        '/api/trades_upload',
        '/api/upload/trades'
      ];
      
      for (const endpoint of commonEndpoints) {
        try {
          await axios.get(endpoint);
          endpoints.value.push(endpoint);
          addLog(`Endpoint ${endpoint} is available`);
        } catch (error) {
          if (error.response && error.response.status !== 404) {
            // If not 404, the endpoint exists but might require authentication or different method
            endpoints.value.push(endpoint);
            addLog(`Endpoint ${endpoint} exists (status: ${error.response.status})`);
          }
        }
      }
    }
  } catch (error) {
    addLog(`Error discovering endpoints: ${error.message}`);
  }
};

// Test an endpoint
const testApi = async () => {
  try {
    addLog(`Testing ${testMethod.value.toUpperCase()} ${testEndpoint.value}`);
    
    const config = {
      headers: {}
    };
    
    // Add auth header if token exists
    const token = AuthService.token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      addLog('Added authorization header');
    }
    
    // Parse request body
    let data = {};
    try {
      data = JSON.parse(testRequestBody.value);
    } catch (e) {
      addLog('Warning: Invalid JSON in request body');
      data = { test: true };
    }
    
    // Make request
    let response;
    if (testMethod.value === 'get') {
      response = await axios.get(testEndpoint.value, config);
    } else {
      response = await axios[testMethod.value](testEndpoint.value, data, config);
    }
    
    // Display response
    testResponse.value = JSON.stringify(response.data, null, 2);
    addLog(`Response: ${response.status} ${response.statusText}`);
  } catch (error) {
    testResponse.value = JSON.stringify({
      error: error.message,
      response: error.response ? {
        status: error.response.status,
        statusText: error.response.statusText,
        data: error.response.data
      } : 'No response'
    }, null, 2);
    
    addLog(`Error: ${error.message}`);
  }
};

// Add a log entry
const addLog = (message) => {
  const timestamp = new Date().toLocaleTimeString();
  apiLogs.value.push(`[${timestamp}] ${message}`);
  
  // Keep logs to a reasonable size
  if (apiLogs.value.length > 100) {
    apiLogs.value = apiLogs.value.slice(-100);
  }
};

// Monitor all axios requests
onMounted(() => {
  // Add interceptors to monitor requests
  axios.interceptors.request.use(
    config => {
      addLog(`Request: ${config.method.toUpperCase()} ${config.url}`);
      return config;
    },
    error => {
      addLog(`Request error: ${error.message}`);
      return Promise.reject(error);
    }
  );
  
  // Add interceptors to monitor responses
  axios.interceptors.response.use(
    response => {
      addLog(`Response: ${response.status} ${response.statusText}`);
      return response;
    },
    error => {
      if (error.response) {
        addLog(`Response error: ${error.response.status} ${error.response.statusText}`);
      } else {
        addLog(`Response error: ${error.message}`);
      }
      return Promise.reject(error);
    }
  );
});
</script>

<template>
  <div class="api-debug">
    <button @click="toggleDebug" class="debug-toggle-btn" title="API Debug">
      <i class="uil uil-bug"></i>
    </button>
    
    <div v-if="debugVisible" class="debug-console">
      <div class="debug-header">
        <h3>API Debug Console</h3>
        <button @click="toggleDebug" class="close-btn">&times;</button>
      </div>
      
      <div class="debug-content">
        <div class="debug-actions">
          <button @click="discoverEndpoints" class="btn btn-sm btn-primary">Discover Endpoints</button>
          
          <div class="endpoint-test mt-3">
            <h4>Test Endpoint</h4>
            <div class="input-group mb-2">
              <select v-model="testMethod" class="form-control">
                <option value="get">GET</option>
                <option value="post">POST</option>
                <option value="put">PUT</option>
                <option value="delete">DELETE</option>
              </select>
              <input v-model="testEndpoint" type="text" class="form-control" placeholder="/api/endpoint" />
              <button @click="testApi" class="btn btn-primary">Test</button>
            </div>
            
            <div v-if="testMethod !== 'get'" class="mb-2">
              <textarea v-model="testRequestBody" class="form-control" placeholder="Request body (JSON)" rows="3"></textarea>
            </div>
            
            <div v-if="endpoints.length > 0" class="endpoints-list mb-2">
              <label>Available Endpoints:</label>
              <div class="list-group">
                <button 
                  v-for="endpoint in endpoints" 
                  @click="testEndpoint = endpoint"
                  class="list-group-item list-group-item-action"
                >
                  {{ endpoint }}
                </button>
              </div>
            </div>
            
            <div v-if="testResponse" class="response-display">
              <label>Response:</label>
              <pre>{{ testResponse }}</pre>
            </div>
          </div>
        </div>
        
        <div class="logs-display">
          <h4>API Logs</h4>
          <div class="logs">
            <div v-for="(log, index) in apiLogs" :key="index" class="log-entry">
              {{ log }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.api-debug {
  position: fixed;
  right: 10px;
  bottom: 10px;
  z-index: 1000;
}

.debug-toggle-btn {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #007bff;
  color: white;
  border: none;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}

.debug-console {
  position: fixed;
  right: 10px;
  bottom: 60px;
  width: 80%;
  max-width: 800px;
  height: 70vh;
  background: white;
  border-radius: 6px;
  box-shadow: 0 3px 10px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.debug-header {
  padding: 10px 15px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.debug-header h3 {
  margin: 0;
  font-size: 16px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}

.debug-content {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.debug-actions {
  flex: 1;
  padding: 15px;
  border-right: 1px solid #e9ecef;
  overflow-y: auto;
}

.logs-display {
  flex: 1;
  padding: 15px;
  background: #f8f9fa;
  overflow-y: auto;
}

.logs {
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
  overflow-y: auto;
  height: calc(100% - 30px);
}

.log-entry {
  margin-bottom: 5px;
  padding: 3px 0;
  border-bottom: 1px solid #e9ecef;
}

.response-display pre {
  background: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  overflow: auto;
  max-height: 200px;
  font-size: 12px;
}

.endpoints-list {
  max-height: 150px;
  overflow-y: auto;
}

.list-group-item {
  padding: 5px 10px;
  font-size: 12px;
  cursor: pointer;
}
</style> 