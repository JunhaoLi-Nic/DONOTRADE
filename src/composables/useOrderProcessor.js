import { computed } from 'vue'
import { detectIfMainOrder } from '../utils/detectmain'
import holdingsMatchService from '../services/holdingsMatchService'

/**
 * Composable for processing and transforming order data
 */
export function useOrderProcessor(openOrders, stockHoldings, currentPrices, positionTypes, ordersWithCatalysts, ordersWithReasons, getPositionType, accountBalance) {
  
  // Helper function to determine if an order is for a new position
  const isNewPositionOrder = (order) => {
    // If the order already has isExitPositionOrder flag, use it
    if (order.hasOwnProperty('isExitPositionOrder')) {
      return !order.isExitPositionOrder
    }
    
    // Otherwise, use the holdings match service to determine
    const matchingHolding = holdingsMatchService.findMatchingHolding(order, stockHoldings.value)
    return !matchingHolding
  }

  // Process orders with additional data
  const processedOrders = computed(() => {
    if (!openOrders.value) return []
    
    return openOrders.value.map(order => {
      // Get price data for this symbol
      const priceData = currentPrices[order.symbol]
      
      // Get existing position type if any
      let isShort = getPositionType(order.symbol)
      
      // Determine if this is a main order (for grouping)
      const isMainOrder = detectIfMainOrder(order, openOrders.value, positionTypes)
      
      // Find the symbol data for this order to calculate risk-reward ratio
      const symbolData = isMainOrder ? {
        mainOrder: order,
        subOrders: openOrders.value.filter(o => 
          o.symbol === order.symbol && !detectIfMainOrder(o, openOrders.value, positionTypes)
        )
      } : null
      
      // Calculate risk-reward ratio if this is a main order
      let riskRewardRatio = null
      if (symbolData) {
        const profit = getPotentialProfit(symbolData)
        const risk = getStopLossRisk(symbolData)
        
        if (profit && risk && risk !== 0) {
          riskRewardRatio = Math.abs(profit / risk)
          console.log(`Calculated risk-reward ratio for ${order.symbol}: ${riskRewardRatio}`)
        }
      }
      
      // Calculate position size percentage
      let positionSizePercent = null
      if (order.limitPrice && order.totalQuantity && accountBalance) {
        const positionValue = order.limitPrice * order.totalQuantity
        positionSizePercent = (positionValue / accountBalance) * 100
        console.log(`Calculated position size for ${order.symbol}: ${positionSizePercent.toFixed(2)}%`)
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
        potentialProfit: null, // Will be calculated by calculations composable
        potentialProfitPercent: null, // Will be calculated by calculations composable
        stopLossRisk: null, // Will be calculated by calculations composable
        stopLossPercent: null, // Will be calculated by calculations composable
        mongoDbId: order.mongoDbId,
        source: 'table_save'
      }
    })
  })
  
  // Filter for new position orders
  const newPositionOrdersProcessed = computed(() => {
    return processedOrders.value.filter(order => isNewPositionOrder(order))
  })
  
  // Filter for exit position orders
  const exitPositionOrdersProcessed = computed(() => {
    return processedOrders.value.filter(order => !isNewPositionOrder(order))
  })
  
  // Group new position orders by symbol for hierarchical display
  const newPositionsBySymbol = computed(() => {
    const symbolMap = {}
    
    // First pass - gather by symbol
    newPositionOrdersProcessed.value.forEach(order => {
      if (!symbolMap[order.symbol]) {
        symbolMap[order.symbol] = {
          symbol: order.symbol,
          mainOrder: null,
          subOrders: []
        }
      }
      
      // Add to appropriate group
      if (order.isMainOrder) {
        symbolMap[order.symbol].mainOrder = order
      } else {
        symbolMap[order.symbol].subOrders.push(order)
      }
    })
    
    // Convert to array and sort
    return Object.values(symbolMap)
  })

  return {
    processedOrders,
    newPositionOrdersProcessed,
    exitPositionOrdersProcessed,
    newPositionsBySymbol,
    isNewPositionOrder
  }
}