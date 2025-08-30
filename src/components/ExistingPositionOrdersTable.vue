<template>
  <div>
    <!-- Existing Positions - Exit Orders -->
    <div class="section-title">Existing Positions - Exit Orders</div>
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
          <tr v-for="order in exitPositionOrdersProcessed" :key="order.orderId">
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
            <td>{{ formatCurrency(order.limitPrice) }}</td>
            <td>{{ formatCurrency(order.stopPrice) }}</td>
            <td>{{ formatCurrency(order.currentPrice) }}</td>
            <td>{{ formatCurrency(order.stopLossRisk) }}</td>
            <td class="risk-value">
              {{ formatPercentage(getStopLossPercentForOrder(order)) }}
            </td>
            <td :class="getValueClass(calculatePotentialProfit(order))">
              {{ formatCurrency(calculatePotentialProfit(order)) }}
            </td>
            <td :class="getValueClass(calculateProfitPercent(order))">
              {{ formatPercentage(calculateProfitPercent(order)) }}
            </td>
            <td :class="{ 'positive-value': calculateRiskReward(order) > 0 }">
              {{ calculateRiskReward(order) ? calculateRiskReward(order).toFixed(2) : '-' }}
            </td>
            <td>
              <span class="status-badge" :class="getStatusClass(order.status)">
                {{ order.status }}
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
                :onCatalystSelected="(catalyst) => handleCatalystSelected(order.tradeNoteId || order.orderId, catalyst)" 
                :currentCatalyst="order.catalystData"
              />
            </td>
          </tr>
          <tr v-if="exitPositionOrdersProcessed.length === 0">
            <td colspan="15" class="empty-table">
              <a-empty description="No existing position orders found" />
            </td>
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
import OrderReasonForm from './OrderReasonForm.vue'
import CatalystSelector from './CatalystSelector.vue'
import { formatCurrency, formatPercentage, getStatusClass, getValueClass } from '../utils/orderUtils'

export default defineComponent({
  name: 'ExistingPositionOrdersTable',
  components: {
    AEmpty: Empty,
    ASwitch: Switch,
    OrderReasonForm,
    CatalystSelector
  },
  props: {
    exitPositionOrdersProcessed: {
      type: Array,
      default: () => []
    },
    accountBalance: {
      type: Number,
      default: 100000
    },
    // Calculation functions
    getPositionType: {
      type: Function,
      required: true
    },
    getStopLossPercentForOrder: {
      type: Function,
      required: true
    },
    // Event handlers
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
    // Calculate potential profit for an exit order
    const calculatePotentialProfit = (order) => {
      if (!order || !order.limitPrice || !order.matchedHolding) return null;
      
      const holding = order.matchedHolding;
      const isShort = props.getPositionType(order.symbol);
      const entryPrice = holding.entryPrice || holding.averagePrice;
      
      if (!entryPrice) return null;
      
      const quantity = order.totalQuantity;
      
      if (isShort) {
        // For short positions, profit is entry price minus exit price
        return (entryPrice - order.limitPrice) * quantity;
      } else {
        // For long positions, profit is exit price minus entry price
        return (order.limitPrice - entryPrice) * quantity;
      }
    };
    
    // Calculate profit percentage for an exit order
    const calculateProfitPercent = (order) => {
      if (!order || !order.limitPrice || !order.matchedHolding) return null;
      
      const holding = order.matchedHolding;
      const isShort = props.getPositionType(order.symbol);
      const entryPrice = holding.entryPrice || holding.averagePrice;
      
      if (!entryPrice) return null;
      
      if (isShort) {
        // For short positions, profit % is (entry - exit) / entry
        return ((entryPrice - order.limitPrice) / entryPrice) * 100;
      } else {
        // For long positions, profit % is (exit - entry) / entry
        return ((order.limitPrice - entryPrice) / entryPrice) * 100;
      }
    };
    
    // Calculate risk/reward ratio for an exit order
    const calculateRiskReward = (order) => {
      if (!order || !order.stopPrice || !order.limitPrice || !order.matchedHolding) return null;
      
      const holding = order.matchedHolding;
      const isShort = props.getPositionType(order.symbol);
      const entryPrice = holding.entryPrice || holding.averagePrice;
      
      if (!entryPrice) return null;
      
      let profit, risk;
      
      if (isShort) {
        // For short positions
        profit = entryPrice - order.limitPrice;
        risk = order.stopPrice - entryPrice;
      } else {
        // For long positions
        profit = order.limitPrice - entryPrice;
        risk = entryPrice - order.stopPrice;
      }
      
      if (risk <= 0) return null; // Invalid risk
      
      return Math.abs(profit / risk);
    };
    
    return {
      formatCurrency,
      formatPercentage,
      getStatusClass,
      getValueClass,
      calculatePotentialProfit,
      calculateProfitPercent,
      calculateRiskReward
    }
  }
})
</script>

<style scoped>
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

.status-default {
  background-color: rgba(158, 158, 158, 0.2);
  color: #9e9e9e;
}

/* Risk values */
.risk-value {
  font-weight: 500;
  color: #f44336;
}

/* Value classes */
.positive-value {
  color: #4caf50;
}

.negative-value {
  color: #f44336;
}
</style>