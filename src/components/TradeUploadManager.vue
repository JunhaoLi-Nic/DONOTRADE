<template>
  <div class="trade-upload-manager">
    <div class="toggle-button">
      <button 
        v-if="localTrades.length > 0"
        @click="showManager = !showManager"
        class="local-trades-button"
      >
        <span class="trade-count">{{ localTrades.length }}</span>
        <span>Local Trades</span>
      </button>
    </div>

    <div v-if="showManager" class="panel">
      <div class="panel-header">
        <h3>Trade Upload Manager</h3>
        <button @click="showManager = false" class="close-button">×</button>
      </div>

      <div v-if="syncResult" :class="['result', syncResult.success ? 'success' : 'error']">
        {{ syncResult.message }}
      </div>

      <div class="local-trades-info">
        <h4>Local Storage</h4>
        <div v-if="localTrades.length > 0" class="trades-count">
          <p>
            You have <strong>{{ localTrades.length }}</strong> trade{{ localTrades.length !== 1 ? 's' : '' }} stored locally.
          </p>
          <p class="help-text">
            These trades are saved in your browser and will be available even if you close the page.
          </p>
        </div>
        <p v-else class="empty-message">No trades stored locally.</p>
      </div>

      <template v-if="localTrades.length > 0">
        <div class="trade-list">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Qty</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(trade, index) in localTrades" :key="trade.id || index" :class="{ 'even-row': index % 2 === 0 }">
                <td>{{ trade.symbol }}</td>
                <td :class="trade.side?.toLowerCase() === 'buy' ? 'buy-side' : 'sell-side'">
                  {{ trade.side }}
                </td>
                <td>{{ trade.quantity || trade.qty }}</td>
                <td>{{ formatDate(trade.date || trade.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="actions">
          <button
            @click="handleClear"
            :disabled="isSyncing"
            class="clear-button"
          >
            Clear
          </button>
          <button
            @click="handleSync"
            :disabled="isSyncing"
            class="sync-button"
          >
            {{ isSyncing ? 'Syncing...' : 'Sync with Server' }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import { DirectUpload } from '../utils/direct-upload';

export default {
  name: 'TradeUploadManager',
  
  data() {
    return {
      localTrades: [],
      isSyncing: false,
      syncResult: null,
      showManager: false
    };
  },
  
  mounted() {
    this.loadLocalTrades();
    
    // Set up interval to refresh trades
    this.refreshInterval = setInterval(this.loadLocalTrades, 5000);
    
    // Listen for trade-manager:open event
    window.addEventListener('trade-manager:open', this.handleOpenEvent);
  },
  
  beforeUnmount() {
    clearInterval(this.refreshInterval);
    window.removeEventListener('trade-manager:open', this.handleOpenEvent);
  },
  
  methods: {
    loadLocalTrades() {
      const trades = DirectUpload.getLocalTrades();
      this.localTrades = trades;
    },
    
    handleOpenEvent() {
      this.showManager = true;
    },
    
    async handleSync() {
      if (this.isSyncing) return;
      
      this.isSyncing = true;
      this.syncResult = null;
      
      try {
        const result = await DirectUpload.syncLocalTrades();
        this.syncResult = result;
        
        // Refresh local trades
        this.loadLocalTrades();
      } catch (error) {
        this.syncResult = {
          success: false,
          message: `Sync failed: ${error.message}`
        };
      } finally {
        this.isSyncing = false;
      }
    },
    
    handleClear() {
      if (window.confirm('Are you sure you want to clear all locally stored trades? This cannot be undone.')) {
        DirectUpload.clearLocalTrades();
        this.localTrades = [];
        this.syncResult = {
          success: true,
          message: 'All local trades cleared'
        };
      }
    },
    
    formatDate(dateString) {
      return new Date(dateString).toLocaleString();
    }
  }
};
</script>

<style scoped>
.trade-upload-manager {
  font-family: sans-serif;
}

.local-trades-button {
  position: fixed;
  bottom: 20px;
  right: 20px;
  padding: 8px 12px;
  background: #f97316;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  z-index: 50;
}

.trade-count {
  display: inline-block;
  width: 18px;
  height: 18px;
  background: white;
  color: #f97316;
  border-radius: 50%;
  font-size: 12px;
  font-weight: bold;
  line-height: 18px;
  text-align: center;
}

.panel {
  position: fixed;
  bottom: 80px;
  right: 20px;
  width: 350px;
  max-height: 500px;
  overflow-y: auto;
  background: white;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
  padding: 16px;
  z-index: 50;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 8px;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
}

.close-button {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 16px;
}

.result {
  padding: 10px;
  margin-bottom: 16px;
  border-radius: 4px;
}

.result.success {
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.result.error {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.local-trades-info {
  margin-bottom: 16px;
}

.local-trades-info h4 {
  font-size: 14px;
  margin-bottom: 8px;
}

.trades-count p {
  margin: 0 0 8px 0;
}

.help-text {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
}

.empty-message {
  margin: 0;
  color: #6b7280;
}

.trade-list {
  margin-bottom: 16px;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

thead tr {
  background: #f9fafb;
}

th {
  padding: 8px;
  text-align: left;
}

th:nth-child(2), th:nth-child(3), th:nth-child(4) {
  text-align: right;
}

td {
  padding: 8px;
  text-align: left;
  border-top: 1px solid #e5e7eb;
}

td:nth-child(2), td:nth-child(3), td:nth-child(4) {
  text-align: right;
}

.buy-side {
  color: #059669;
}

.sell-side {
  color: #e11d48;
}

.even-row {
  background-color: #f9fafb;
}

.actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.clear-button {
  padding: 8px 12px;
  background: white;
  color: #e11d48;
  border: 1px solid #e11d48;
  border-radius: 4px;
  cursor: pointer;
}

.clear-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.sync-button {
  padding: 8px 12px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.sync-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style> 