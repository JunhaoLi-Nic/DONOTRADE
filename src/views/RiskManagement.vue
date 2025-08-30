<template>
  <div class="content-container">
    <div class="page-title">
      <h1>Risk Management</h1>
    </div>
    
    <!-- Loading spinner -->
    <SpinnerLoadingPage v-if="loading && stockHoldings.length === 0" text="Loading positions..." />
    
    <!-- Account Summary and Controls -->
    <div class="card">
      <div class="card-header">
        <div class="title">Account Summary</div>
        <div class="actions">
          <button 
            class="btn btn-secondary" 
            @click="handleRefreshPositions(false)"
            :disabled="loading"
          >
            <i class="fa fa-refresh"></i>
            Refresh Positions
          </button>
          <button 
            class="btn btn-primary" 
            @click="handleRefreshPositions(true)"
            :disabled="loading"
          >
            <i class="fa fa-refresh"></i>
            Refresh Prices
          </button>
          <button 
            class="btn btn-success ms-2" 
            @click="loadDummyData"
            :disabled="loading"
          >
            <i class="fa fa-play"></i>
            Try Demo Data
          </button>
        </div>
      </div>
      
      <div class="card-body">
        <!-- Error message -->
        <div v-if="error" class="error-message mb-3">
          <div class="message-container">
            <div class="icon">
              <i class="fa fa-exclamation-triangle"></i>
            </div>
            <div class="message">
              {{ error }}
            </div>
          </div>
        </div>
        
        <div v-if="loading && stockHoldings.length === 0" class="text-center py-4">
          <i class="fa fa-spinner fa-spin me-2"></i>
          Loading account data...
        </div>
        <risk-controls
          v-else
          :account-data="accountData"
          :stock-holdings="stockHoldings"
          @max-drawdown-change="handleMaxDrawdownChange"
          @risk-per-trade-change="handleRiskPerTradeChange"
          @max-expected-stop-loss-percent-change="handleMaxExpectedStopLossPercentChange"
        />
      </div>
    </div>
    
    <!-- Stock Holdings Table -->
    <div class="card">
      <div class="card-header">
        <div class="title">Current Holdings & Exit Orders</div>
      </div>
      
      <div class="card-body">
        <div v-if="loading && stockHoldings.length === 0" class="text-center py-4">
          <i class="fa fa-spinner fa-spin me-2"></i>
          Loading positions...
        </div>
        <stock-holdings-table
          v-else
          :key="refreshKey"
          :stock-holdings="stockHoldings"
          :loading="loading"
          :account-data="accountData"
          :exit-position-orders="exitPositionOrders"
          @refresh="handleRefreshPositions"
          @update:totalRisk="handleTotalRiskUpdate"
          :hideRefreshButton="true"
        />
      </div>
    </div>
    
    <!-- Open Orders Table -->
    <div class="card">
      <div class="card-header">
        <div class="title">Open Orders</div>
        <div class="actions">
          <button 
            class="btn btn-secondary" 
            @click="handleRefreshOrders"
            :disabled="ordersLoading"
          >
            <i class="fa fa-refresh"></i>
            Refresh Orders
          </button>
        </div>
      </div>
      
      <div class="card-body">
        <open-orders-table
          :key="refreshKey"
          :open-orders="openOrders"
          :loading="ordersLoading"
          :error="ordersError"
          :account-balance="accountData.balance"
          :stock-holdings="stockHoldings"
          :holdings-stop-loss-risk="totalHoldingsStopLossRisk"
          @refresh="handleRefreshPositions"
          @orders-updated="handleOrdersUpdated"
          :hideRefreshButton="true"
        />
      </div>
    </div>
    
    <!-- Previous Buy Orders Table -->
    <div class="card">
      <div class="card-header">
        <div class="title">Previous Buy Orders</div>
      </div>
      
      <div class="card-body">
        <previous-buy-orders-table
          :open-orders="openOrders"
          :account-balance="accountData.balance"
          :stock-holdings="stockHoldings"
          @order-canceled="handlePreviousOrderCanceled"
          :hideRefreshButton="true"
        />
      </div>
    </div>

    <!-- Portfolio correlation coefficient-->
    <div class="card">
      <div class="card-header">
        <div class="title"> Correlation Coefficient</div>
      </div>

      <div class="card-body">
        <CorrelationCoefficient
        :stockholdings="stockHoldings.map(pos => pos.name)"
        />
      </div>
    </div>
    
    <!-- Order Checklist Table -->
    <div class="card">
      <div class="card-header">
        <div class="title">Order Checklist</div>
      </div>
      
      <div class="card-body">
        <order-checklist-table
          :orders="openOrders"
          :loading="ordersLoading"
        />
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, watch, onMounted, onBeforeUnmount, computed } from 'vue';
import axios from '../config/api'; // Import axios from our configured file
import { pageId } from '../stores/globals';
import { API_PREFIX, IBKR_ENDPOINTS } from '../config/api';
import { positionTypes, detectPositionType } from '../utils/positionUtils';
import { calculateStopLosses, calculateRiskExposure, riskParameters } from '../utils/riskUtils';

