<template>
  <div class="table-header">
    <div class="header-title">
      <div v-if="ordersNeedingPrices > 0" class="missing-data-badge">
        <info-circle-outlined /> {{ ordersNeedingPrices }} order{{ ordersNeedingPrices > 1 ? 's' : '' }} missing price data
      </div>
      
      <div class="risk-info" v-if="totalStopLossRisk !== 0">
        Total Stop Loss Risk: <span class="risk-amount">${{ Math.abs(totalStopLossRisk).toFixed(2) }} ({{ totalRiskPercent.toFixed(2) }}%)</span>
      </div>
    </div>
    
    <div class="header-actions">
      <!-- Hide refresh button when hideRefreshButton prop is true (when in RiskManagement view) -->
      <button 
        v-if="!hideRefreshButton"
        class="refresh-btn"
        @click="handleRefreshPrices"
        :disabled="priceLoading"
      >
        <reload-outlined v-if="!priceLoading" />
        <a-spin v-else size="small" />
        Refresh Prices
      </button>
      
      <button 
        class="save-btn"
        @click="saveOrdersToMongoDB"
        :disabled="saveLoading"
      >
        <cloud-upload-outlined v-if="!saveLoading" />
        <a-spin v-else size="small" />
        Save Orders
      </button>

      <button 
        class="load-btn"
        @click="loadOrdersFromMongoDB"
        :disabled="loadLoading"
      >
        <cloud-download-outlined v-if="!loadLoading" />
        <a-spin v-else size="small" />
        Load Orders
      </button>
    </div>
  </div>
</template>

<script>
import { defineComponent } from 'vue'
import {
  Spin,
} from 'ant-design-vue'
import {
  ReloadOutlined,
  InfoCircleOutlined,
  CloudUploadOutlined,
  CloudDownloadOutlined,
} from '@ant-design/icons-vue'

export default defineComponent({
  name: 'OrderTableHeader',
  components: {
    ASpin: Spin,
    ReloadOutlined,
    InfoCircleOutlined,
    CloudUploadOutlined,
    CloudDownloadOutlined,
  },
  props: {
    ordersNeedingPrices: {
      type: Number,
      default: 0
    },
    totalStopLossRisk: {
      type: Number,
      default: 0
    },
    totalRiskPercent: {
      type: Number,
      default: 0
    },
    hideRefreshButton: {
      type: Boolean,
      default: false
    },
    priceLoading: {
      type: Boolean,
      default: false
    },
    saveLoading: {
      type: Boolean,
      default: false
    },
    loadLoading: {
      type: Boolean,
      default: false
    },
    // Event handlers
    handleRefreshPrices: {
      type: Function,
      required: true
    },
    saveOrdersToMongoDB: {
      type: Function,
      required: true
    },
    loadOrdersFromMongoDB: {
      type: Function,
      required: true
    }
  }
})
</script>

<style scoped>
.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.save-btn, .load-btn, .refresh-btn {
  background-color: #4a6cf7;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.save-btn {
  background-color: #4caf50;
}

.save-btn:hover {
  background-color: #388e3c;
}

.load-btn {
  background-color: #ff9800;
}

.load-btn:hover {
  background-color: #f57c00;
}

.refresh-btn:hover {
  background-color: #3a5cd8;
}

.save-btn:disabled, .load-btn:disabled, .refresh-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.risk-info {
  color: #a0a0a0;
  font-size: 14px;
}

.risk-amount {
  color: #f44336;
  font-weight: 500;
}

.missing-data-badge {
  background-color: rgba(255, 152, 0, 0.2);
  color: #ff9800;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

:deep(.ant-spin-dot i) {
  background-color: #ffffff;
}
</style>