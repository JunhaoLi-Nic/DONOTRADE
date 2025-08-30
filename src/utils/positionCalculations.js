/**
 * Utility functions for position-related calculations
 * Handles position values, allocation percentages, and position sizing
 */

/**
 * Calculate position value for a symbol group
 * @param {Object} symbolData - Object containing mainOrder and subOrders
 * @returns {number|null} Position value or null if cannot be calculated
 */
export function getPositionValue(symbolData) {
  if (!symbolData || !symbolData.mainOrder) return null
  
  const { mainOrder } = symbolData
  if (!mainOrder.limitPrice || !mainOrder.totalQuantity) return null
  
  return mainOrder.limitPrice * mainOrder.totalQuantity
}

/**
 * Calculate allocation percentage for a symbol group
 * @param {Object} symbolData - Object containing mainOrder and subOrders
 * @param {number} accountBalance - Total account balance
 * @returns {number|null} Allocation percentage or null if cannot be calculated
 */
export function getAllocationPercent(symbolData, accountBalance) {
  const positionValue = getPositionValue(symbolData)
  if (positionValue === null || !accountBalance) return null
  
  return (positionValue / accountBalance) * 100
}

/**
 * Calculate position size for an order
 * @param {Object} order - Order object
 * @param {number} accountBalance - Total account balance
 * @returns {number|null} Position size percentage or null if cannot be calculated
 */
export function calculatePositionSize(order, accountBalance) {
  if (!order.limitPrice || !order.totalQuantity || !accountBalance) return null
  
  const positionValue = order.limitPrice * order.totalQuantity
  return (positionValue / accountBalance) * 100
}

/**
 * Calculate total position value across multiple positions
 * @param {Array} symbolDataArray - Array of symbol data objects
 * @returns {number} Total position value
 */
export function calculateTotalPositionValue(symbolDataArray) {
  if (!Array.isArray(symbolDataArray)) return 0
  
  return symbolDataArray.reduce((total, symbolData) => {
    if (symbolData.mainOrder && symbolData.mainOrder.limitPrice && symbolData.mainOrder.totalQuantity) {
      return total + (symbolData.mainOrder.limitPrice * symbolData.mainOrder.totalQuantity)
    }
    return total
  }, 0)
}

/**
 * Calculate total allocation percentage
 * @param {number} totalPositionValue - Total value of all positions
 * @param {number} accountBalance - Total account balance
 * @returns {number} Total allocation percentage
 */
export function calculateTotalAllocationPercent(totalPositionValue, accountBalance) {
  if (!accountBalance || accountBalance <= 0) return 0
  return (totalPositionValue / accountBalance) * 100
}

/**
 * Calculate share quantity needed for target allocation
 * @param {number} targetPercent - Target allocation percentage
 * @param {number} accountBalance - Total account balance
 * @param {number} sharePrice - Price per share
 * @returns {number|null} Number of shares or null if cannot be calculated
 */
export function calculateSharesForAllocation(targetPercent, accountBalance, sharePrice) {
  if (!targetPercent || !accountBalance || !sharePrice || sharePrice <= 0) return null
  
  const targetValue = (targetPercent / 100) * accountBalance
  return Math.floor(targetValue / sharePrice)
}

/**
 * Calculate cost basis for a position
 * @param {Array} orders - Array of order objects for the same symbol
 * @returns {Object} Object containing total shares, total cost, and average price
 */
export function calculateCostBasis(orders) {
  if (!Array.isArray(orders) || orders.length === 0) {
    return { totalShares: 0, totalCost: 0, averagePrice: 0 }
  }
  
  let totalShares = 0
  let totalCost = 0
  
  orders.forEach(order => {
    if (order.totalQuantity && order.limitPrice) {
      const shares = order.totalQuantity
      const cost = shares * order.limitPrice
      
      // Handle buy vs sell orders
      if (order.action && order.action.toUpperCase() === 'BUY') {
        totalShares += shares
        totalCost += cost
      } else if (order.action && order.action.toUpperCase() === 'SELL') {
        totalShares -= shares
        // For sells, subtract the cost basis proportionally
        totalCost -= cost
      }
    }
  })
  
  const averagePrice = totalShares > 0 ? totalCost / totalShares : 0
  
  return {
    totalShares,
    totalCost,
    averagePrice
  }
}

/**
 * Calculate diversification metrics
 * @param {Array} symbolDataArray - Array of symbol data objects
 * @param {number} accountBalance - Total account balance
 * @returns {Object} Diversification metrics
 */
export function calculateDiversificationMetrics(symbolDataArray, accountBalance) {
  if (!Array.isArray(symbolDataArray) || symbolDataArray.length === 0) {
    return {
      totalPositions: 0,
      averageAllocation: 0,
      maxAllocation: 0,
      minAllocation: 0,
      concentrationRisk: 'low'
    }
  }
  
  const allocations = symbolDataArray.map(symbolData => {
    return getAllocationPercent(symbolData, accountBalance) || 0
  }).filter(allocation => allocation > 0)
  
  const totalPositions = allocations.length
  const averageAllocation = allocations.length > 0 ? 
    allocations.reduce((sum, alloc) => sum + alloc, 0) / allocations.length : 0
  const maxAllocation = allocations.length > 0 ? Math.max(...allocations) : 0
  const minAllocation = allocations.length > 0 ? Math.min(...allocations) : 0
  
  // Determine concentration risk
  let concentrationRisk = 'low'
  if (maxAllocation > 20) {
    concentrationRisk = 'high'
  } else if (maxAllocation > 10) {
    concentrationRisk = 'medium'
  }
  
  return {
    totalPositions,
    averageAllocation,
    maxAllocation,
    minAllocation,
    concentrationRisk
  }
}

/**
 * Calculate Kelly Criterion position size
 * @param {number} winRate - Win rate as decimal (0.6 for 60%)
 * @param {number} avgWin - Average winning amount
 * @param {number} avgLoss - Average losing amount
 * @returns {number|null} Recommended position size as percentage or null if invalid
 */
export function calculateKellyPositionSize(winRate, avgWin, avgLoss) {
  if (!winRate || !avgWin || !avgLoss || avgLoss <= 0 || winRate <= 0 || winRate >= 1) return null
  
  const lossRate = 1 - winRate
  const kellyPercent = winRate - (lossRate / (avgWin / avgLoss))
  
  // Cap at reasonable maximum and ensure it's positive
  return Math.max(0, Math.min(kellyPercent * 100, 25))
}