// Import components
import SpinnerLoadingPage from '../components/SpinnerLoadingPage.vue';
import StockHoldingsTable from '../components/StockHoldingsTable.vue';
import OpenOrdersTable from '../components/OpenOrdersTable.vue';
import PreviousBuyOrdersTable from '../components/PreviousBuyOrdersTable.vue';
import RiskControls from '../components/RiskControls.vue';
import OrderChecklistTable from '../components/OrderChecklistTable.vue';
import CorrelationCoefficient from '../components/CorrelationCoefficient.vue';

export default {
  name: 'RiskManagement',
  components: {
    CorrelationCoefficient,
    SpinnerLoadingPage,
    StockHoldingsTable,
    OpenOrdersTable,
    PreviousBuyOrdersTable,
    RiskControls,
    OrderChecklistTable
  },
  // a specific function that runs before the compoennt is created and rendered
  setup() {
    // Set pageId for sidebar highlighting
    pageId.value = 'riskmanagement';

    // Add a refresh key to force re-render
    const refreshKey = ref(0);
    
    /**
     * Structure of `pos` (position) object:
     * {
     *   symbol: string,           // Ticker symbol, e.g. "AAPL"
     *   shares: number,           // Number of shares held
     *   value: number,            // Market value of the position (shares * currentPrice)
     *   currentPrice: number,     // Current market price per share
     *   entryPrice: number,       // Average entry price per share
     *   profitLoss: number,       // Total P&L for this position
     *   allocation: number|null,  // % of portfolio (set in code)
     *   targetPrice: number|null, // Target price from open orders (set in code)
     *   stopLoss: number|null,    // Stop loss price from open orders (set in code)
     *   percentToTarget: number|null, // % to target from current price (set in code)
     *   percentToStop: number|null,   // % to stop from current price (set in code)
     *   expectedStopLoss: number|null, // Calculated stop loss price based on risk (set in code)
     *   expectedStopLossPercent: number|null, // % drop to expected stop loss (set in code)
     *   riskRewardRatio: number|null // Calculated risk/reward (set in code)
     *   // ...other broker-specific fields may be present
     * }
     */

    // State
    const accountData = reactive({
      name: "Trading Account",
      balance: 0,
      maxDrawdown: riskParameters.maxDrawdown,
      riskPerTrade: riskParameters.riskPerTrade,  // Default 1% risk per trade
      maxExpectedStopLossPercent: riskParameters.maxExpectedStopLossPercent,
      totalProfitLoss: 0,
      totalProfitLossPercent: 0
    });

    const stockHoldings = ref([]);
    const openOrders = ref([]);
    const loading = ref(true);
    const error = ref(null);
    const ordersLoading = ref(true);
    const ordersError = ref(null);

    // Function to manually refresh orders
    const handleRefreshOrders = async () => {
      ordersLoading.value = true;
      ordersError.value = null;
      try {
        const response = await axios.get(IBKR_ENDPOINTS.OPEN_ORDERS, {
          timeout: 30000,
          params: { _t: new Date().getTime() }
        });

        if (response.data && Array.isArray(response.data)) {
          openOrders.value = response.data;
          ordersLoading.value = false;
          ordersError.value = null;
          refreshKey.value++;
        }
      } catch (err) {
        console.error('Error fetching orders:', err);
        ordersError.value = 'Failed to load orders. Please try again.';
        ordersLoading.value = false;
      }
    };

    // Silent refresh function for automated updates
    const silentRefresh = async () => {
      try {
        const response = await axios.get(IBKR_ENDPOINTS.OPEN_ORDERS, {
          timeout: 30000,
          params: { _t: new Date().getTime() }
        });

        if (response.data && Array.isArray(response.data)) {
          openOrders.value = response.data;
          ordersLoading.value = false;
          ordersError.value = null;
        }

        return true;
      } catch (err) {
        console.error('Silent refresh failed:', err);
        // Don't set error state for silent refreshes to avoid UI disruption
        return false;
      }
    };

    // Risk calculations are now handled by the riskUtils module

    // Handle orders updated from the OpenOrdersTable component
    const handleOrdersUpdated = (updatedOrders) => {
      if (updatedOrders && Array.isArray(updatedOrders)) {
        openOrders.value = updatedOrders;
      }
    };
    
    // Handle when an order is canceled in the PreviousBuyOrdersTable component
    const handlePreviousOrderCanceled = (orderId) => {
      console.log(`Order ${orderId} was canceled`);
      // Refresh orders to ensure the UI is up to date
      silentRefresh();
    };

    // Function to load dummy data directly
    const loadDummyData = async () => {
      loading.value = true;
      error.value = null;
      
      try {
        console.log("Loading dummy data...");
        const response = await axios.get(IBKR_ENDPOINTS.POSITIONS, { 
          params: { 
            use_dummy: false 
          }  
        });
        
        //console.log("Dummy data loaded:", response.data);
        
        // Process the response data
        const { account, positions, openOrders: ordersData } = response.data;
        
        // Update account data
        accountData.name = account.name;
        accountData.balance = account.balance;
        
        // Set stock holdings
        stockHoldings.value = positions;
        
        // Set open orders
        if (Array.isArray(ordersData)) {
          openOrders.value = ordersData;
          ordersLoading.value = false;
        }
        
      } catch (err) {
        console.error('Error loading dummy data:', err);
        error.value = 'Failed to load dummy data. Please try again.';
      } finally {
        loading.value = false;
      }
    };

    // Function to manually refresh positions with new prices
    const handleRefreshPositions = async (refreshPrices = false) => {
      loading.value = true;
      error.value = null;
      console.log("Refreshing positions with refreshPrices =", refreshPrices);
      
      try {
        let apiCalls = [];
        
        // Add a timestamp to create a unique request each time
        const timestamp = new Date().getTime();
        
        // First call: Get positions with refreshed prices
        console.log(`Calling API: ${IBKR_ENDPOINTS.POSITIONS} with refresh=${refreshPrices}`);
        const positionsPromise = axios.get(IBKR_ENDPOINTS.POSITIONS, { 
          timeout: 30000,
          params: { 
            _t: timestamp,
            refresh: refreshPrices, // This refreshes position prices
            force_refresh: refreshPrices, // Add an alternative parameter name
            use_dummy: false 
          }  
        });
        apiCalls.push(positionsPromise);
        
        // If explicitly refreshing prices, refresh orders too and reset price service timer
        if (refreshPrices) {
          // Also refresh orders with fresh prices
          console.log("Also refreshing orders with fresh prices");
          const ordersPromise = axios.get(IBKR_ENDPOINTS.OPEN_ORDERS, {
            timeout: 30000,
            params: { 
              _t: timestamp,
              refresh: true,  // Explicitly request price refresh
              force_refresh: true // Add an alternative parameter name
            }
          });
          apiCalls.push(ordersPromise);
          
          // If we have access to the priceService, reset its timer
          try {
            const priceService = require('../services/priceService').default;
            if (priceService && typeof priceService.resetFetchTimer === 'function') {
              priceService.resetFetchTimer();
              console.log("Reset price service fetch timer");
            }
          } catch (e) {
            console.log("Could not reset price service timer:", e);
          }
        }
        
        // Wait for all API calls to complete
        const results = await Promise.all(apiCalls);
        const positionsResponse = results[0];
        
        console.log("API response:", positionsResponse.data);
        
        // Process the positions response data
        const { account, positions, openOrders: ordersData } = positionsResponse.data;
        
        // Calculate total value and profit/loss from positions with prices
        const positionsWithPrices = positions.filter(pos => pos.currentPrice !== null);
        const totalValue = positionsWithPrices.reduce((sum, pos) => sum + pos.value, 0);
        const totalProfitLoss = positionsWithPrices.reduce((sum, pos) => sum + pos.profitLoss, 0);
        const profitLossPercent = totalValue > totalProfitLoss ? 
          (totalProfitLoss / (totalValue - totalProfitLoss)) * 100 : 0;

        // Calculate combined balance
        const combinedBalance = account.balance + totalValue;

        // Set open orders directly from the response
        if (Array.isArray(ordersData)) {
          openOrders.value = ordersData;
          ordersLoading.value = false;
          ordersError.value = null;
        }
        
        // If we explicitly refreshed orders, use that response
        if (refreshPrices && results.length > 1) {
          const ordersResponse = results[1];
          if (ordersResponse.data && Array.isArray(ordersResponse.data)) {
            openOrders.value = ordersResponse.data;
            ordersLoading.value = false;
            ordersError.value = null;
          }
        }

        // We'll update positions with order data when orders are available
        const positionsWithPercentages = positions.map(pos => {
          const allocation = pos.value !== null && combinedBalance > 0 ? 
            (pos.value / combinedBalance) * 100 : null;
            
          return {
            ...pos,
            allocation: allocation !== null ? allocation : null,
            targetPrice: null,
            stopLoss: null,
            percentToTarget: null,
            percentToStop: null,
            expectedStopLoss: null,
            expectedStopLossPercent: null,
            riskRewardRatio: null
          };
        });

        // Update account data with combined balance
        accountData.balance = combinedBalance;
        accountData.totalProfitLoss = totalProfitLoss;
        accountData.totalProfitLossPercent = profitLossPercent;
        
        // Calculate stop losses using new balances from the riskUtils module
        const holdingsWithStopLosses = calculateStopLosses(
          positionsWithPercentages, 
          accountData.maxDrawdown, 
          accountData.riskPerTrade,
          accountData.balance
        );
        
        // Apply position type detection to each holding
        holdingsWithStopLosses.forEach(position => {
          // Only set default position type if not already manually set
          if (!positionTypes.hasOwnProperty(position.symbol)) {
            // Initial detection
            const isShort = detectPositionType(position);
            if (isShort) {
              console.log(`Position ${position.symbol} detected as SHORT with shares: ${position.shares}`);
              positionTypes[position.symbol] = true;
            } else {
              console.log(`Position ${position.symbol} detected as LONG with shares: ${position.shares}`);
            }
          }
        });
        
        console.log("Processed positions:", holdingsWithStopLosses);
        
        // Update positions with calculated percentages and stop losses
        stockHoldings.value = holdingsWithStopLosses;
        
        // CRITICAL FIX: Explicitly update positions with order data to ensure calculations are performed
        updatePositionsWithOrderData();
        
        // Increment refresh key to force component re-render
        refreshKey.value++;
        
        // If refreshing prices, inform the user
        if (refreshPrices) {
          // Show toast or notification
          console.log("Prices refreshed successfully");
        }
        
      } catch (err) {
        console.error('Error fetching positions:', err);
        if (err.response) {
          console.error('Response status:', err.response.status);
          console.error('Response data:', err.response.data);
        }
        error.value = 'Failed to load positions. Please check your connection to the broker.';
      } finally {
        loading.value = false;
      }
    };

    // Update positions when orders change
    const updatePositionsWithOrderData = () => {
      if (stockHoldings.value.length === 0 || openOrders.value.length === 0) return;
      
      const updatedHoldings = stockHoldings.value.map(pos => {
        // Find all open orders for this symbol
        const symbolOrders = openOrders.value.filter(order => order.symbol === pos.symbol);
        // If any BUY order exists for a long position, or any SELL order for a short position, 
        // these are likely adding to the position, not exits
        const isShort = positionTypes[pos.symbol] || (pos.strategy === 'short');
        const hasAddingOrder = isShort 
          ? symbolOrders.some(order => order.action === 'SELL' && order.orderType === 'LMT')
          : symbolOrders.some(order => order.action === 'BUY' && order.orderType === 'LMT');
        
        let targetPrice = null;
        let stopLoss = null;
        let riskRewardRatio = null;
        
        if (!hasAddingOrder) {
          if (isShort) {
            // For short positions
            // Find BUY LMT orders below entry price for targetPrice (profit targets)
            const targetOrders = symbolOrders.filter(order => 
              order.action === 'BUY' && 
              order.orderType === 'LMT' && 
              order.limitPrice < pos.entryPrice
            );
            
            if (targetOrders.length > 0) {
              if (targetOrders.length === 1) {
                targetPrice = targetOrders[0].limitPrice;
              } else {
                // Calculate weighted average for multiple target orders
                let totalQuantity = 0;
                let weightedSum = 0;
                
                targetOrders.forEach(order => {
                  const qty = order.totalQuantity || 0;
                  totalQuantity += qty;
                  weightedSum += (order.limitPrice * qty);
                });
                
                targetPrice = totalQuantity > 0 ? weightedSum / totalQuantity : null;
              }
            }
            
            // Find BUY STP orders for stopLoss
            let stopOrders = symbolOrders.filter(order => 
              order.action === 'BUY' && order.orderType === 'STP'
            );
            
            // If no STP orders, look for BUY LMT orders above entry price (potential stops)
            if (stopOrders.length === 0) {
              stopOrders = symbolOrders.filter(order => 
                order.action === 'BUY' && 
                order.orderType === 'LMT' && 
                order.limitPrice > pos.entryPrice
              );
            }
            
            if (stopOrders.length > 0) {
              if (stopOrders.length === 1) {
                stopLoss = stopOrders[0].stopPrice || stopOrders[0].limitPrice;
              } else {
                // Calculate weighted average for multiple stop orders
                let totalQuantity = 0;
                let weightedSum = 0;
                
                stopOrders.forEach(order => {
                  const qty = order.totalQuantity || 0;
                  totalQuantity += qty;
                  weightedSum += ((order.stopPrice || order.limitPrice) * qty);
                });
                
                stopLoss = totalQuantity > 0 ? weightedSum / totalQuantity : null;
              }
            }
          } else {
            // For long positions
            // Find SELL LMT orders above entry price for targetPrice (profit targets)
            const targetOrders = symbolOrders.filter(order => 
              order.action === 'SELL' && 
              order.orderType === 'LMT' && 
              order.limitPrice > pos.entryPrice
            );
            
            if (targetOrders.length > 0) {
              if (targetOrders.length === 1) {
                targetPrice = targetOrders[0].limitPrice;
              } else {
                // Calculate weighted average for multiple target orders
                let totalQuantity = 0;
                let weightedSum = 0;
                
                targetOrders.forEach(order => {
                  const qty = order.totalQuantity || 0;
                  totalQuantity += qty;
                  weightedSum += (order.limitPrice * qty);
                });
                
                targetPrice = totalQuantity > 0 ? weightedSum / totalQuantity : null;
              }
            }
            
            // Find SELL STP orders for stopLoss
            let stopOrders = symbolOrders.filter(order => 
              order.action === 'SELL' && order.orderType === 'STP'
            );
            
            // If no STP orders, look for SELL LMT orders below entry price (potential stops)
            if (stopOrders.length === 0) {
              stopOrders = symbolOrders.filter(order => 
                order.action === 'SELL' && 
                order.orderType === 'LMT' && 
                order.limitPrice < pos.entryPrice
              );
            }
            
            if (stopOrders.length > 0) {
              if (stopOrders.length === 1) {
                stopLoss = stopOrders[0].stopPrice || stopOrders[0].limitPrice;
              } else {
                // Calculate weighted average for multiple stop orders
                let totalQuantity = 0;
                let weightedSum = 0;
                
                stopOrders.forEach(order => {
                  const qty = order.totalQuantity || 0;
                  totalQuantity += qty;
                  weightedSum += ((order.stopPrice || order.limitPrice) * qty);
                });
                
                stopLoss = totalQuantity > 0 ? weightedSum / totalQuantity : null;
              }
            }
          }
          
          // Calculate risk/reward if we have both target and stop
          if (targetPrice && stopLoss && pos.entryPrice) {
            if (isShort) {
              riskRewardRatio = Math.abs((pos.entryPrice - targetPrice) / (stopLoss - pos.entryPrice));
            } else {
              riskRewardRatio = Math.abs((targetPrice - pos.entryPrice) / (pos.entryPrice - stopLoss));
            }
          }
        }
        
        // Calculate percentages based on position type
        let percentToTarget = null;
        let percentToStop = null;
        
        if (targetPrice && pos.currentPrice) {
          percentToTarget = isShort 
            ? ((pos.currentPrice - targetPrice) / pos.currentPrice) * 100  // Short: target is below current
            : ((targetPrice - pos.currentPrice) / pos.currentPrice) * 100; // Long: target is above current
        }
        
        if (stopLoss && pos.currentPrice) {
          percentToStop = isShort
            ? ((stopLoss - pos.currentPrice) / pos.currentPrice) * 100     // Short: stop is above current
            : ((pos.currentPrice - stopLoss) / pos.currentPrice) * 100;    // Long: stop is below current
        }
        
        return {
          ...pos,
          targetPrice,
          stopLoss,
          percentToTarget,
          percentToStop,
          riskRewardRatio
        };
      });
      
      stockHoldings.value = updatedHoldings;
    };

    // Handle risk parameter changes
    const handleMaxDrawdownChange = (value) => {
      if (value !== null) {
        accountData.maxDrawdown = value;
        
        // Use riskUtils module calculateStopLosses function
        const updatedHoldings = calculateStopLosses(
          stockHoldings.value, 
          value, 
          accountData.riskPerTrade, 
          accountData.balance
        );
        
        stockHoldings.value = updatedHoldings;
      }
    };

    const handleRiskPerTradeChange = (value) => {
      if (value !== null) {
        accountData.riskPerTrade = value;
        
        // Use riskUtils module calculateStopLosses function
        const updatedHoldings = calculateStopLosses(
          stockHoldings.value, 
          accountData.maxDrawdown, 
          value, 
          accountData.balance
        );
        
        stockHoldings.value = updatedHoldings;
      }
    };

    const handleMaxExpectedStopLossPercentChange = (value) => {
      if (value !== null) {
        accountData.maxExpectedStopLossPercent = value;
        
        // Update the riskParameters in riskUtils
        riskParameters.maxExpectedStopLossPercent = value;
        
        // Recalculate risk exposure with new parameter
        updatePositionsWithOrderData();
      }
    };

    const totalHoldingsStopLossRisk = ref(0);

    const handleTotalRiskUpdate = (value) => {
      totalHoldingsStopLossRisk.value = value;
    };

    // Filter exit position orders (orders that close existing positions)
    const exitPositionOrders = computed(() => {
      if (!openOrders.value || !stockHoldings.value) return [];
      
      return openOrders.value.filter(order => {
        // Find if there's a matching holding for this symbol
        const matchingHolding = stockHoldings.value.find(holding => holding.symbol === order.symbol);
        if (!matchingHolding) return false;
        
        // Determine if this order would reduce the position
        const isShort = detectPositionType(matchingHolding);
        const isExitOrder = (isShort && order.action === 'BUY') || (!isShort && order.action === 'SELL');
        
        return isExitOrder;
      });
    });

    // Setup on component mount
    onMounted(async () => {
      // Initial fetch
      await handleRefreshPositions();
      
      // Set up polling for positions every 5 minutes (300000ms)
      const positionsInterval = setInterval(() => handleRefreshPositions(), 300000);
      
      // Set up polling for orders every 5 minutes
      const ordersInterval = setInterval(silentRefresh, 300000);
      
      // Store intervals for cleanup
      intervals.positionsInterval = positionsInterval;
      intervals.ordersInterval = ordersInterval;
    });
    
    // Track intervals for cleanup
    const intervals = {
      positionsInterval: null,
      ordersInterval: null
    };
    
    // Cleanup on component unmount
    onBeforeUnmount(() => {
      if (intervals.positionsInterval) clearInterval(intervals.positionsInterval);
      if (intervals.ordersInterval) clearInterval(intervals.ordersInterval);
    });
    
    // Watch for changes to orders to update positions
    // Use deep equality check and prevent cascading API calls
    watch(openOrders, (newOrders, oldOrders) => {
      // Skip if the arrays are the same length and have the same order IDs
      // This prevents unnecessary updates that can trigger API call loops
      if (oldOrders && 
          newOrders.length === oldOrders.length && 
          JSON.stringify(newOrders.map(o => o.orderId).sort()) === 
          JSON.stringify(oldOrders.map(o => o.orderId).sort())) {
        return;
      }
      
      // Only update position data, don't trigger any API calls
      updatePositionsWithOrderData();
    }, { deep: true });

    return {
      accountData,
      stockHoldings,
      openOrders,
      exitPositionOrders,
      loading,
      error,
      ordersLoading,
      ordersError,
      totalHoldingsStopLossRisk,
      handleRefreshPositions,
      handleRefreshOrders,
      handleMaxDrawdownChange,
      handleRiskPerTradeChange,
      handleMaxExpectedStopLossPercentChange,
      handleOrdersUpdated,
      handlePreviousOrderCanceled,
      handleTotalRiskUpdate,
      loadDummyData,
      refreshKey
    };
  }
}
</script>

