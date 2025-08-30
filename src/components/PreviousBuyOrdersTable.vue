<template>
  <div>
    <!-- Previous Buy Orders section header -->
    <div class="table-header">
      <div class="header-title">
        <h3>Previous Buy Orders</h3>
        <div v-if="previousBuyOrders.length > 0" class="order-count-badge">
          {{ previousBuyOrders.length }} preorder{{ previousBuyOrders.length > 1 ? 's' : '' }} pending review
        </div>
        <div class="info-badge" title="These are orders saved with 'preorder' state in MongoDB that don't appear in your current IBKR feed">
          <i class="fa fa-info-circle"></i> Orders in database but not in IBKR
        </div>
      </div>
      
      <div class="header-actions">
        <!-- Hide refresh button when hideRefreshButton prop is true (when in RiskManagement view) -->
        <button 
          v-if="!hideRefreshButton"
          class="refresh-btn"
          @click="fetchPreviousBuyOrders"
          :disabled="loading"
        >
          <reload-outlined v-if="!loading" />
          <a-spin v-else size="small" />
          Refresh
        </button>
        
        <button 
          class="fix-btn"
          @click="fixMissingOrderFields"
          :disabled="fixLoading"
          title="Fix orders with missing ID fields in MongoDB"
        >
          <tool-outlined v-if="!fixLoading" />
          <a-spin v-else size="small" />
          Fix IDs
        </button>
      </div>
    </div>

    <!-- Previous Buy Orders Table -->
    <div class="table-container">
      <table class="stock-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Action</th>
            <th>Order Type</th>
            <th>Total Qty</th>
            <th>Limit Price</th>
            <th>Stop Price</th>
            <th>Current Price</th>
            <th>Position Value</th>
            <th>Allocation %</th>
            <th>Stop Loss Risk</th>
            <th>Stop Loss %</th>
            <th>Potential Profit</th>
            <th>Profit %</th>
            <th>Risk/Reward</th>
            <th>Status</th>
            <th>Why Held</th>
            <th>Catalyst/Driver</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="order in previousBuyOrders" :key="order.orderId">
            <tr :class="{'canceled-row': order.currentState === 'cancel', 'pending-cancel-row': order.status === 'PendingCancel'}">
              <td>
                <div class="symbol-cell">
                  <span class="symbol">{{ order.symbol }}</span>
                  <a-switch 
                    :checked="getPositionType(order.symbol)" 
                    size="small" 
                    @change="() => togglePositionType(order.symbol)"
                    :checkedChildren="'Short'" 
                    :unCheckedChildren="'Long'"
                  />
                </div>
              </td>
              <td>{{ order.action }}</td>
              <td>{{ order.orderType }}</td>
              <td>{{ order.totalQuantity }}</td>
              <td>{{ order.limitPrice }}</td>
              <td>{{ order.stopPrice }}</td>
              <td>{{ order.currentPrice ? '$' + order.currentPrice.toFixed(2) : '-' }}</td>
              <td class="position-value">
                {{ order.positionValue ? '$' + order.positionValue.toFixed(2) : '-' }}
              </td>
              <td class="allocation-value">
                {{ order.allocationPercent ? order.allocationPercent.toFixed(2) + '%' : '-' }}
              </td>
              <td class="risk-value">
                {{ order.stopLossRisk ? '$' + order.stopLossRisk.toFixed(2) : '-' }}
              </td>
              <td class="risk-value">
                {{ order.stopLossPercent ? order.stopLossPercent.toFixed(2) + '%' : '-' }}
              </td>
              <td :class="{ 'positive-value': order.potentialProfit > 0, 'negative-value': order.potentialProfit < 0 }">
                {{ order.potentialProfit ? '$' + order.potentialProfit.toFixed(2) : '-' }}
              </td>
              <td :class="{ 'positive-value': order.potentialProfitPercent > 0, 'negative-value': order.potentialProfitPercent < 0 }">
                {{ order.potentialProfitPercent ? order.potentialProfitPercent.toFixed(2) + '%' : '-' }}
              </td>
              <td :class="{ 'positive-value': order.riskRewardRatio > 0 }">
                {{ order.riskRewardRatio ? order.riskRewardRatio.toFixed(2) : '-' }}
              </td>
              <td>
                <span class="status-badge" :class="getStatusClass(order.status)">
                  <template v-if="order.currentState === 'cancel'">Canceled</template>
                  <template v-else-if="order.status === 'PendingCancel'">Pending Cancel</template>
                  <template v-else>{{ order.status }}</template>
                </span>
              </td>
              <td>
                <OrderReasonForm 
                  :order="order" 
                  :onReasonUpdated="handleOrderReasonUpdate" 
                  :accountBalance="accountBalance" 
                  :showButton="true"
                  :visible="false"
                />
              </td>
              <td>
                <CatalystSelector 
                  :symbol="order.symbol" 
                  :onCatalystSelected="(catalyst) => handleCatalystSelected(order.orderId, catalyst)" 
                  :currentCatalyst="order.catalystData"
                />
              </td>
              <td>
                <button 
                  v-if="order.currentState !== 'cancel' && order.status !== 'PendingCancel'"
                  class="cancel-btn" 
                  @click="cancelOrder(order)"
                  title="Cancel this order"
                >
                  X
                </button>
                <span v-else-if="order.currentState === 'cancel'" class="canceled-text">Canceled</span>
                <span v-else-if="order.status === 'PendingCancel'" class="pending-cancel-text">Pending Cancel</span>
              </td>
            </tr>
          </template>

          <tr v-if="previousBuyOrders.length === 0">
            <td colspan="18" class="empty-table">
              <a-empty description="No previous buy orders found" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, reactive, computed, watch, onMounted } from 'vue';
