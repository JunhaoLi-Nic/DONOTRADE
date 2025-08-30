<template>
  <div>
    <!-- New Position Orders section -->
    <div class="section-title">New Position Orders</div>
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
            <th>Weighted Profit</th>
            <th>Weighted Loss</th>
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
          </tr>
        </thead>
        <tbody>
          <!-- Loop through symbols first -->
          <template v-for="symbolData in newPositionsBySymbol" :key="symbolData.symbol">
            <!-- Render main order -->
            <tr 
              v-if="symbolData.mainOrder" 
              :key="symbolData.mainOrder.orderId"
              @click="toggleExpand(symbolData.mainOrder.orderId)" 
              class="main-order-row" 
              :class="{'expanded': expandedOrders[symbolData.mainOrder.orderId], 'expandable': symbolData.subOrders.length > 0}"
            >
              <td>
                <div class="symbol-cell">
                  <!-- Only show expand icon if there are sub-orders -->
                  <span v-if="symbolData.subOrders.length > 0" class="expand-icon">
                    <down-outlined v-if="expandedOrders[symbolData.mainOrder.orderId]" />
                    <right-outlined v-else />
                  </span>
                  <span class="symbol">{{ symbolData.mainOrder.symbol }}</span>
                  <!-- Add sub-order count badge -->
                  <span v-if="getActiveSubOrders(symbolData.subOrders).length > 0" class="exit-orders-badge">
                    {{ getActiveSubOrders(symbolData.subOrders).length }}
                  </span>
                  <a-switch 
                    :checked="getPositionType(symbolData.mainOrder.symbol)" 
                    size="small" 
                    @change="() => togglePositionType(symbolData.mainOrder.symbol)"
                    :checkedChildren="'Short'" 
                    :unCheckedChildren="'Long'"
                    @click.stop
                  />
                </div>
              </td>
              <td>{{ symbolData.mainOrder.action }}</td>
              <td>{{ symbolData.mainOrder.orderType }}</td>
              <td>{{ symbolData.mainOrder.totalQuantity }}</td>
              <td>{{ formatCurrency(symbolData.mainOrder.limitPrice) }}</td>
              <td>{{ formatCurrency(symbolData.mainOrder.stopPrice) }}</td>
              <td>{{ formatCurrency(getWeightedProfitPrice(symbolData)) }}</td>
              <td>{{ formatCurrency(getWeightedLossPrice(symbolData)) }}</td>
              <td>{{ formatCurrency(symbolData.mainOrder.currentPrice) }}</td>
              <td class="position-value">
                {{ formatCurrency(getPositionValue(symbolData)) }}
              </td>
              <td class="allocation-value">
                {{ formatPercentage(getAllocationPercent(symbolData)) }}
              </td>
              <td class="risk-value">
                {{ formatCurrency(getStopLossRisk(symbolData)) }}
              </td>
              <td class="risk-value">
                {{ formatPercentage(getStopLossPercent(symbolData)) }}
              </td>
              <td :class="getValueClass(getPotentialProfit(symbolData))">
                {{ formatCurrency(getPotentialProfit(symbolData)) }}
              </td>
              <td :class="getValueClass(getProfitPercent(symbolData))">
                {{ formatPercentage(getProfitPercent(symbolData)) }}
              </td>
              <td :class="{ 'positive-value': getRiskReward(symbolData) > 0 }">
                {{ getRiskReward(symbolData) ? getRiskReward(symbolData).toFixed(2) : '-' }}
              </td>
              <td>
                <span class="status-badge" :class="getStatusClass(symbolData.mainOrder.status)">
                  {{ symbolData.mainOrder.status }}
                </span>
              </td>
              <td>
                <OrderReasonForm 
                  :order="symbolData.mainOrder" 
                  :onReasonUpdated="handleOrderReasonUpdate" 
                  :accountBalance="accountBalance" 
                  :showButton="true"
                  :visible="false"
                  @click.stop
                />
              </td>
              <td>
                <CatalystSelector 
                  :symbol="symbolData.mainOrder.symbol" 
                  :onCatalystSelected="(catalyst) => handleCatalystSelected(symbolData.mainOrder.tradeNoteId || symbolData.mainOrder.orderId, catalyst)" 
                  :currentCatalyst="symbolData.mainOrder.catalystData"
                  @click.stop
                />
              </td>
            </tr>
            
            <!-- Render sub-orders if expanded -->
            <template v-if="symbolData.mainOrder && expandedOrders[symbolData.mainOrder.orderId]">
              <tr 
                v-for="subOrder in getSortedSubOrders(symbolData)" 
                :key="subOrder.orderId"
                class="sub-order-row"
                :class="{
                  'profit-order': isProfitSubOrder(subOrder, getPositionType(symbolData.mainOrder.symbol), symbolData.mainOrder.limitPrice),
                  'risk-order': isRiskSubOrder(subOrder, getPositionType(symbolData.mainOrder.symbol), symbolData.mainOrder.limitPrice)
                }"
              >
                <td>
                  <div class="symbol-cell sub-order-cell">
                    <span class="sub-order-indicator text-muted">⤷</span>
                    <span class="order-type-badge">
                      {{ subOrder.action }} {{ subOrder.orderType }}
                      <span v-if="isProfitSubOrder(subOrder, getPositionType(symbolData.mainOrder.symbol), symbolData.mainOrder.limitPrice)" class="order-type-icon">
                        <i class="fas fa-arrow-circle-up"></i> Target
                      </span>
                      <span v-else-if="isRiskSubOrder(subOrder, getPositionType(symbolData.mainOrder.symbol), symbolData.mainOrder.limitPrice)" class="order-type-icon">
                        <i class="fas fa-arrow-circle-down"></i> Stop
                      </span>
                    </span>
                  </div>
                </td>
                <td>{{ subOrder.action }}</td>
                <td>{{ subOrder.orderType }}</td>
                <td>{{ subOrder.totalQuantity }}</td>
                <td>{{ formatCurrency(subOrder.limitPrice) }}</td>
                <td>{{ formatCurrency(subOrder.stopPrice) }}</td>
                <td>-</td>
                <td>-</td>
                <td>{{ formatCurrency(subOrder.currentPrice) }}</td>
                <td>-</td>
                <td>-</td>
                <!-- Stop Loss Risk calculation -->
                <td v-if="isStopLossOrder(subOrder, getPositionType(symbolData.mainOrder.symbol))" class="risk-value">
                  {{ formatCurrency(calculateSubOrderStopLossRisk(subOrder, getPositionType(symbolData.mainOrder.symbol), symbolData.mainOrder)) }}
                </td>
                <td v-else>-</td>
                <!-- Stop Loss % calculation -->
                <td v-if="isStopLossOrder(subOrder, getPositionType(symbolData.mainOrder.symbol))" class="risk-value">
                  {{ formatPercentage(calculateSubOrderStopLossPercent(subOrder, getPositionType(symbolData.mainOrder.symbol), symbolData.mainOrder)) }}
                </td>
                <td v-else>-</td>
                <!-- Calculate potential profit for profit target orders -->
                <td v-if="isProfitTargetOrder(subOrder, getPositionType(symbolData.mainOrder.symbol))" 
                    :class="getValueClass(calculateSubOrderPotentialProfit(subOrder, getPositionType(symbolData.mainOrder.symbol), symbolData.mainOrder))">
                  {{ formatCurrency(calculateSubOrderPotentialProfit(subOrder, getPositionType(symbolData.mainOrder.symbol), symbolData.mainOrder)) }}
                </td>
                <td v-else>-</td>
                <!-- Calculate profit percentage for profit target orders -->
                <td v-if="isProfitTargetOrder(subOrder, getPositionType(symbolData.mainOrder.symbol))"
                    :class="getValueClass(calculateSubOrderProfitPercent(subOrder, getPositionType(symbolData.mainOrder.symbol), symbolData.mainOrder))">
                  {{ formatPercentage(calculateSubOrderProfitPercent(subOrder, getPositionType(symbolData.mainOrder.symbol), symbolData.mainOrder)) }}
                </td>
                <td v-else>-</td>
                <td>-</td>
                <td>
                  <span class="status-badge" :class="getStatusClass(subOrder.status)">
                    {{ subOrder.status }}
                  </span>
                </td>
                <td></td>
                <td></td>
              </tr>
            </template>
          </template>

          <tr v-if="newPositionsBySymbol.length === 0">
            <td colspan="19" class="empty-table">
              <a-empty description="No new position orders found" />
            </td>
          </tr>
          
          <!-- Total row for stop loss risk -->
          <tr v-if="newPositionsBySymbol.length > 0" class="total-row">
            <td colspan="9" class="total-label text-left">Total:</td>
            <td class="total-value">{{ formatCurrency(totalPositionValue) }}</td>
            <td class="total-value">{{ formatPercentage(totalAllocationPercent) }}</td>
            <td class="risk-value text-danger">{{ formatCurrency(totalStopLossRisk) }}</td>
            <td class="risk-value text-danger">{{ formatPercentage(totalRiskPercent) }}</td>
            <td class="total-value text-success">{{ formatCurrency(totalPotentialProfit) }}</td>
            <td colspan="5"></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { defineComponent } from 'vue'
