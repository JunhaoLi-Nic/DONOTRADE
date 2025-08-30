/**
 * OpenOrdersTable.vue
 * 
 * Parent component that coordinates the display of open orders using various sub-components.
 * This component was refactored from a monolithic component into a coordinating container
 * that delegates rendering to specialized sub-components:
 * - OrderTableHeader: Displays the header with refresh/save/load controls
 * - NewPositionOrdersTable: Displays orders for new positions with collapsible rows
 * - RiskSummary: Displays the total risk metrics
 * 
 * Note: Exit position orders are now integrated into the StockHoldingsTable component
 * in the RiskManagement view for a unified trading experience.
 * 
 * The component manages shared state and provides calculation functions to its children.
 */
<template>
  <div>
    <!-- Header component -->
    <OrderTableHeader 
      :ordersNeedingPrices="ordersNeedingPrices"
      :totalStopLossRisk="totalStopLossRisk"
      :totalRiskPercent="totalRiskPercent"
      :hideRefreshButton="hideRefreshButton"
      :priceLoading="priceLoading"
      :saveLoading="saveLoading"
      :loadLoading="loadLoading"
      :handleRefreshPrices="handleRefreshPrices"
      :saveOrdersToMongoDB="saveOrdersToMongoDB"
      :loadOrdersFromMongoDB="loadOrdersFromMongoDB"
    />

    <!-- New Position Orders Table -->
    <NewPositionOrdersTable 
      :newPositionsBySymbol="newPositionsBySymbol"
      :expandedOrders="expandedOrders"
      :accountBalance="accountBalance"
      :totalPositionValue="totalPositionValue"
      :totalAllocationPercent="totalAllocationPercent"
      :totalStopLossRisk="totalStopLossRisk"
      :totalRiskPercent="totalRiskPercent"
      :totalPotentialProfit="totalPotentialProfit"
      :getPositionType="getPositionType"
      :getPositionValue="getPositionValue"
      :getAllocationPercent="getAllocationPercent"
      :getStopLossRisk="getStopLossRisk"
      :getStopLossPercent="getStopLossPercent"
      :getPotentialProfit="getPotentialProfit"
      :getProfitPercent="getProfitPercent"
      :getRiskReward="getRiskReward"
      :toggleExpand="toggleExpand"
      :togglePositionType="togglePositionType"
      :handleOrderReasonUpdate="handleOrderReasonUpdate"
      :handleCatalystSelected="handleCatalystSelected"
    />

    <!-- Exit position orders are now integrated into the Holdings table in RiskManagement view -->

    <!-- Risk Summary component -->
    <RiskSummary 
      :totalStopLossRisk="totalStopLossRisk"
      :holdingsStopLossRisk="holdingsStopLossRisk"
    />
  </div>
</template>

<script>
import { defineComponent, reactive, computed, watch } from 'vue';
import { message } from 'ant-design-vue';
import OrderTableHeader from './OrderTableHeader.vue';
import NewPositionOrdersTable from './NewPositionOrdersTable.vue';
import RiskSummary from './RiskSummary.vue';
import { positionTypes as appPositionTypes } from '../utils/positionUtils';
import { detectIfMainOrder } from '../utils/detectmain';
import holdingsMatchService from '../services/holdingsMatchService';
import priceService from '../services/priceService';
import { 
  clearOrderDataFromLocalStorage, 
  applyLocalStorageToOrdersState 
} from '../utils/localStorageUtils';

// Import services and utility functions
import orderTableService from '../services/orderTableService';
import { getTargetPrice as getTargetPriceUtil, getStopPrice as getStopPriceUtil } from '../utils/priceCalculations';
import { 
  getStopLossRisk as getStopLossRiskUtil, 
  getStopLossPercent as getStopLossPercentUtil, 
  getPotentialProfit as getPotentialProfitUtil, 
  getProfitPercent as getProfitPercentUtil, 
  getRiskReward as getRiskRewardUtil, 
  getStopLossPercentForOrder as getStopLossPercentForOrderUtil,
  calculateTotalRisk,
  calculateTotalProfit
} from '../utils/riskCalculations';
import { 
  getPositionValue as getPositionValueUtil, 
  getAllocationPercent as getAllocationPercentUtil,
  calculateTotalPositionValue,
  calculateTotalAllocationPercent
} from '../utils/positionCalculations';

