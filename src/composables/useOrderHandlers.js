import { reactive } from 'vue'
import { message } from 'ant-design-vue'
import { positionTypes as appPositionTypes } from '../utils/positionUtils'
import priceService from '../services/priceService'

/**
 * Composable for order event handlers and actions
 */
export function useOrderHandlers(orderData, emit, props, stockHoldings) {
  
  const { currentPrices, ordersWithReasons, positionTypes, ordersWithCatalysts, expandedOrders } = orderData

  // Event handlers
  const handleOrderReasonUpdate = (orderId, completed, reasonData) => {
    // Store the reason completion status in the reactive map
    ordersWithReasons[orderId] = completed
    
    // Find the order in our local state and update it with the reason data
    const orderToUpdate = props.openOrders.find(
      order => (order.tradeNoteId === orderId) || (order.orderId === orderId)
    )
    
    if (orderToUpdate) {
      console.log(`Updating order ${orderId} with reason data:`, reasonData)
      // Update the order with new data
      orderToUpdate.reasonData = reasonData
      orderToUpdate.reasonCompleted = completed
      
      // Force reactivity by emitting updated orders
      emit('orders-updated', [...props.openOrders])
    }
  }
  
  const handleCatalystSelected = (orderId, catalyst) => {
    // Store catalyst data in the reactive map
    ordersWithCatalysts[orderId] = catalyst
    
    // Find the order and update its catalyst data
    const orderToUpdate = props.openOrders.find(
      order => (order.tradeNoteId === orderId) || (order.orderId === orderId)
    )
    
    if (orderToUpdate) {
      orderToUpdate.catalystData = catalyst
      
      // Force reactivity by emitting updated orders
      emit('orders-updated', [...props.openOrders])
    }
  }
  
  // Get position type (short/long) for a symbol
  const getPositionType = (symbol) => {
    if (!symbol) return false
    
    // Check in app-wide position types first
    if (appPositionTypes.hasOwnProperty(symbol)) {
      return appPositionTypes[symbol]
    }
    
    // Check local position types
    if (positionTypes.hasOwnProperty(symbol)) {
      return positionTypes[symbol]
    }
    
    // Otherwise check holdings
    const existingHolding = stockHoldings.value?.find(holding => holding.symbol === symbol)
    if (existingHolding) {
      const isShort = existingHolding.shares < 0 || !!existingHolding.isShort
      positionTypes[symbol] = isShort
      appPositionTypes[symbol] = isShort
      return isShort
    }
    
    // Default to long
    positionTypes[symbol] = false
    return false
  }
    
  // Toggle position type for a symbol
  const togglePositionType = (symbol) => {
    if (!symbol) return
    
    const currentType = getPositionType(symbol)
    const newType = !currentType
    
    positionTypes[symbol] = newType
    appPositionTypes[symbol] = newType
    
    console.log(`Setting ${symbol} to ${newType ? 'SHORT' : 'LONG'}`)
    
    if (props.openOrders && props.openOrders.length > 0) {
      emit('orders-updated', [...props.openOrders])
    }
  }
        
  // Expand/collapse order groups
  const toggleExpand = (orderId) => {
    expandedOrders[orderId] = !expandedOrders[orderId]
  }
  
  // Get status CSS class
  const getStatusClass = (status) => {
    if (!status) return 'status-default'
    
    switch (status.toLowerCase()) {
      case 'filled':
        return 'status-success'
      case 'submitted':
      case 'presubmitted':
        return 'status-processing'
      case 'cancelled':
        return 'status-error'
      case 'pendingsubmit':
        return 'status-warning'
      default:
        return 'status-default'
    }
  }

  // Fetch current prices using the centralized price service
  const fetchCurrentPrices = async (symbols, refresh = false) => {
    if (!symbols || symbols.length === 0) return
    
    try {
      // Use the centralized price service
      const prices = await priceService.fetchCurrentPrices(
        symbols, 
        refresh,
        // Success callback
        (data) => {
          if (refresh) message.success('Prices refreshed successfully')
        },
        // Error callback
        (error) => {
          if (refresh) message.error('Failed to fetch current prices')
        }
      )
      
      // Update local state with the fetched prices
      Object.assign(currentPrices, prices)
    } catch (error) {
      console.error('Error fetching prices:', error)
      if (refresh) message.error('Failed to fetch prices')
    }
  }

  const handleRefreshPrices = async (loadingState, processedOrders) => {
    loadingState.price = true
    try {
      // Get all unique symbols from orders
      const symbols = Array.from(new Set([
        ...processedOrders.value.map(order => order.symbol)
      ]))
      
      if (symbols.length > 0) {
        // Use the price service to force refresh all symbols
        await priceService.fetchCurrentPrices(
          symbols,
          true, // force refresh from API and backend cache
          (data) => {
            message.success('Prices refreshed successfully')
            // Update local state with the fetched prices
            Object.assign(currentPrices, data)
          },
          (error) => {
            message.error('Failed to refresh prices')
          }
        )
        
        // Reset the price service timer to ensure next regular fetch happens
        priceService.resetFetchTimer()
      }
      
      // Also emit to parent for any additional refresh handling
      emit('refresh', true)
    } catch (error) {
      console.error('Error refreshing prices:', error)
      message.error('Failed to refresh prices')
    } finally {
      loadingState.price = false
    }
  }

  return {
    handleOrderReasonUpdate,
    handleCatalystSelected,
    getPositionType,
    togglePositionType,
    toggleExpand,
    getStatusClass,
    fetchCurrentPrices,
    handleRefreshPrices
  }
}