import {
  Empty,
  Switch,
} from 'ant-design-vue'
import {
  DownOutlined,
  RightOutlined,
} from '@ant-design/icons-vue'
import OrderReasonForm from './OrderReasonForm.vue'
import CatalystSelector from './CatalystSelector.vue'
import { 
  formatCurrency, 
  formatPercentage, 
  getValueClass, 
  getStatusClass,
  isProfitOrder,
  isRiskOrder,
  getSortedOrders
} from '../utils/orderUtils'
import {
  getTargetPrice,
  getStopPrice
} from '../utils/priceCalculations'
import {
  saveOrderChecklistToLocalStorage,
  saveOrderCatalystToLocalStorage
} from '../utils/localStorageUtils'

export default defineComponent({
  name: 'NewPositionOrdersTable',
  components: {
    AEmpty: Empty,
    ASwitch: Switch,
    DownOutlined,
    RightOutlined,
    OrderReasonForm,
    CatalystSelector
  },
  props: {
    newPositionsBySymbol: {
      type: Array,
      default: () => []
    },
    expandedOrders: {
      type: Object,
      default: () => ({})
    },
    accountBalance: {
      type: Number,
      default: 100000
    },
    totalPositionValue: {
      type: Number,
      default: 0
    },
    totalAllocationPercent: {
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
    totalPotentialProfit: {
      type: Number,
      default: 0
    },
    // Calculation functions
    getPositionType: {
      type: Function,
      required: true
    },
    getPositionValue: {
      type: Function,
      required: true
    },
    getAllocationPercent: {
      type: Function,
      required: true
    },
    getStopLossRisk: {
      type: Function,
      required: true
    },
    getStopLossPercent: {
      type: Function,
      required: true
    },
    getPotentialProfit: {
      type: Function,
      required: true
    },
    getProfitPercent: {
      type: Function,
      required: true
    },
    getRiskReward: {
      type: Function,
      required: true
    },
    // Event handlers
    toggleExpand: {
      type: Function,
      required: true
    },
    togglePositionType: {
      type: Function,
      required: true
    },
    handleOrderReasonUpdate: {
      type: Function,
      required: true
    },
    handleCatalystSelected: {
      type: Function,
      required: true
    }
  },
  setup(props) {
    // Local wrapper for handleOrderReasonUpdate to also save to localStorage
    const handleLocalOrderReasonUpdate = (orderId, completed, reasonData) => {
      // Save to localStorage using utility function
      saveOrderChecklistToLocalStorage(orderId, completed, reasonData);
      
      // Call parent handler to update state
      props.handleOrderReasonUpdate(orderId, completed, reasonData);
    };

    // Local wrapper for handleCatalystSelected to also save to localStorage
    const handleLocalCatalystSelected = (orderId, catalyst) => {
      // Save catalyst to localStorage using utility function
      saveOrderCatalystToLocalStorage(orderId, catalyst);
      
      // Call parent handler to update state
      props.handleCatalystSelected(orderId, catalyst);
    };
    
    // Determine if an order is a stop loss order based on position type and order details
    const isStopLossOrder = (order, isShort) => {
      // Find main order from symbolData context
      const mainOrder = findMainOrderForSubOrder(order);
      if (!mainOrder) return false;
      
      const entryPrice = mainOrder.limitPrice;
      const orderPrice = order.stopPrice || order.limitPrice;
      
      if (!entryPrice || !orderPrice) return false;
      
      // For Long positions: SELL orders with price below entry are stop losses
      // For Short positions: BUY orders with price above entry are stop losses
      if (isShort) {
        return order.action.toUpperCase() === 'BUY' && 
              (order.orderType.toUpperCase() === 'STP' || 
              (order.orderType.toUpperCase() === 'LMT' && orderPrice > entryPrice));
      } else {
        return order.action.toUpperCase() === 'SELL' && 
              (order.orderType.toUpperCase() === 'STP' || 
              (order.orderType.toUpperCase() === 'LMT' && orderPrice < entryPrice));
      }
    };
    
    // Determine if an order is a profit target order based on position type and order details
    const isProfitTargetOrder = (order, isShort) => {
      // Find main order from symbolData context
      const mainOrder = findMainOrderForSubOrder(order);
      if (!mainOrder) return false;
      
      const entryPrice = mainOrder.limitPrice;
      if (!entryPrice || !order.limitPrice) return false;
      
      // For Long positions: SELL LMT orders with price above entry are profit targets
      // For Short positions: BUY LMT orders with price below entry are profit targets
      if (isShort) {
        return order.action.toUpperCase() === 'BUY' && 
               order.orderType.toUpperCase() === 'LMT' && 
               order.limitPrice < entryPrice;
      } else {
        return order.action.toUpperCase() === 'SELL' && 
               order.orderType.toUpperCase() === 'LMT' && 
               order.limitPrice > entryPrice;
      }
    };
    
    // Helper function for determining profit target orders using common utils
    const isProfitSubOrder = (order, isShort, entryPrice) => {
      if (!order.limitPrice || !entryPrice) return false;
      
      // Same logic as isProfitTargetOrder but uses entryPrice directly
      if (isShort) {
        return order.action.toUpperCase() === 'BUY' && 
              order.orderType.toUpperCase() === 'LMT' && 
              order.limitPrice < entryPrice;
      } else {
        return order.action.toUpperCase() === 'SELL' && 
              order.orderType.toUpperCase() === 'LMT' && 
              order.limitPrice > entryPrice;
      }
    };
    
    // Helper function for determining risk orders using common utils
    const isRiskSubOrder = (order, isShort, entryPrice) => {
      if (!entryPrice) return false;
      const orderPrice = order.stopPrice || order.limitPrice;
      if (!orderPrice) return false;
      
      // Same logic as isStopLossOrder but uses entryPrice directly
      if (isShort) {
        return order.action.toUpperCase() === 'BUY' && 
              (order.orderType.toUpperCase() === 'STP' || 
              (order.orderType.toUpperCase() === 'LMT' && orderPrice > entryPrice));
      } else {
        return order.action.toUpperCase() === 'SELL' && 
              (order.orderType.toUpperCase() === 'STP' || 
              (order.orderType.toUpperCase() === 'LMT' && orderPrice < entryPrice));
      }
    };
    
    // Helper function to sort sub-orders
    const getSortedSubOrders = (symbolData) => {
      const activeSubOrders = getActiveSubOrders(symbolData.subOrders);
      if (activeSubOrders.length === 0) return [];
      
      const isShort = props.getPositionType(symbolData.mainOrder.symbol);
      const entryPrice = symbolData.mainOrder.limitPrice;
      const currentPrice = symbolData.mainOrder.currentPrice || entryPrice;
      
      // Prepare orders for sorting without breaking references
      // We'll only add currentPrice if needed but won't create new objects
      activeSubOrders.forEach(order => {
        if (!order.currentPrice) {
          order.currentPrice = currentPrice;
        }
      });
      
      // Use the shared utility function for consistent sorting
      // But create a new array to avoid mutating the original
      return [...getSortedOrders(activeSubOrders, isShort, currentPrice)];
    };
    
    // Calculate stop loss risk for sub orders
    const calculateSubOrderStopLossRisk = (order, isShort, mainOrder = null) => {
      if (!order.stopPrice && !order.limitPrice) return null;
      
      // Use provided mainOrder or find it
      const entryOrder = mainOrder || findMainOrderForSubOrder(order);
      if (!entryOrder) return null;
      
      const entryPrice = entryOrder.limitPrice;
      const effectivePrice = order.stopPrice || order.limitPrice;
      
      // For long positions: only SELL orders with price below entry are stop losses
      // For short positions: only BUY orders with price above entry are stop losses
      if (isShort) {
        if (order.action.toUpperCase() === 'BUY' && effectivePrice > entryPrice) {
          return (effectivePrice - entryPrice) * order.totalQuantity;
        }
      } else {
        if (order.action.toUpperCase() === 'SELL' && effectivePrice < entryPrice) {
          return (entryPrice - effectivePrice) * order.totalQuantity;
        }
      }
      return null;
    };
    
    // Calculate stop loss percent for sub orders
    const calculateSubOrderStopLossPercent = (order, isShort, mainOrder = null) => {
      if (!order.stopPrice && !order.limitPrice) return null;
      
      // Use provided mainOrder or find it
      const entryOrder = mainOrder || findMainOrderForSubOrder(order);
      if (!entryOrder) return null;
      
      const entryPrice = entryOrder.limitPrice;
      const effectivePrice = order.stopPrice || order.limitPrice;
      
      // For long positions: only SELL orders with price below entry are stop losses
      // For short positions: only BUY orders with price above entry are stop losses
      if (isShort) {
        if (order.action.toUpperCase() === 'BUY' && effectivePrice > entryPrice) {
          return ((effectivePrice - entryPrice) / entryPrice) * 100;
        }
      } else {
        if (order.action.toUpperCase() === 'SELL' && effectivePrice < entryPrice) {
          return ((entryPrice - effectivePrice) / entryPrice) * 100;
        }
      }
      return null;
    };
    
    // Calculate potential profit for profit target orders
    const calculateSubOrderPotentialProfit = (order, isShort, mainOrder = null) => {
      if (!order.limitPrice) return null;
      
      // Use provided mainOrder or find it
      const entryOrder = mainOrder || findMainOrderForSubOrder(order);
      if (!entryOrder) return null;
      
      const entryPrice = entryOrder.limitPrice;
      
      // For long positions: only SELL LMT orders with price above entry are profit targets
      // For short positions: only BUY LMT orders with price below entry are profit targets
      if (isShort) {
        if (order.action.toUpperCase() === 'BUY' && order.orderType.toUpperCase() === 'LMT' && order.limitPrice < entryPrice) {
          return (entryPrice - order.limitPrice) * order.totalQuantity;
        }
      } else {
        if (order.action.toUpperCase() === 'SELL' && order.orderType.toUpperCase() === 'LMT' && order.limitPrice > entryPrice) {
          return (order.limitPrice - entryPrice) * order.totalQuantity;
        }
      }
      return null;
    };
    
    // Calculate profit percentage for profit target orders
    const calculateSubOrderProfitPercent = (order, isShort, mainOrder = null) => {
      if (!order.limitPrice) return null;
      
      // Use provided mainOrder or find it
      const entryOrder = mainOrder || findMainOrderForSubOrder(order);
      if (!entryOrder) return null;
      
      const entryPrice = entryOrder.limitPrice;
      
      // For long positions: only SELL LMT orders with price above entry are profit targets
      // For short positions: only BUY LMT orders with price below entry are profit targets
      if (isShort) {
        if (order.action.toUpperCase() === 'BUY' && order.orderType.toUpperCase() === 'LMT' && order.limitPrice < entryPrice) {
          return ((entryPrice - order.limitPrice) / entryPrice) * 100;
        }
      } else {
        if (order.action.toUpperCase() === 'SELL' && order.orderType.toUpperCase() === 'LMT' && order.limitPrice > entryPrice) {
          return ((order.limitPrice - entryPrice) / entryPrice) * 100;
        }
      }
      return null;
    };
    
    // Use existing utility functions for weighted prices
    const getWeightedProfitPrice = (symbolData) => {
      return getTargetPrice(symbolData, props.getPositionType);
    };
    
    const getWeightedLossPrice = (symbolData) => {
      return getStopPrice(symbolData, props.getPositionType);
    };
    
    // Helper function to find the main order for a sub-order
    const findMainOrderForSubOrder = (subOrder) => {
      for (const symbolData of props.newPositionsBySymbol) {
        if (symbolData.symbol === subOrder.symbol && symbolData.subOrders.includes(subOrder)) {
          return symbolData.mainOrder;
        }
      }
      return null;
    };
    
    // Filter out sub-orders with PendingCancel status
    const getActiveSubOrders = (subOrders) => {
      return subOrders.filter(order => order.status !== 'PendingCancel');
    };
    
    return {
      formatCurrency,
      formatPercentage,
      getValueClass,
      getStatusClass,
      isStopLossOrder,
      isProfitTargetOrder,
      isProfitSubOrder,
      isRiskSubOrder,
      calculateSubOrderStopLossRisk,
      calculateSubOrderStopLossPercent,
      calculateSubOrderPotentialProfit,
      calculateSubOrderProfitPercent,
      getActiveSubOrders,
      findMainOrderForSubOrder,
      getSortedSubOrders,
      getWeightedProfitPrice,
      getWeightedLossPrice,
      handleOrderReasonUpdate: handleLocalOrderReasonUpdate,
      handleCatalystSelected: handleLocalCatalystSelected
    }
  }
})
</script>

<style scoped>
/* Only minimal global styles needed for the container */
/* All component-specific styles have been moved to their respective sub-components */

/* Import all the existing table styles */
.section-title {
  font-size: 16px;
  font-weight: 500;
  color: #e0e0e0;
  margin-bottom: 10px;
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

.stock-table th, 
.stock-table td {
  padding: 10px;
  border-bottom: 1px solid #3a3a3a;
  text-align: left;
}

.stock-table thead th {
  background-color: #1c1c1c;
  color: #a0a0a0;
  font-weight: normal;
}

.stock-table tbody td {
  border-bottom: 1px solid #2a2a2a;
  color: #e0e0e0;
}

.stock-table tbody tr:hover td {
  background-color: #2a2a2a;
}

.stock-table tfoot th {
  background-color: #2a2a2a;
  color: #e0e0e0;
  font-weight: bold;
  border-top: 1px solid #4a6cf7;
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

/* Add new styles for profit/risk orders */
.sub-order-row.profit-order {
  background-color: rgba(76, 175, 80, 0.05);
  border-left: 3px solid #4caf50;
}

.sub-order-row.risk-order {
  background-color: rgba(244, 67, 54, 0.05);
  border-left: 3px solid #f44336;
}

.profit-order .order-type-badge {
  background-color: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.risk-order .order-type-badge {
  background-color: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

/* New styles for order type icons */
.order-type-icon {
  font-size: 10px;
  margin-left: 4px;
}
</style>