export default defineComponent({
  name: 'OpenOrdersTable',
  components: {
    OrderTableHeader,
    NewPositionOrdersTable,
    RiskSummary
  },
  props: {
    openOrders: {
      type: Array,
      default: () => []
    },
    loading: Boolean,
    error: Object,
    accountBalance: {
      type: Number,
      default: 100000,
    },
    stockHoldings: {
      type: Array,
      default: () => []
    },
    holdingsStopLossRisk: {
      type: Number,
      default: 0
    },
    hideRefreshButton: {
      type: Boolean,
      default: false
    }
  },
  emits: ['orders-updated', 'refresh'],
  setup(props, { emit }) {
    // Reactive state - simplified and consolidated
    const loadingState = reactive({
      price: false,
      save: false,
      load: false
    });
    
    const orderData = reactive({
      currentPrices: {},
      ordersWithReasons: {},
      positionTypes: {},
      ordersWithCatalysts: {},
      expandedOrders: {}
    });

    // Computed loading states for template
    const priceLoading = computed(() => loadingState.price);
    const saveLoading = computed(() => loadingState.save);
    const loadLoading = computed(() => loadingState.load);
    
    // Access to reactive data for template
    const currentPrices = orderData.currentPrices;
    const ordersWithReasons = orderData.ordersWithReasons;
    const positionTypes = orderData.positionTypes;
    const ordersWithCatalysts = orderData.ordersWithCatalysts;
    const expandedOrders = orderData.expandedOrders;

    // Get position type (short/long) for a symbol
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
      
    // Toggle position type for a symbol
    const togglePositionType = (symbol) => {
      if (!symbol) return;
      
      const currentType = getPositionType(symbol);
      const newType = !currentType;
      
      positionTypes[symbol] = newType;
      appPositionTypes[symbol] = newType;
      
      console.log(`Setting ${symbol} to ${newType ? 'SHORT' : 'LONG'}`);
      
      if (props.openOrders && props.openOrders.length > 0) {
        emit('orders-updated', [...props.openOrders]);
      }
    };
          
    // Expand/collapse order groups
    const toggleExpand = (orderId) => {
      expandedOrders[orderId] = !expandedOrders[orderId];
    };
    
    // Get status CSS class
    const getStatusClass = (status) => {
      if (!status) return 'status-default';
      
      switch (status.toLowerCase()) {
        case 'filled':
          return 'status-success';
        case 'submitted':
        case 'presubmitted':
          return 'status-processing';
        case 'cancelled':
          return 'status-error';
        case 'pendingsubmit':
          return 'status-warning';
        default:
          return 'status-default';
      }
    };

    // Event handlers
    const handleOrderReasonUpdate = (orderId, completed, reasonData) => {
      ordersWithReasons[orderId] = completed;
      
      const orderToUpdate = props.openOrders.find(
        order => (order.tradeNoteId === orderId) || (order.orderId === orderId)
      );
      
      if (orderToUpdate) {
        console.log(`Updating order ${orderId} with reason data:`, reasonData);
        orderToUpdate.reasonData = reasonData;
        orderToUpdate.reasonCompleted = completed;
        
        emit('orders-updated', [...props.openOrders]);
      }
    };
    
    const handleCatalystSelected = (orderId, catalyst) => {
      ordersWithCatalysts[orderId] = catalyst;
      
      const orderToUpdate = props.openOrders.find(
        order => (order.tradeNoteId === orderId) || (order.orderId === orderId)
      );
      
      if (orderToUpdate) {
        orderToUpdate.catalystData = catalyst;
        emit('orders-updated', [...props.openOrders]);
      }
    };

    // Helper function to determine if an order is for a new position
    const isNewPositionOrder = (order) => {
      if (order.hasOwnProperty('isExitPositionOrder')) {
        return !order.isExitPositionOrder;
      }
      
      const matchingHolding = holdingsMatchService.findMatchingHolding(order, props.stockHoldings);
      return !matchingHolding;
    };

    // Create wrapper functions that include getPositionType and avoid reactivity issues
    const getTargetPrice = (symbolData) => getTargetPriceUtil(symbolData, getPositionType);
    const getStopPrice = (symbolData) => getStopPriceUtil(symbolData, getPositionType);
    const getPositionValue = (symbolData) => getPositionValueUtil(symbolData);
    const getAllocationPercent = (symbolData, accountBalance = props.accountBalance) => getAllocationPercentUtil(symbolData, accountBalance);
    const getStopLossRisk = (symbolData) => getStopLossRiskUtil(symbolData, getPositionType);
    const getStopLossPercent = (symbolData) => getStopLossPercentUtil(symbolData, getPositionType);
    const getPotentialProfit = (symbolData) => getPotentialProfitUtil(symbolData, getPositionType);
    const getProfitPercent = (symbolData) => getProfitPercentUtil(symbolData, getPositionType);
    const getRiskReward = (symbolData) => getRiskRewardUtil(symbolData, getPositionType);
    const getStopLossPercentForOrder = (order) => getStopLossPercentForOrderUtil(order, getPositionType);

    // Process orders with additional data
    const processedOrders = computed(() => {
      if (!props.openOrders) return [];
      
      return props.openOrders.map(order => {
        const priceData = currentPrices[order.symbol];
        let isShort = getPositionType(order.symbol);
        const isMainOrder = detectIfMainOrder(order, props.openOrders, positionTypes);
        
        const symbolData = isMainOrder ? {
          mainOrder: order,
          subOrders: props.openOrders.filter(o => 
            o.symbol === order.symbol && !detectIfMainOrder(o, props.openOrders, positionTypes)
          )
        } : null;
        
        let riskRewardRatio = null;
        if (symbolData) {
          const profit = getPotentialProfit(symbolData);
          const risk = getStopLossRisk(symbolData);
          
          if (profit && risk && risk !== 0) {
            riskRewardRatio = Math.abs(profit / risk);
          }
        }
        
        let positionSizePercent = null;
        if (order.limitPrice && order.totalQuantity && props.accountBalance) {
          const positionValue = order.limitPrice * order.totalQuantity;
          positionSizePercent = (positionValue / props.accountBalance) * 100;
        }
        
        return {
          ...order,
          currentPrice: priceData?.price,
          priceSource: priceData?.source || 'Unknown',
          priceTimestamp: priceData?.timestamp,
          isShort,
          isMainOrder,
          catalystData: ordersWithCatalysts[order.orderId],
          reasonCompleted: ordersWithReasons[order.orderId],
          riskRewardRatio: riskRewardRatio,
          positionSizePercent: positionSizePercent,
          positionType: getPositionType(order.symbol) ? 'short' : 'long',
          potentialProfit: getPotentialProfit(symbolData),
          potentialProfitPercent: getProfitPercent(symbolData),
          stopLossRisk: getStopLossRisk(symbolData),
          stopLossPercent: getStopLossPercent(symbolData),
          mongoDbId: order.mongoDbId,
          source: 'table_save'
        };
      });
    });
    
    // Filter for new position orders
    const newPositionOrdersProcessed = computed(() => {
      return processedOrders.value.filter(order => isNewPositionOrder(order));
    });
    
    // Filter for exit position orders
    const exitPositionOrdersProcessed = computed(() => {
      return processedOrders.value.filter(order => !isNewPositionOrder(order));
    });
    
    // Group new position orders by symbol for hierarchical display
    const newPositionsBySymbol = computed(() => {
      const symbolMap = {};
      
      newPositionOrdersProcessed.value.forEach(order => {
        if (!symbolMap[order.symbol]) {
          symbolMap[order.symbol] = {
            symbol: order.symbol,
            mainOrder: null,
            subOrders: []
          };
        }
        
        if (order.isMainOrder) {
          symbolMap[order.symbol].mainOrder = order;
        } else {
          symbolMap[order.symbol].subOrders.push(order);
        }
      });

      const validPositions = [];
      const groups = Object.values(symbolMap);

      for (const group of groups) {
        let mainOrder = group.mainOrder;

        // If main order is cancelled, try to promote a new one
        if (mainOrder && (mainOrder.status === 'PendingCancel' || mainOrder.status === 'Cancelled')) {
          const isShort = getPositionType(group.symbol);
          const mainOrderAction = isShort ? 'SELL' : 'BUY';
          
          const candidates = group.subOrders.filter(o => 
            o.action.toUpperCase() === mainOrderAction && 
            o.orderType.toUpperCase() === 'LMT' &&
            o.status !== 'PendingCancel' && 
            o.status !== 'Cancelled'
          );

          if (candidates.length > 0) {
            // Promote the one with the largest quantity as the new main order
            const newMainOrder = candidates.reduce((prev, curr) => 
              (curr.totalQuantity > prev.totalQuantity) ? curr : prev
            );
            
            const oldMainOrder = group.mainOrder;
            group.mainOrder = { ...newMainOrder, isMainOrder: true };
            
            // Update subOrders: remove promoted order and add demoted old main order
            group.subOrders = group.subOrders
              .filter(o => o.orderId !== newMainOrder.orderId)
              .concat({ ...oldMainOrder, isMainOrder: false });
            
            validPositions.push(group);
          }
          // If no candidates, the group is discarded
        
        } else if (mainOrder) {
          // Main order is valid, keep the group
          validPositions.push(group);
        }
        // If no main order, group is discarded
      }
      
      return validPositions;
    });

    // Computed properties for UI state using utility functions directly
    const ordersNeedingPrices = computed(() => newPositionOrdersProcessed.value.filter(o => !o.currentPrice).length);
    
    const totalPositionValue = computed(() => {
      return calculateTotalPositionValue(newPositionsBySymbol.value);
    });
    
    const totalStopLossRisk = computed(() => {
      return calculateTotalRisk(newPositionsBySymbol.value, getPositionType);
    });
    
    const totalRiskPercent = computed(() => {
      if (totalPositionValue.value <= 0) return 0;
      return (totalStopLossRisk.value / totalPositionValue.value) * 100;
    });
    
    const totalAllocationPercent = computed(() => {
      return calculateTotalAllocationPercent(totalPositionValue.value, props.accountBalance || 100000);
    });
    
    const totalPotentialProfit = computed(() => {
      return calculateTotalProfit(newPositionsBySymbol.value, getPositionType);
    });

    // Fetch current prices using the centralized price service
    const fetchCurrentPrices = async (symbols, refresh = false) => {
      if (!symbols || symbols.length === 0) return;
      
      loadingState.price = true;
      try {
        const prices = await priceService.fetchCurrentPrices(
          symbols, 
          refresh,
          (data) => {
            if (refresh) message.success('Prices refreshed successfully');
          },
          (error) => {
            if (refresh) message.error('Failed to fetch current prices');
          }
        );
        
        Object.assign(currentPrices, prices);
      } finally {
        loadingState.price = false;
      }
    };

    const handleRefreshPrices = async () => {
      loadingState.price = true;
      try {
        const symbols = Array.from(new Set([
          ...processedOrders.value.map(order => order.symbol)
        ]));
        
        if (symbols.length > 0) {
          await priceService.fetchCurrentPrices(
            symbols,
            true,
            (data) => {
              message.success('Prices refreshed successfully');
              Object.assign(currentPrices, data);
            },
            (error) => {
              message.error('Failed to refresh prices');
            }
          );
          
          priceService.resetFetchTimer();
        }
        
        emit('refresh', true);
      } catch (error) {
        console.error('Error refreshing prices:', error);
        message.error('Failed to refresh prices');
      } finally {
        loadingState.price = false;
      }
    };
    // Additional helper functions for loading state
    const setSaveLoading = (loading) => {
      loadingState.save = loading;
    };
    
    const setLoadLoading = (loading) => {
      loadingState.load = loading;
    };
    
    // Check for duplicate orders in MongoDB and load their checklists
    const checkAndLoadOrdersFromMongoDB = async () => {
      await orderTableService.checkAndLoadOrdersFromMongoDB(
        processedOrders.value.filter(order => order.isMainOrder),
        ordersWithReasons,
        ordersWithCatalysts,
        props.openOrders,
        emit
      );
    };
    
    // Watch for changes to orders to update calculated metrics
    watch(() => props.openOrders, async (newOrders, oldOrders) => {
      await orderTableService.processOrdersWatch(
        newOrders,
        oldOrders,
        positionTypes,
        props.stockHoldings,
        emit,
        async () => {
          // Check MongoDB first
          await checkAndLoadOrdersFromMongoDB();
          
          // Then also apply any localStorage data to ensure latest data is used
          applyLocalStorageToOrdersState(
            ordersWithReasons,
            ordersWithCatalysts,
            newOrders
          );
        }
      );
    }, { immediate: true, deep: true });
    
    // Watch for changes in stock holdings to update order classifications - optimized
    watch(
      () => props.stockHoldings,
      (newHoldings) => {
        if (newHoldings && processedOrders.value.length > 0) {
          orderTableService.processStockHoldingsWatch(
            newHoldings,
            processedOrders.value,
            emit
          );
        }
      },
      { deep: true }
    );
    
    // Watch for price updates when parent refreshes prices - optimized
    watch(
      () => props.openOrders.map(order => ({ symbol: order.symbol, currentPrice: order.currentPrice })),
      (newData, oldData) => {
        if (!newData || newData.length === 0) return;
        
        // Check if prices have changed - more efficient comparison
        const pricesChanged = !oldData || 
          newData.length !== oldData.length ||
          newData.some((item, index) => {
            const oldItem = oldData[index];
            return !oldItem || item.currentPrice !== oldItem.currentPrice;
          });
        
        if (pricesChanged) {
          // Update local price cache efficiently
          newData.forEach(({ symbol, currentPrice }) => {
            if (symbol && currentPrice) {
              currentPrices[symbol] = {
                price: currentPrice,
                source: 'Parent',
                timestamp: new Date().toISOString()
              };
            }
          });
        }
      },
      { deep: true }
    );

    // MongoDB Integration using OrderTableService
    const saveOrdersToMongoDB = async () => {
      try {
        await orderTableService.saveOrdersToMongoDB(
          processedOrders.value,
          getPositionType,
          setSaveLoading
        );
        
        // After successful save to MongoDB, clear localStorage data
        clearOrderDataFromLocalStorage();
        console.log('Cleared checklist and catalyst data from localStorage after saving to MongoDB');
        message.success('Orders saved to MongoDB and cleared from local storage');
      } catch (error) {
        console.error('Error saving orders to MongoDB:', error);
        message.error('Failed to save orders to MongoDB');
      }
    };
    
    const loadOrdersFromMongoDB = async () => {
      try {
        setLoadLoading(true);
        
        // First check localStorage for any unsaved data
        try {
          const dataLoaded = applyLocalStorageToOrdersState(
            ordersWithReasons, 
            ordersWithCatalysts,
            props.openOrders
          );
          
          // If we have local data, refresh the order list
          if (dataLoaded) {
            emit('orders-updated', [...props.openOrders]);
            message.info('Loaded data from local storage');
          }
        } catch (error) {
          console.error('Error loading from localStorage:', error);
        }
        
        // Then load from MongoDB for any additional data
        await orderTableService.loadOrdersFromMongoDB(
          ordersWithCatalysts,
          ordersWithReasons,
          positionTypes,
          getPositionType,
          fetchCurrentPrices,
          emit,
          setLoadLoading
        );
      } finally {
        setLoadLoading(false);
      }
    };
    
    // Return only what's needed for the main component and sub-components
    return {
      // Loading states for header component
      priceLoading,
      saveLoading,
      loadLoading,
      
      // Data for sub-components
      newPositionsBySymbol,
      exitPositionOrdersProcessed,
      
      // Calculated totals for header and sub-components
      ordersNeedingPrices,
      totalStopLossRisk,
      totalRiskPercent,
      totalPositionValue,
      totalAllocationPercent,
      totalPotentialProfit,
      
      // Event handlers for header component
      handleRefreshPrices,
      saveOrdersToMongoDB,
      loadOrdersFromMongoDB,
      
      // Event handlers for table components
      getPositionType,
      togglePositionType,
      handleOrderReasonUpdate,
      handleCatalystSelected,
      toggleExpand,
      expandedOrders,
      
      // Calculation functions for table components
      getStopLossRisk,
      getStopLossPercent,
      getStopLossPercentForOrder,
      getPotentialProfit,
      getProfitPercent,
      getRiskReward,
      getPositionValue,
      getAllocationPercent
    };
  }
});
</script>

<style scoped>
/* Only minimal global styles needed for the container */
/* All component-specific styles have been moved to their respective sub-components */
</style> 