import {
  Empty,
  Spin,
  Switch,
  message,
} from 'ant-design-vue';
import {
  ReloadOutlined,
  ToolOutlined,
} from '@ant-design/icons-vue';
import axios from '../config/api';
import OrderReasonForm from './OrderReasonForm.vue';
import CatalystSelector from './CatalystSelector.vue';
import { positionTypes as appPositionTypes } from '../utils/positionUtils';
import orderSyncService from '../services/orderSyncService';
import priceService from '../services/priceService';

export default defineComponent({
  name: 'PreviousBuyOrdersTable',
  components: {
    AEmpty: Empty,
    ASpin: Spin,
    ASwitch: Switch,
    ReloadOutlined,
    ToolOutlined,
    OrderReasonForm,
    CatalystSelector
  },
  props: {
    openOrders: {
      type: Array,
      default: () => []
    },
    accountBalance: {
      type: Number,
      default: 100000,
    },
    stockHoldings: {
      type: Array,
      default: () => []
    },
    hideRefreshButton: {
      type: Boolean,
      default: false
    }
  },
  emits: ['orders-updated', 'order-canceled'],
  setup(props, { emit }) {
    // Reactive state
    const loading = ref(false);
    const fixLoading = ref(false);
    const previousBuyOrders = ref([]);
    const currentPrices = reactive({});
    const ordersWithReasons = reactive({});
    const positionTypes = reactive({});
    const ordersWithCatalysts = reactive({});
    
    // Debounce mechanism to prevent multiple API calls
    let fetchTimeout = null;
    
    // Track last fetch time to prevent excessive API calls
    let lastFetchTime = 0;
    const MIN_FETCH_INTERVAL = 5000; // Minimum 5 seconds between fetches
    
    // Fetch previous buy orders using the orderSyncService
    const fetchPreviousBuyOrders = async () => {
      // Clear any pending fetch
      if (fetchTimeout) {
        clearTimeout(fetchTimeout);
        fetchTimeout = null;
      }
      
      // Don't fetch if already loading
      if (loading.value) return;
      
      // Prevent excessive API calls by enforcing minimum time between fetches
      const now = Date.now();
      if (now - lastFetchTime < MIN_FETCH_INTERVAL) {
        console.log(`Skipping fetch - last fetch was ${now - lastFetchTime}ms ago`);
        return;
      }
      
      loading.value = true;
      lastFetchTime = now;
      
      try {
        // Pass the entire openOrders array for more robust matching
        const orders = await orderSyncService.fetchPreviousBuyOrders(props.openOrders);
        previousBuyOrders.value = orders;
        
        // Fetch current prices for these orders, but only if we have orders
        if (orders.length > 0) {
          const symbols = Array.from(new Set(orders.map(order => order.symbol)));
          if (symbols.length > 0) {
            // Always force refresh prices when explicitly clicking refresh
            await priceService.fetchCurrentPrices(
              symbols, 
              true, // Force refresh from API instead of cache
              (data) => {
                console.log('Refreshed prices for previous orders:', Object.keys(data).length);
                // Update local state with the fetched prices
                Object.assign(currentPrices, data);
              },
              (error) => {
                console.error('Error fetching prices for previous orders:', error);
              }
            );
          }
        }
        
        return orders;
      } catch (error) {
        console.error('Error fetching previous buy orders:', error);
        message.error('Failed to fetch previous buy orders');
        return [];
      } finally {
        loading.value = false;
      }
    };

    // Cancel an order by updating its currentState to "cancel"
    const cancelOrder = async (order) => {
      try {
        // Use the MongoDB ID (_id) as the primary identifier, falling back to other IDs if not available
        const orderId = order._id || order.mongoDbId || order.orderId;
        console.log(`Canceling order with ID: ${orderId} (Symbol: ${order.symbol})`);
        
        const response = await orderSyncService.updateOrderState(orderId, 'cancel');
        
        if (response && response.success) {
          // Update local state to mark order as canceled
          const orderIndex = previousBuyOrders.value.findIndex(o => 
            o._id === orderId || o.mongoDbId === orderId || o.orderId === orderId
          );
          
          if (orderIndex !== -1) {
            previousBuyOrders.value[orderIndex].currentState = 'cancel';
            
            // Create a new array to trigger reactivity
            previousBuyOrders.value = [...previousBuyOrders.value];
          }
          
          // Emit event for parent component
          emit('order-canceled', orderId);
          
          // Show success message
          message.success(`Order for ${order.symbol} has been canceled`);
        } else {
          message.error(`Failed to cancel order: ${response?.message || 'Unknown error'}`);
        }
      } catch (error) {
        console.error('Error canceling order:', error);
        message.error(`Failed to cancel order: ${error.message || 'Unknown error'}`);
      }
    };

    // Event handlers for order reason and catalyst updates
    const handleOrderReasonUpdate = (orderId, completed, reasonData) => {
      // Store the reason completion status in the reactive map
      ordersWithReasons[orderId] = completed;
      
      // Find the order in our local state and update it
      const orderToUpdate = previousBuyOrders.value.find(order => order.orderId === orderId);
      
      if (orderToUpdate) {
        console.log(`Updating order ${orderId} with reason data:`, reasonData);
        // Update the order with new data
        orderToUpdate.reasonData = reasonData;
        orderToUpdate.reasonCompleted = completed;
        
        // Force reactivity
        previousBuyOrders.value = [...previousBuyOrders.value];
      }
    };
    
    const handleCatalystSelected = (orderId, catalyst) => {
      // Store catalyst data in the reactive map
      ordersWithCatalysts[orderId] = catalyst;
      
      // Find the order and update its catalyst data
      const orderToUpdate = previousBuyOrders.value.find(order => order.orderId === orderId);
      
      if (orderToUpdate) {
        orderToUpdate.catalystData = catalyst;
        
        // Force reactivity
        previousBuyOrders.value = [...previousBuyOrders.value];
      }
    };

    // Position type handling
    const getPositionType = (symbol) => {
      if (!symbol) return false;
      
      // Check in app-wide position types first
      if (appPositionTypes.hasOwnProperty(symbol)) {
        return appPositionTypes[symbol];
      }
      
      // Check local position types
      if (positionTypes.hasOwnProperty(symbol)) {
        return positionTypes[symbol];
      }
      
      // Otherwise check holdings
      const existingHolding = props.stockHoldings.find(holding => holding.symbol === symbol);
      if (existingHolding) {
        const isShort = existingHolding.shares < 0 || !!existingHolding.isShort;
        positionTypes[symbol] = isShort;
        appPositionTypes[symbol] = isShort;
        return isShort;
      }
      
      // Default to long
      positionTypes[symbol] = false;
      return false;
    };
    
    const togglePositionType = (symbol) => {
      if (!symbol) return;
      
      const currentType = getPositionType(symbol);
      positionTypes[symbol] = !currentType;
      appPositionTypes[symbol] = !currentType;
      
      console.log(`Setting ${symbol} to ${!currentType ? 'SHORT' : 'LONG'}`);
      
      // Force reactivity
      previousBuyOrders.value = [...previousBuyOrders.value];
    };

    // Status CSS class helper
    const getStatusClass = (status) => {
      if (!status) return 'status-default';
      
      switch (status.toLowerCase()) {
        case 'filled':
          return 'status-success';
        case 'submitted':
        case 'presubmitted':
          return 'status-processing';
        case 'cancelled':
        case 'canceled':
        case 'pendingcancel':
          return 'status-error';
        case 'pendingsubmit':
          return 'status-warning';
        default:
          return 'status-default';
      }
    };

    // No need to calculate metrics as they come directly from the backend
    // Just keeping the position type handling functions

    // Fix orders with missing fields in MongoDB
    const fixMissingOrderFields = async () => {
      fixLoading.value = true;
      try {
        const result = await orderSyncService.fixMissingOrderFields();
        if (result.success) {
          message.success(`Fixed ${result.updated_count} orders with missing fields`);
          // Refresh the orders list after fixing
          await fetchPreviousBuyOrders();
        } else {
          message.error('Failed to fix orders with missing fields');
        }
      } catch (error) {
        console.error('Error fixing orders with missing fields:', error);
        message.error('Failed to fix orders with missing fields');
      } finally {
        fixLoading.value = false;
      }
    };

    // Load data on component mount, not when props change
    onMounted(() => {
      // Use setTimeout to ensure this happens after the parent component is fully mounted
      // and to prevent race conditions with other components
      setTimeout(() => {
        // Only fetch if we have open orders to compare against
        if (props.openOrders && props.openOrders.length > 0) {
          console.log('Initial fetch of previous buy orders');
          fetchPreviousBuyOrders();
        } else {
          console.log('Delaying fetch until open orders are available');
          // Try again in 2 seconds if no open orders yet
          setTimeout(() => {
            fetchPreviousBuyOrders();
          }, 2000);
        }
      }, 1000);
    });

    // Return what's needed in the template
    return {
      loading,
      fixLoading,
      previousBuyOrders,
      fetchPreviousBuyOrders,
      fixMissingOrderFields,
      cancelOrder,
      getPositionType,
      togglePositionType,
      handleOrderReasonUpdate,
      handleCatalystSelected,
      getStatusClass,
      accountBalance: props.accountBalance
    };
  }
});
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

