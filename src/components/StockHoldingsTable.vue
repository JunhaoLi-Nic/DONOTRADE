<template>
  <div>
    <!-- Loading or no data state -->
    <div v-if="loading && stockHoldings.length === 0" class="loading">
      Loading positions...
    </div>
    <div v-else-if="stockHoldings.length === 0" class="no-data">
      <NoData>
        <template #description>
          <div class="no-holdings-message">
            <p>No current holdings found</p>
            <p class="no-holdings-sub">Position data will appear here when you have open positions</p>
          </div>
        </template>
      </NoData>
    </div>
    
    <!-- Table view when data is available -->
    <div v-else class="table-container">
      <!-- Add refresh button -->
      <div class="table-header">
        <div class="header-title">
          <h3>Current Holdings & Exit Orders</h3>
          <div v-if="stockHoldings.length > 0" class="position-count-badge">
            {{ stockHoldings.length }} position{{ stockHoldings.length > 1 ? 's' : '' }}
          </div>
          <div v-if="totalExitOrders > 0" class="exit-count-badge">
            {{ totalExitOrders }} exit order{{ totalExitOrders > 1 ? 's' : '' }}
          </div>
        </div>
        <div class="header-actions">
          <!-- Only show refresh button when not in RiskManagement view -->
          <button 
            v-if="!hideRefreshButton"
            class="refresh-btn"
            @click="handleRefreshPrices"
            :disabled="refreshLoading"
          >
            <span v-if="!refreshLoading">
              <i class="fas fa-sync-alt"></i>
            </span>
            <span v-else class="loading-spinner">
              <i class="fas fa-spinner fa-spin"></i>
            </span>
            Refresh Prices
          </button>
        </div>
      </div>

        <table class="positions-table">
          <thead>
            <tr>
              <th class="text-left symbol-col">Symbol</th>
              <th class="text-left type-col">Type</th>
              <th class="text-right shares-col">Shares</th>
              <th class="text-right price-col">Entry</th>
              <th class="text-right price-col">Current</th>
              <th class="text-right price-col">Target</th>
              <th class="text-right percent-col">% to Target</th>
              <th class="text-right value-col">Potential Profit</th>
              <th class="text-right price-col">Stop Loss</th>
              <th class="text-right percent-col">% to Stop</th>
              <th class="text-right risk-col">Risk ($)</th>
              <!-- New columns -->
              <th class="text-right risk-col">Expected Risk($)</th>
              <th class="text-right price-col">Expected Stop Loss</th>
              <th class="text-right percent-col">Expected SL %</th>
              <!-- End new columns -->
              <th class="text-right ratio-col">R:R</th>
              <th class="text-right value-col">Value</th>
              <th class="text-right percent-col">Allocation</th>
              <th class="text-right pnl-col">P/L</th>
              <th class="text-right percent-col">P/L %</th>
              <th class="text-left source-col">Source</th>
            </tr>
          </thead>
          <tbody>
            <!-- Loop through positions -->
            <template v-for="position in sortedPositions" :key="position.symbol">
              <!-- Main position row -->
              <tr 
                @click="position.exitOrders.length > 0 ? toggleExpand(position.symbol) : null" 
                class="main-position-row" 
                :class="{
                  'expandable': position.exitOrders.length > 0,
                  'expanded': expandedPositions[position.symbol]
                }"
              >
                <td class="text-left symbol-cell">
                  <div class="symbol-content">
                    <!-- Only show expand icon if there are exit orders -->
                    <span v-if="position.exitOrders.length > 0" class="expand-icon">
                      <i class="fas fa-chevron-down" v-if="expandedPositions[position.symbol]"></i>
                      <i class="fas fa-chevron-right" v-else></i>
                    </span>
                    <div class="symbol-info">
                      <span class="symbol-name">{{ position.symbol }}</span>
                      <span v-if="position.name" class="company-name">{{ position.name }}</span>
                    </div>
                    <span v-if="position.exitOrders.length > 0" class="exit-orders-badge">
                      {{ position.exitOrders.length }}
                    </span>
                  </div>
                </td>
                <td class="text-left">
                  <div class="position-type-cell">
                    <label class="switch compact">
                      <input type="checkbox" :checked="position.isShort" @change="handleTogglePositionType(position.symbol)" @click.stop>
                      <span class="slider">
                        <span class="position-type">
                          <span v-if="position.shares > 0 && position.isShort" class="position-warning">[!]</span>
                          {{ position.isShort ? 'Short' : 'Long' }}
                        </span>
                      </span>
                    </label>
                  </div>
                </td>
                <td class="text-right">
                  <span class="shares-value">{{ formatNumber(position.shares) }}</span>
                </td>
                <td class="text-right">
                  <span class="price-value">{{ formatCurrency(position.entryPrice) }}</span>
                </td>
                <td class="text-right">
                  <span class="price-value current-price">{{ formatCurrency(position.currentPrice) }}</span>
                </td>
                <td class="text-right">
                  <span v-if="position.targetPrice" class="price-value text-success">
                    {{ formatCurrency(position.targetPrice) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right">
                  <span v-if="position.targetPrice" class="percent-value text-success">
                    {{ formatPercent(getPercentToTarget(position)) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right">
                  <span v-if="position.targetPrice" class="value-amount text-success">
                    {{ formatCurrency(calculateTargetPriceMoney(position)) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right">
                  <span v-if="position.stopLoss" 
                    class="price-value"
                    :class="{
                      'text-danger': !position.effectiveExpectedStopLoss && !position.expectedStopLoss || 
                                     (position.isShort && position.stopLoss <= (position.effectiveExpectedStopLoss || position.expectedStopLoss)) ||
                                     (!position.isShort && position.stopLoss >= (position.effectiveExpectedStopLoss || position.expectedStopLoss)),
                      'text-warning': (position.effectiveExpectedStopLoss || position.expectedStopLoss) && 
                                     (position.isShort && position.stopLoss > (position.effectiveExpectedStopLoss || position.expectedStopLoss)) ||
                                     (!position.isShort && position.stopLoss < (position.effectiveExpectedStopLoss || position.expectedStopLoss))
                    }">
                    {{ formatCurrency(position.stopLoss) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right">
                  <span v-if="position.stopLoss" 
                    class="percent-value"
                    :class="{
                      'text-danger': !position.effectiveExpectedStopLoss && !position.expectedStopLoss || 
                                     (position.isShort && position.stopLoss <= (position.effectiveExpectedStopLoss || position.expectedStopLoss)) ||
                                     (!position.isShort && position.stopLoss >= (position.effectiveExpectedStopLoss || position.expectedStopLoss)),
                      'text-warning': (position.effectiveExpectedStopLoss || position.expectedStopLoss) && 
                                     (position.isShort && position.stopLoss > (position.effectiveExpectedStopLoss || position.expectedStopLoss)) ||
                                     (!position.isShort && position.stopLoss < (position.effectiveExpectedStopLoss || position.expectedStopLoss))
                    }">
                    {{ formatPercent(getPercentToStop(position)) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right">
                  <span v-if="position.stopLoss && position.currentPrice && position.shares" class="risk-value text-danger">
                    {{ formatCurrency(calculateStopLossMoney(position)) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right">
                  <span v-if="position.stopLoss && position.currentPrice && position.shares" class="risk-value text-danger">
                    {{ formatCurrency(calculateExpectedStopLossMoney(position)) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right">
                  <span v-if="position.effectiveExpectedStopLoss || position.expectedStopLoss" class="price-value text-danger">
                    {{ formatCurrency(position.effectiveExpectedStopLoss || position.expectedStopLoss) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right">
                  <span v-if="position.effectiveExpectedStopLoss || position.expectedStopLoss" class="percent-value text-danger">
                    {{ calculateEffectiveStopLossPercent(position) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right">
                  <span v-if="position.riskRewardRatio && 
                             ((position.isShort && position.stopLoss > position.entryPrice) || 
                              (!position.isShort && position.stopLoss < position.entryPrice))" 
                        class="ratio-value"
                        :class="{ 'good-ratio': position.riskRewardRatio >= 2 }">
                    {{ position.riskRewardRatio.toFixed(1) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right">
                  <span class="value-amount">{{ formatCurrency(position.value) }}</span>
                </td>
                <td class="text-right">
                  <span v-if="position.allocation !== null" class="allocation-value">
                    {{ formatPercent(position.allocation) }}
                  </span>
                  <span v-else class="no-value">-</span>
                </td>
                <td class="text-right">
                  <span class="pnl-value" :class="getAdjustedProfitLoss(position).isPositive ? 'text-success' : 'text-danger'">
                    {{ formatCurrency(getAdjustedProfitLoss(position).value) }}
                  </span>
                </td>
                <td class="text-right">
                  <span class="pnl-percent" :class="getAdjustedProfitLoss(position).isPositive ? 'text-success' : 'text-danger'">
                    {{ formatPercent(getAdjustedProfitLoss(position).percent) }}
                  </span>
                </td>
                <td class="text-left">
                  <span class="source-text">{{ position.priceSource || '-' }}</span>
                </td>
              </tr>
              
              <!-- Exit orders rows (shown when expanded) -->
              <template v-if="position.exitOrders.length > 0 && expandedPositions[position.symbol]">
                <tr 
                  v-for="order in getSortedOrders(position.exitOrders, position.isShort, position.currentPrice)" 
                  :key="order.orderId"
                  class="exit-order-row"
                  :class="{'profit-order': isProfitOrder(order, position.isShort), 'risk-order': isRiskOrder(order, position.isShort)}"
                >
                  <td class="text-left symbol-cell">
                    <div class="exit-order-content">
                      <span class="exit-order-indicator">⤷</span>
                      <div class="order-info">
                        <span class="order-type-badge">
                          {{ order.action }} {{ order.orderType }}
                          <span v-if="isProfitOrder(order, position.isShort)" class="order-type-icon">
                            <i class="fas fa-arrow-circle-up"></i> Target
                          </span>
                          <span v-else-if="isRiskOrder(order, position.isShort)" class="order-type-icon">
                            <i class="fas fa-arrow-circle-down"></i> Stop
                          </span>
                        </span>
                        <div class="order-details">
                          <span class="order-id">ID: {{ order.orderId }}</span>
                          <span class="status-badge" :class="getOrderStatusClass(order.status)">
                            {{ order.status }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </td>
                  <td class="text-left">
                    <span class="exit-label">Exit</span>
                  </td>
                  <td class="text-right">
                    <span class="shares-value">{{ formatNumber(order.totalQuantity || 0) }}</span>
                  </td>
                  <td class="text-right">
                    <span class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span class="price-value">{{ formatCurrency(order.currentPrice) }}</span>
                  </td>
                  <td class="text-right">
                    <span v-if="order.limitPrice" class="price-value target-price">
                      {{ formatCurrency(order.limitPrice) }}
                    </span>
                    <span v-else class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span v-if="order.limitPrice && order.currentPrice" class="percent-value target-percent">
                      {{ formatPercent(((order.limitPrice - order.currentPrice) / order.currentPrice) * 100) }}
                    </span>
                    <span v-else class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span v-if="order.limitPrice && order.currentPrice && order.totalQuantity" class="value-amount target-price">
                      {{ formatCurrency(calculateSubOrderTargetPriceMoney(order, position.isShort)) }}
                    </span>
                    <span v-else class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span v-if="order.stopPrice" class="price-value stop-price">
                      {{ formatCurrency(order.stopPrice) }}
                    </span>
                    <span v-else class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span v-if="order.stopPrice && order.currentPrice" class="percent-value text-danger">
                      {{ position.isShort ? 
                        formatPercent(((order.stopPrice - order.currentPrice) / order.currentPrice) * 100) :
                        formatPercent(((order.currentPrice - order.stopPrice) / order.currentPrice) * 100) 
                      }}
                    </span>
                    <span v-else class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span v-if="order.stopPrice && order.currentPrice && order.totalQuantity && isRiskOrder(order, position.isShort)" class="risk-value text-danger">
                      {{ formatCurrency(calculateSubOrderStopLossMoney(order, position.isShort)) }}
                    </span>
                    <span v-else class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span class="no-value">-</span>
                  </td>
                  <td class="text-right">
                    <span class="no-value">-</span>
                  </td>
                  <td class="text-left">
                    <span class="source-text">Order</span>
                  </td>
                </tr>
              </template>
            </template>
          </tbody>
          
          <!-- Summary row -->
          <tfoot>
            <tr>
              <th class="text-left">Total/Avg:</th>
              <th></th> <!-- Type -->
              <th></th> <!-- Shares -->
              <th></th> <!-- Entry -->
              <th></th> <!-- Current -->
              <th></th> <!-- Target -->
              <th></th> <!-- % to Target -->
              <th class="text-right text-success">{{ formatCurrency(totalTargetPriceMoney) }}</th> <!-- Potential Profit -->
              <th></th> <!-- Stop Loss -->
              <th></th> <!-- % to Stop -->
              <th class="text-right text-danger">{{ formatCurrency(totalStopLossMoney) }}</th> <!-- Risk ($) -->
              <th class="text-right text-danger">{{ formatCurrency(totalExpectedStopLossMoney) }}</th> <!-- Expected Risk -->
              <th></th> <!-- Expected SL Price -->
              <th></th> <!-- Expected SL % -->
              <th></th> <!-- R:R -->
              <th class="text-right">{{ formatCurrency(totalValue) }}</th> <!-- Value -->
              <th class="text-right">{{ formatPercent(totalAllocation) }}</th> <!-- Allocation -->
              <th class="text-right" :class="accountData.totalProfitLoss >= 0 ? 'text-success' : 'text-danger'">
                {{ formatCurrency(accountData.totalProfitLoss) }}
              </th> <!-- P/L -->
              <th class="text-right" :class="accountData.totalProfitLossPercent >= 0 ? 'text-success' : 'text-danger'">
                {{ formatPercent(accountData.totalProfitLossPercent) }}
              </th> <!-- P/L % -->
              <th></th> <!-- Source -->
            </tr>
          </tfoot>
        </table>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import NoData from './NoData.vue';
import { detectPositionType, togglePositionType } from '../utils/positionUtils';
import priceService from '../services/priceService';
import executedTradeService from '../services/executedTradeService';
import { message } from 'ant-design-vue';
import { 
  formatCurrency, 
  formatPercentage, 
  getStatusClass as getOrderStatusClass, 
  isProfitOrder,
  isRiskOrder,
  getSortedOrders 
} from '../utils/orderUtils';

export default {
  name: 'StockHoldingsTable',
  components: {
    NoData
  },
  props: {
    stockHoldings: {
      type: Array,
      required: true
    },
    loading: {
      type: Boolean,
      default: false
    },
    accountData: {
      type: Object,
      required: true
    },
    hideRefreshButton: {
      type: Boolean,
      default: false
    },
    exitPositionOrders: {
      type: Array,
      default: () => []
    }
  },
  emits: ['refresh', 'update:totalRisk'],
  setup(props, { emit }) {
    // Add refreshLoading state
    const refreshLoading = ref(false);
    const tradeTrackingActive = ref(false);
    const expandedPositions = ref({});
    
    // Process executed trades when stock holdings change
    const processExecutedTrades = async () => {
      if (!props.stockHoldings || props.stockHoldings.length === 0 || tradeTrackingActive.value) {
        return;
      }
      
      try {
        console.log('Starting trade execution detection...');
        tradeTrackingActive.value = true;
        
        // Call the executed trade service to process holdings
        const result = await executedTradeService.processStockHoldings(props.stockHoldings);
        
        // Log and show notification if any trades were executed or merged
        if (result.executed.length > 0 || result.merged.length > 0) {
          console.log('Trade tracking results:', result);
          
          // Show notification for executed trades
          if (result.executed.length > 0) {
            message.success(`Detected ${result.executed.length} executed trade${result.executed.length > 1 ? 's' : ''}`);
          }
          
          // Show notification for merged trades
          if (result.merged.length > 0) {
            message.success(`Merged ${result.merged.length} position${result.merged.length > 1 ? 's' : ''}`);
          }
          
          // If any changes were made, refresh the component data
          emit('refresh', true);
        }
      } catch (error) {
        console.error('Error processing executed trades:', error);
        message.error('Error detecting executed trades');
      } finally {
        tradeTrackingActive.value = false;
      }
    };
    
    // Add refresh function
    const handleRefreshPrices = async () => {
      refreshLoading.value = true;
      try {
        // Get all symbols from holdings
        const symbols = Array.from(new Set(
          props.stockHoldings.map(holding => holding.symbol)
        ));
        
        if (symbols.length > 0) {
          // Use the price service to force refresh
          await priceService.fetchCurrentPrices(
            symbols,
            true, // Force refresh from API and backend cache
            (data) => {
              message.success(`Refreshed prices for ${Object.keys(data).length} symbols`);
            },
            (error) => {
              message.error('Failed to refresh prices');
            }
          );
          
          // Reset the price service timer for future requests
          priceService.resetFetchTimer();
          
          // Process executed trades after refreshing prices
          await processExecutedTrades();
          
          // Emit refresh event to parent to trigger a full data refresh
          emit('refresh', true);
        } else {
          message.info('No positions to refresh');
        }
      } catch (error) {
        console.error('Error refreshing stock holding prices:', error);
        message.error('Failed to refresh prices');
      } finally {
        refreshLoading.value = false;
      }
    };

    // Process executed trades when component mounts or when holdings change
    onMounted(() => {
      if (props.stockHoldings && props.stockHoldings.length > 0) {
        processExecutedTrades();
      }
    });
    
    // Watch for changes in stock holdings to detect executed trades
    watch(() => props.stockHoldings, (newHoldings, oldHoldings) => {
      if (newHoldings && newHoldings.length > 0) {
        // Check if the holdings have actually changed (either in length or content)
        const hasChanged = !oldHoldings || 
          oldHoldings.length !== newHoldings.length || 
          JSON.stringify(newHoldings) !== JSON.stringify(oldHoldings);
          
        if (hasChanged) {
          console.log('Holdings changed, checking for executed trades...');
          processExecutedTrades();
        }
      }
    }, { deep: true });
    
    // Group positions with their exit orders
    const positionsWithOrders = computed(() => {
      return [...props.stockHoldings].map(position => {
        // Find exit orders for this position
        const exitOrders = props.exitPositionOrders.filter(order => 
          order.symbol === position.symbol
        );
        
        // Determine position type
        const isShort = detectPositionType(position);
        
        // Calculate fallback target price and stop loss from exit orders if needed
        let fallbackTargetPrice = null;
        let fallbackStopLoss = null;
        
        if (exitOrders.length > 0 && (!position.targetPrice || !position.stopLoss)) {
          // Look for target price in profit orders
          const profitOrders = exitOrders.filter(order => isProfitOrder(order, isShort));
          if (profitOrders.length > 0 && !position.targetPrice) {
            // Use the "best" profit target (highest for long, lowest for short)
            fallbackTargetPrice = isShort
              ? Math.min(...profitOrders.map(order => order.limitPrice).filter(Boolean))
              : Math.max(...profitOrders.map(order => order.limitPrice).filter(Boolean));
          }
          
          // Look for stop loss in risk orders
          const riskOrders = exitOrders.filter(order => isRiskOrder(order, isShort));
          if (riskOrders.length > 0 && !position.stopLoss) {
            // Use the "worst" stop loss (lowest for long, highest for short)
            fallbackStopLoss = isShort
              ? Math.max(...riskOrders.map(order => order.stopPrice || order.limitPrice).filter(Boolean))
              : Math.min(...riskOrders.map(order => order.stopPrice || order.limitPrice).filter(Boolean));
          }
        }
        
        // Use original or fallback values
        const effectiveTargetPrice = position.targetPrice || fallbackTargetPrice;
        const effectiveStopLoss = position.stopLoss || fallbackStopLoss;
        
        // Calculate risk reward ratio if we have both target and stop loss
        let riskRewardRatio = position.riskRewardRatio;
        if (effectiveTargetPrice && effectiveStopLoss && position.entryPrice && position.currentPrice) {
          // Only calculate if we don't already have one or we're using fallbacks
          if (!riskRewardRatio || fallbackTargetPrice || fallbackStopLoss) {
            const entryToTarget = Math.abs(effectiveTargetPrice - position.entryPrice);
            const entryToStop = Math.abs(position.entryPrice - effectiveStopLoss);
            
            // Avoid division by zero
            if (entryToStop > 0) {
              riskRewardRatio = entryToTarget / entryToStop;
            }
          }
        }
        
        return {
          ...position,
          isShort,
          effectiveExpectedStopLoss: calculateEffectiveExpectedStopLoss(position),
          exitOrders,
          // Use fallbacks when needed
          targetPrice: effectiveTargetPrice,
          stopLoss: effectiveStopLoss,
          riskRewardRatio: riskRewardRatio
        };
      }).sort((a, b) => b.value - a.value);
    });

    // Toggle expand/collapse for positions with orders
    const toggleExpand = (symbol) => {
      expandedPositions.value[symbol] = !expandedPositions.value[symbol];
    };

    // Sort positions by value (largest to smallest) - maintain for backwards compatibility
    const sortedPositions = computed(() => {
      return positionsWithOrders.value;
    });
    
    // Calculate effective expected stop loss using the smaller of:
    // 1. Current expected stop loss
    // 2. Max expected stop loss percentage of position value
    const calculateEffectiveExpectedStopLoss = (position) => {
      // If no max percentage set in accountData, use default expected stop loss
      if (!props.accountData.maxExpectedStopLossPercent || !position.currentPrice) {
        return position.expectedStopLoss;
      }
      
      const isShort = detectPositionType(position);
      const maxAllowedPercentStopLoss = props.accountData.maxExpectedStopLossPercent;
      
      // Calculate max allowed stop loss price based on percentage
      let maxAllowedStopLossPrice;
      if (isShort) {
        // For shorts: stop loss is above current price
        maxAllowedStopLossPrice = position.currentPrice * (1 + maxAllowedPercentStopLoss / 100);
      } else {
        // For longs: stop loss is below current price
        maxAllowedStopLossPrice = position.currentPrice * (1 - maxAllowedPercentStopLoss / 100);
      }
      
      // Original expected stop loss (may be null)
      const originalExpectedStopLoss = position.expectedStopLoss;
      
      // Return the less risky (closer to current price) stop loss
      if (!originalExpectedStopLoss) {
        return maxAllowedStopLossPrice;
      }
      
      if (isShort) {
        // For shorts: lower stop loss price is better
        return Math.min(originalExpectedStopLoss, maxAllowedStopLossPrice);
      } else {
        // For longs: higher stop loss price is better
        return Math.max(originalExpectedStopLoss, maxAllowedStopLossPrice);
      }
    };
    
    // Calculate total value
    const totalValue = computed(() => {
      return props.stockHoldings.reduce((sum, pos) => sum + (pos.value || 0), 0);
    });
    
    // Calculate total allocation
    const totalAllocation = computed(() => {
      return props.stockHoldings.reduce((sum, pos) => sum + (pos.allocation || 0), 0);
    });

    // Calculate total exit orders
    const totalExitOrders = computed(() => {
      return sortedPositions.value.reduce((sum, pos) => sum + (pos.exitOrders?.length || 0), 0);
    });
    
    // Calculate weighted average target price
    const avgTargetPrice = computed(() => {
      const positions = props.stockHoldings.filter(pos => pos.targetPrice && pos.value);
      if (positions.length === 0) return null;
      
      const totalValue = positions.reduce((sum, pos) => sum + pos.value, 0);
      const weightedSum = positions.reduce((sum, pos) => sum + (pos.targetPrice * pos.value), 0);
      
      return totalValue > 0 ? weightedSum / totalValue : null;
    });
    
    // Calculate weighted average stop loss
    const avgStopLoss = computed(() => {
      const positions = props.stockHoldings.filter(pos => pos.stopLoss && pos.value);
      if (positions.length === 0) return null;
      
      const totalValue = positions.reduce((sum, pos) => sum + pos.value, 0);
      const weightedSum = positions.reduce((sum, pos) => sum + (pos.stopLoss * pos.value), 0);
      
      return totalValue > 0 ? weightedSum / totalValue : null;
    });
    
    // Calculate weighted average expected stop loss
    const avgExpectedSL = computed(() => {
      const processedPositions = sortedPositions.value;
      const positions = processedPositions.filter(pos => pos.effectiveExpectedStopLoss && pos.value);
      if (positions.length === 0) return null;
      
      const totalValue = positions.reduce((sum, pos) => sum + pos.value, 0);
      const weightedSum = positions.reduce((sum, pos) => sum + (pos.effectiveExpectedStopLoss * pos.value), 0);
      
      return totalValue > 0 ? weightedSum / totalValue : null;
    });
    
    // Handle position type toggle
    const handleTogglePositionType = (symbol) => {
      togglePositionType(symbol);
    };

    // Calculate adjusted P/L based on position type
    const getAdjustedProfitLoss = (position) => {
      if (!position.profitLoss) return { value: 0, isPositive: false };
      
      // For short positions, properly calculate P/L percentage
      if (position.isShort) {
        // For short positions, P/L is positive when price goes down
        // No need to adjust the actual value, just make sure the display logic is correct
        let percentValue = position.profitLossPercent;
        
        // If the system already inverted the sign, we keep it as is
        // If not, we need to correct it based on actual profit/loss direction
        const priceDirection = position.entryPrice && position.currentPrice ? 
          position.entryPrice - position.currentPrice : 0;
        
        // Check if sign needs correction
        const signMismatch = (priceDirection > 0 && position.profitLoss < 0) || 
                            (priceDirection < 0 && position.profitLoss > 0);
        
        if (signMismatch && position.profitLossPercent) {
          // Flip the sign if there's a mismatch
          percentValue = -position.profitLossPercent;
        }
        
        return { 
          value: position.profitLoss, 
          percent: percentValue,
          // For shorts: profit is positive when the value is positive
          isPositive: position.profitLoss > 0
        };
      }
      
      // For long positions, keep as is
      return { 
        value: position.profitLoss, 
        percent: position.profitLossPercent,
        isPositive: position.profitLoss > 0
      };
    };
    
    // Get correct % to target based on position type
    const getPercentToTarget = (position) => {
      if (!position.targetPrice || !position.currentPrice) return null;
      
      if (position.isShort) {
        // For short: target is below current price
        return ((position.currentPrice - position.targetPrice) / position.currentPrice) * 100;
      }
      
      // Use existing percentToTarget or calculate for long
      return position.percentToTarget || 
        ((position.targetPrice - position.currentPrice) / position.currentPrice) * 100;
    };
    
    // Get correct % to stop based on position type
    const getPercentToStop = (position) => {
      if (!position.stopLoss || !position.currentPrice) return null;
      
      if (position.isShort) {
        // For short: stop is above current price
        return ((position.stopLoss - position.currentPrice) / position.currentPrice) * 100;
      }
      
      // Use existing percentToStop or calculate for long
      return position.percentToStop || 
        ((position.currentPrice - position.stopLoss) / position.currentPrice) * 100;
    };
    
    // Format utilities - use imported utilities instead
    const formatPercent = (value) => {
      if (value === null || value === undefined) return '-';
      return new Intl.NumberFormat('en-US', { 
        style: 'percent',
        minimumFractionDigits: 1,
        maximumFractionDigits: 1
      }).format(value / 100);
    };

    const formatNumber = (value) => {
      if (value === null || value === undefined) return '-';
      return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(Math.abs(value));
    };
    
    // Calculate expected stop loss in money
    const calculateExpectedStopLossMoney = (position) => {
      if (position.shares === 0 || !position.currentPrice) return null;
      
      // Use the effective stop loss (considering max percentage limit)
      const effectiveStopLoss = position.effectiveExpectedStopLoss || position.expectedStopLoss;
      if (!effectiveStopLoss) return null;
      
      const absShares = Math.abs(position.shares);
      const isShort = position.isShort;
      
      if (isShort) {
        // For short positions: risk is when price goes up to stop loss
        return (effectiveStopLoss - position.currentPrice) * absShares;
      } else {
        // For long positions: risk is when price goes down to stop loss
        return (position.currentPrice - effectiveStopLoss) * absShares;
      }
    };
    
    // Calculate total expected stop loss in money
    const totalExpectedStopLossMoney = computed(() => {
      // Sum risk from main positions
      const mainPositionsRisk = sortedPositions.value.reduce((sum, pos) => {
        const slMoney = calculateExpectedStopLossMoney(pos);
        return sum + (slMoney || 0);
      }, 0);
      
      return mainPositionsRisk;
    });
    
    // Calculate stop loss for sub-orders
    const calculateSubOrderStopLossMoney = (order, isShort) => {
      if (!order.stopPrice || !order.currentPrice || !order.totalQuantity) return null;
      
      if (isShort) {
        // For short positions with BUY STP orders
        if (order.action.toUpperCase() === 'BUY') {
          // Risk is when stop price is above current price
          return (order.stopPrice - order.currentPrice) * order.totalQuantity;
        }
      } else {
        // For long positions with SELL STP orders
        if (order.action.toUpperCase() === 'SELL') {
          // Risk is when stop price is below current price
          return (order.currentPrice - order.stopPrice) * order.totalQuantity;
        }
      }
      return null;
    };
    
    // Calculate stop loss in money
    const calculateStopLossMoney = (position) => {
      if (!position.stopLoss || !position.currentPrice) return null;
      
      const absShares = Math.abs(position.shares);
      const isShort = position.isShort;
      
      if (isShort) {
        // For short positions: risk is when price goes up to stop loss
        return (position.stopLoss - position.currentPrice) * absShares;
      } else {
        // For long positions: risk is when price goes down to stop loss
        return (position.currentPrice - position.stopLoss) * absShares;
      }
    };
    
    // Calculate total stop loss in money
    const totalStopLossMoney = computed(() => {
      return sortedPositions.value.reduce((sum, pos) => {
        let positionRisk = 0;
        const riskOrders = pos.exitOrders.filter(order => isRiskOrder(order, pos.isShort));

        if (riskOrders.length > 0) {
          // If there are risk orders, sum their risk
          positionRisk = riskOrders.reduce((orderSum, order) => {
            const risk = calculateSubOrderStopLossMoney(order, pos.isShort);
            return orderSum + (risk || 0);
          }, 0);
        } else {
          // Otherwise, use the main position's stop loss
          positionRisk = calculateStopLossMoney(pos) || 0;
        }
        
        return sum + positionRisk;
      }, 0);
    });

    watch(totalStopLossMoney, (newValue) => {
      emit('update:totalRisk', newValue);
    }, { immediate: true });

    const totalTargetPrice = computed(() => {
      return props.stockHoldings.reduce((sum, pos) => {
        return sum + (pos.targetPrice || 0);
      }, 0);
    });
    
    // Calculate effective stop loss percent
    const calculateEffectiveStopLossPercent = (position) => {
      if (!position.currentPrice) return formatPercent(0);
      
      const effectiveStopLoss = position.effectiveExpectedStopLoss;
      if (!effectiveStopLoss) {
        return position.expectedStopLossPercent ? formatPercent(position.expectedStopLossPercent) : '-';
      }
      
      const isShort = position.isShort;
      let percent;
      
      if (isShort) {
        // For short positions: risk when price goes up
        percent = ((effectiveStopLoss - position.currentPrice) / position.currentPrice) * 100;
      } else {
        // For long positions: risk when price goes down
        percent = ((position.currentPrice - effectiveStopLoss) / position.currentPrice) * 100;
      }
      
      return formatPercent(percent);
    };
    
    // Calculate target price in money
    const calculateTargetPriceMoney = (position) => {
      if (!position.targetPrice || !position.currentPrice || !position.shares) return null;
      
      const absShares = Math.abs(position.shares);
      const isShort = position.isShort;
      
      if (isShort) {
        // For short positions: profit when price goes down
        return (position.currentPrice - position.targetPrice) * absShares;
      } else {
        // For long positions: profit when price goes up
        return (position.targetPrice - position.currentPrice) * absShares;
      }
    };
    
    // Calculate potential profit for exit/sub orders
    const calculateSubOrderTargetPriceMoney = (order, isShort) => {
      if (!order.limitPrice || !order.currentPrice || !order.totalQuantity) return null;
      
      if (isShort) {
        // For short positions with BUY orders
        if (order.action.toUpperCase() === 'BUY') {
          // Profit is when exit price is below current price
          return (order.currentPrice - order.limitPrice) * order.totalQuantity;
        }
      } else {
        // For long positions with SELL orders
        if (order.action.toUpperCase() === 'SELL') {
          // Profit is when exit price is above current price
          return (order.limitPrice - order.currentPrice) * order.totalQuantity;
        }
      }
      return null;
    };
    
    // Calculate total target price in money
    const totalTargetPriceMoney = computed(() => {
      // Sum potential profit from main positions
      const mainPositionsProfit = sortedPositions.value.reduce((sum, pos) => {
        const targetMoney = calculateTargetPriceMoney(pos);
        return sum + (targetMoney || 0);
      }, 0);
      
      return mainPositionsProfit;
    });

    return {
      refreshLoading,
      handleRefreshPrices,
      processExecutedTrades,
      sortedPositions,
      expandedPositions,
      toggleExpand,
      totalValue,
      totalAllocation,
      totalExitOrders,
      avgTargetPrice,
      avgStopLoss,
      avgExpectedSL,
      totalExpectedStopLossMoney,
      totalStopLossMoney,
      totalTargetPrice,
      totalTargetPriceMoney,
      handleTogglePositionType,
      getAdjustedProfitLoss,
      getPercentToTarget,
      getPercentToStop,
      formatCurrency,
      formatPercent,
      formatNumber,
      calculateExpectedStopLossMoney,
      calculateStopLossMoney,
      calculateSubOrderStopLossMoney,
      calculateTargetPriceMoney,
      calculateSubOrderTargetPriceMoney,
      calculateEffectiveStopLossPercent,
      getOrderStatusClass,
      getSortedOrders,
      isProfitOrder,
      isRiskOrder
    };
  }
};
</script>

<style scoped>
.table-container {
  width: 100%;
  overflow-x: auto;
  margin-bottom: 24px;
}

.positions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.positions-table th, 
.positions-table td {
  padding: 10px;
  border-bottom: 1px solid #3a3a3a;
  text-align: left;
}

.positions-table thead th {
  background-color: #1c1c1c;
  color: #a0a0a0;
  font-weight: normal;
}

.positions-table tbody td {
  border-bottom: 1px solid #2a2a2a;
  color: #e0e0e0;
}

.positions-table tbody tr:hover td {
  background-color: #2a2a2a;
}

.positions-table tfoot th {
  background-color: #2a2a2a;
  color: #e0e0e0;
  font-weight: bold;
  border-top: 1px solid #4a6cf7;
}

.text-left {
  text-align: left;
}

.text-right {
  text-align: right;
}

.text-success {
  color: #4caf50;
}

.text-danger {
  color: #f44336;
}

.text-warning {
  color: #ffc107;
}

.no-data {
  text-align: center;
  padding: 30px 0;
  color: #a0a0a0;
}

.loading {
  text-align: center;
  padding: 30px 0;
  color: #a0a0a0;
}

.no-holdings-message {
  text-align: center;
}

.no-holdings-message p {
  margin: 0;
  color: #a0a0a0;
}

.no-holdings-sub {
  font-size: 12px;
  margin-top: 4px !important;
  color: #666 !important;
}

/* Position warning indicator */
.position-warning {
  color: #ff9800;
  font-weight: bold;
  margin-right: 4px;
}

/* Switch styles */
.position-type-cell {
  display: flex;
  align-items: center;
}

.switch {
  position: relative;
  display: inline-block;
  width: 70px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #2a2a2a;
  border: 1px solid #4a6cf7;
  border-radius: 24px;
  transition: .3s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 2px;
  background-color: #4a6cf7;
  border-radius: 50%;
  transition: .3s;
}

input:checked + .slider {
  background-color: #2a2a2a;
}

input:checked + .slider:before {
  transform: translateX(46px);
}

.position-type {
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  transition: .3s;
  position: relative;
  z-index: 1;
}

input:not(:checked) + .slider .position-type {
  margin-left: 10px;
  color: #4caf50;
}

input:checked + .slider .position-type {
  margin-right: 10px;
  color: #f44336;
}

/* Add styles for the table header and refresh button */
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

.position-count-badge {
  background-color: rgba(74, 108, 247, 0.2);
  color: #4a6cf7;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.exit-count-badge {
  background-color: rgba(255, 152, 0, 0.2);
  color: #ff9800;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.refresh-btn {
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

.refresh-btn:hover {
  background-color: #3a5cd8;
}

.refresh-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.loading-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
}

/* Collapsible holdings styling */
.main-position-row.expandable {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.main-position-row.expandable:hover {
  background-color: #333333;
}

.main-position-row.expanded {
  background-color: #2a2a2a;
  border-bottom: none;
}

.exit-order-row {
  background-color: #1a1a1a;
  border-left: 3px solid #4a6cf7;
}

.exit-order-row.profit-order {
  background-color: rgba(76, 175, 80, 0.05);
  border-left: 3px solid #4caf50;
}

.exit-order-row.risk-order {
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

.exit-order-row:hover {
  background-color: #222222;
}

.exit-order-cell {
  padding-left: 20px;
}

.expand-icon {
  display: inline-flex;
  width: 16px;
  height: 16px;
  margin-right: 8px;
  align-items: center;
  justify-content: center;
  color: #a0a0a0;
}

.expanded .expand-icon {
  color: #4a6cf7;
}

.exit-order-indicator {
  font-size: 12px;
  color: #a0a0a0;
  font-style: italic;
  margin-right: 8px;
}

.symbol-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.exit-orders-badge {
  background-color: rgba(74, 108, 247, 0.2);
  color: #4a6cf7;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.order-type-badge {
  background-color: rgba(255, 152, 0, 0.2);
  color: #ff9800;
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 500;
  margin-right: 6px;
}

.order-quantity {
  font-size: 12px;
  color: #a0a0a0;
  font-style: italic;
}

/* Status badges for orders */
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

.text-info {
  color: #2196f3;
}

/* Optimized cell content styling */
.symbol-content {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.symbol-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.symbol-name {
  font-weight: 600;
  font-size: 14px;
  color: #fff;
}

.company-name {
  font-size: 11px;
  color: #a0a0a0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
}

.exit-orders-badge {
  background-color: rgba(74, 108, 247, 0.2);
  color: #4a6cf7;
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 600;
  min-width: 16px;
  text-align: center;
}

.switch.compact {
  width: 60px;
  height: 20px;
}

.switch.compact .slider {
  border-radius: 20px;
}

.switch.compact .slider:before {
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 2px;
}

.switch.compact input:checked + .slider:before {
  transform: translateX(40px);
}

.switch.compact .position-type {
  font-size: 11px;
}

/* Value formatting */
.shares-value, .price-value, .percent-value, .risk-value, .ratio-value, 
.value-amount, .allocation-value, .pnl-value, .pnl-percent {
  font-weight: 500;
}

.current-price {
  font-weight: 600;
  color: #fff;
}

.no-value {
  color: #666;
  font-style: italic;
}

.good-ratio {
  color: #4caf50;
  font-weight: 600;
}

.source-text {
  font-size: 11px;
  color: #a0a0a0;
}

.exit-label {
  font-size: 11px;
  color: #ff9800;
  font-weight: 500;
  text-transform: uppercase;
}

/* Exit order styling */
.exit-order-content {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 12px;
}

.order-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.order-details {
  display: flex;
  align-items: center;
  gap: 8px;
}

.order-id {
  font-size: 10px;
  color: #a0a0a0;
  font-family: monospace;
}

.order-type-badge {
  background-color: rgba(255, 152, 0, 0.2);
  color: #ff9800;
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
}

.target-price {
  color: #4caf50;
}

.target-percent {
  color: #4caf50;
}

.stop-price {
  color: #f44336;
}

.stop-percent {
  color: #f44336;
}

/* New styles for order type icons */
.order-type-icon {
  font-size: 10px;
  margin-left: 4px;
}
</style> 