<style scoped>
.content-container {
  padding: 20px;
  max-width: 100%;
  background-color: #121212;
  color: #e0e0e0;
  min-height: 100vh;
}

.page-title {
  margin-bottom: 20px;
  color: #ffffff;
}

.card {
  background-color: #1e1e1e;
  border-radius: 5px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
  margin-bottom: 20px;
  overflow: hidden;
  border: 1px solid #2a2a2a;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background-color: #2a2a2a;
  border-bottom: 1px solid #3a3a3a;
}

.card-header .title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #ffffff;
}

.card-header .actions {
  display: flex;
  gap: 10px;
}

.card-body {
  padding: 20px;
  color: #e0e0e0;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: none;
}

.btn i {
  margin-right: 5px;
}

.btn-primary {
  background-color: #4a6cf7;
  color: white;
}

.btn-secondary {
  background-color: #5c636a;
  color: white;
}

.btn-success {
  background-color: #2ea043;
  color: white;
}

.btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.error-message {
  background-color: rgba(220, 53, 69, 0.2);
  color: #f8d7da;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
  border: 1px solid rgba(220, 53, 69, 0.3);
}

.error-message .message-container {
  display: flex;
  align-items: center;
}

.error-message .icon {
  margin-right: 10px;
  font-size: 1.5rem;
  color: #dc3545;
}

/* Add styles for loading indicators */
.text-center {
  text-align: center;
}

.py-4 {
  padding-top: 1.5rem;
  padding-bottom: 1.5rem;
}

/* Tabs styling for the catalyst manager */
:deep(.nav-tabs) {
  border-bottom-color: #3a3a3a;
}

:deep(.nav-link) {
  color: #e0e0e0;
}

:deep(.nav-link.active) {
  background-color: transparent;
  border-color: #3a3a3a #3a3a3a #1e1e1e;
  color: #4a6cf7;
}

:deep(.tab-content) {
  background-color: #1e1e1e;
  color: #e0e0e0;
}

:deep(table) {
  color: #e0e0e0;
}

:deep(table thead th) {
  border-bottom-color: #3a3a3a;
  background-color: #2a2a2a;
}

:deep(table tbody td) {
  border-top-color: #3a3a3a;
}
</style>