.header-title h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #e0e0e0;
}

.order-count-badge {
  background-color: rgba(255, 152, 0, 0.2);
  color: #ff9800;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.info-badge {
  background-color: rgba(74, 108, 247, 0.2);
  color: #4a6cf7;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: help;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.refresh-btn, .fix-btn {
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
}

.refresh-btn:hover, .fix-btn:hover {
  background-color: #3a5cd8;
}

.refresh-btn:disabled, .fix-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.fix-btn {
  background-color: #ff9800;
}

.fix-btn:hover {
  background-color: #f57c00;
}

.cancel-btn {
  background-color: #f44336;
  color: white;
  border: none;
  border-radius: 4px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 14px;
  padding: 0;
}

.cancel-btn:hover {
  background-color: #d32f2f;
}

.canceled-text {
  color: #f44336;
  font-style: italic;
  font-size: 12px;
}

.pending-cancel-text {
  color: #ff9800;
  font-style: italic;
  font-size: 12px;
}

.table-container {
  width: 100%;
  overflow-x: auto;
  margin-bottom: 24px;
}

.stock-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.stock-table th {
  background-color: #1c1c1c;
  color: #a0a0a0;
  border-bottom: 1px solid #3a3a3a;
  text-align: left;
  padding: 10px;
  font-weight: normal;
}

.stock-table td {
  border-bottom: 1px solid #2a2a2a;
  padding: 10px;
  color: #e0e0e0;
}

.stock-table tr:hover td {
  background-color: #2a2a2a;
}

.canceled-row td {
  opacity: 0.6;
  text-decoration: line-through;
  background-color: rgba(244, 67, 54, 0.05);
}

.canceled-row:hover td {
  background-color: rgba(244, 67, 54, 0.1);
}

.pending-cancel-row td {
  opacity: 0.8;
  font-style: italic;
  background-color: rgba(255, 152, 0, 0.05);
}

.pending-cancel-row:hover td {
  background-color: rgba(255, 152, 0, 0.1);
}

.symbol-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.symbol {
  font-weight: 500;
}

.empty-table {
  text-align: center;
  padding: 32px 0;
}

:deep(.ant-empty-description) {
  color: #a0a0a0;
}

:deep(.ant-switch-checked) {
  background-color: #4a6cf7;
}

:deep(.ant-spin-dot i) {
  background-color: #4a6cf7;
}

/* Status badges */
.status-badge {
  display: inline-flex;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-success {
  background-color: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.status-processing {
  background-color: rgba(74, 108, 247, 0.2);
  color: #4a6cf7;
}

.status-error {
  background-color: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.status-warning {
  background-color: rgba(255, 152, 0, 0.2);
  color: #ff9800;
}

.status-default {
  background-color: rgba(158, 158, 158, 0.2);
  color: #9e9e9e;
}

/* Add styles for profit/loss values */
.positive-value {
  color: #4caf50;
}

.negative-value {
  color: #f44336;
}

/* Styling for various data cells */
.position-value {
  font-weight: 500;
  color: #e0e0e0;
}

.allocation-value {
  font-weight: 500;
  color: #4a6cf7;
}

.risk-value {
  font-weight: 500;
  color: #f44336; /* Always show risk in red */
}
</style> 