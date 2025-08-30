/**
 * Utility functions for risk-related calculations
 * Handles stop loss risk, profit calculations, and risk/reward ratios
 */

import { getTargetPrice, getStopPrice } from './priceCalculations'

/**
 * Calculate stop loss risk for a symbol group
 * @param {Object} symbolData - Object containing mainOrder and subOrders
 * @param {Function} getPositionType - Function to determine if position is short
 * @returns {number|null} Stop loss risk amount or null if cannot be calculated
 */
export function getStopLossRisk(symbolData, getPositionType) {
  if (!symbolData || !symbolData.mainOrder) return null
  
  const { mainOrder } = symbolData
  const entryPrice = mainOrder.limitPrice
  const quantity = mainOrder.totalQuantity
  
  if (!entryPrice || !quantity) return null
  
  // Get stop price from sub-orders
  const stopPrice = getStopPrice(symbolData, getPositionType)
  if (!stopPrice) return null
  
  const isShort = getPositionType(symbolData.symbol || symbolData.mainOrder?.symbol)
  
  // Find all stop orders
  const activeSubOrders = symbolData.subOrders ? symbolData.subOrders.filter(order => order.status !== 'PendingCancel') : [];
  
  if (isShort) {
    // For short positions, find all stop orders (BUY STP or BUY LMT above entry)
    const stopOrders = activeSubOrders.filter(order => {
      const isStopLoss = order.action.toUpperCase() === 'BUY' && (
        order.orderType.toUpperCase() === 'STP' || 
        (order.orderType.toUpperCase() === 'LMT' && order.limitPrice > entryPrice)
      );
      return isStopLoss;
    });
    
    if (stopOrders.length > 0) {
      // Calculate total risk from all stop orders using their quantities
      let totalRisk = 0;
      let remainingQty = quantity;
      
      // Sort by price (highest to lowest for short positions - worst to best)
      const sortedStops = stopOrders.sort((a, b) => 
        (b.stopPrice || b.limitPrice) - (a.stopPrice || a.limitPrice)
      );
      
      for (const order of sortedStops) {
        const stopPrice = order.stopPrice || order.limitPrice;
        const orderQty = Math.min(order.totalQuantity, remainingQty);
        
        if (orderQty > 0) {
          totalRisk += (stopPrice - entryPrice) * orderQty;
          remainingQty -= orderQty;
          
          if (remainingQty <= 0) break;
        }
      }
      
      // If we still have remaining quantity, use the worst stop price for the rest
      if (remainingQty > 0) {
        const worstStopPrice = Math.max(...stopOrders.map(o => o.stopPrice || o.limitPrice));
        totalRisk += (worstStopPrice - entryPrice) * remainingQty;
      }
      
      return totalRisk;
    }
    
    // Fall back to simple calculation if no specific stop orders found
    return (stopPrice - entryPrice) * quantity;
  } else {
    // For long positions, find all stop orders (SELL STP or SELL LMT below entry)
    const stopOrders = activeSubOrders.filter(order => {
      const isStopLoss = order.action.toUpperCase() === 'SELL' && (
        order.orderType.toUpperCase() === 'STP' || 
        (order.orderType.toUpperCase() === 'LMT' && order.limitPrice < entryPrice)
      );
      return isStopLoss;
    });
    
    if (stopOrders.length > 0) {
      // Calculate total risk from all stop orders using their quantities
      let totalRisk = 0;
      let remainingQty = quantity;
      
      // Sort by price (lowest to highest for long positions - worst to best)
      const sortedStops = stopOrders.sort((a, b) => 
        (a.stopPrice || a.limitPrice) - (b.stopPrice || b.limitPrice)
      );
      
      for (const order of sortedStops) {
        const stopPrice = order.stopPrice || order.limitPrice;
        const orderQty = Math.min(order.totalQuantity, remainingQty);
        
        if (orderQty > 0) {
          totalRisk += (entryPrice - stopPrice) * orderQty;
          remainingQty -= orderQty;
          
          if (remainingQty <= 0) break;
        }
      }
      
      // If we still have remaining quantity, use the worst stop price for the rest
      if (remainingQty > 0) {
        const worstStopPrice = Math.min(...stopOrders.map(o => o.stopPrice || o.limitPrice));
        totalRisk += (entryPrice - worstStopPrice) * remainingQty;
      }
      
      return totalRisk;
    }
    
    // Fall back to simple calculation if no specific stop orders found
    return (entryPrice - stopPrice) * quantity;
  }
}

/**
 * Calculate stop loss percentage
 * @param {Object} symbolData - Object containing mainOrder and subOrders
 * @param {Function} getPositionType - Function to determine if position is short
 * @returns {number|null} Stop loss percentage or null if cannot be calculated
 */
export function getStopLossPercent(symbolData, getPositionType) {
  if (!symbolData || !symbolData.mainOrder) return null
  
  const entryPrice = symbolData.mainOrder.limitPrice
  if (!entryPrice) return null
  
  const stopPrice = getStopPrice(symbolData, getPositionType)
  if (!stopPrice) return null
  
  const isShort = getPositionType(symbolData.symbol || symbolData.mainOrder?.symbol)
  
  if (isShort) {
    // For short positions: percentage = ((stopPrice - entryPrice) / entryPrice) * 100
    return ((stopPrice - entryPrice) / entryPrice) * 100
  } else {
    // For long positions: percentage = ((entryPrice - stopPrice) / entryPrice) * 100  
    return ((entryPrice - stopPrice) / entryPrice) * 100
  }
}

/**
 * Calculate potential profit for a symbol group
 * @param {Object} symbolData - Object containing mainOrder and subOrders
 * @param {Function} getPositionType - Function to determine if position is short
 * @returns {number|null} Potential profit amount or null if cannot be calculated
 */
export function getPotentialProfit(symbolData, getPositionType) {
  if (!symbolData || !symbolData.mainOrder) return null
  
  const { mainOrder } = symbolData
  const entryPrice = mainOrder.limitPrice
  const quantity = mainOrder.totalQuantity
  
  if (!entryPrice || !quantity) return null
  
  // Get target price from sub-orders
  const targetPrice = getTargetPrice(symbolData, getPositionType)
  if (!targetPrice) return null
  
  const isShort = getPositionType(symbolData.symbol || symbolData.mainOrder?.symbol)
  
  // Find all target orders
  const activeSubOrders = symbolData.subOrders ? symbolData.subOrders.filter(order => order.status !== 'PendingCancel') : [];
  
  if (isShort) {
    // For short positions, find all target orders (BUY LMT below entry)
    const targetOrders = activeSubOrders.filter(order => {
      return order.action.toUpperCase() === 'BUY' && 
             order.orderType.toUpperCase() === 'LMT' && 
             order.limitPrice < entryPrice;
    });
    
    if (targetOrders.length > 0) {
      // Calculate total profit from all target orders using their quantities
      let totalProfit = 0;
      let remainingQty = quantity;
      
      // Sort by price (highest to lowest for short positions - best to worst)
      const sortedTargets = targetOrders.sort((a, b) => b.limitPrice - a.limitPrice);
      
      for (const order of sortedTargets) {
        const orderQty = Math.min(order.totalQuantity, remainingQty);
        
        if (orderQty > 0) {
          totalProfit += (entryPrice - order.limitPrice) * orderQty;
          remainingQty -= orderQty;
          
          if (remainingQty <= 0) break;
        }
      }
      
      // If we still have remaining quantity, use the weighted average target price
      if (remainingQty > 0) {
        totalProfit += (entryPrice - targetPrice) * remainingQty;
      }
      
      return totalProfit;
    }
    
    // Fall back to simple calculation if no specific target orders found
    return (entryPrice - targetPrice) * quantity;
  } else {
    // For long positions, find all target orders (SELL LMT above entry)
    const targetOrders = activeSubOrders.filter(order => {
      return order.action.toUpperCase() === 'SELL' && 
             order.orderType.toUpperCase() === 'LMT' && 
             order.limitPrice > entryPrice;
    });
    
    if (targetOrders.length > 0) {
      // Calculate total profit from all target orders using their quantities
      let totalProfit = 0;
      let remainingQty = quantity;
      
      // Sort by price (highest to lowest for long positions - best to worst)
      const sortedTargets = targetOrders.sort((a, b) => b.limitPrice - a.limitPrice);
      
      for (const order of sortedTargets) {
        const orderQty = Math.min(order.totalQuantity, remainingQty);
        
        if (orderQty > 0) {
          totalProfit += (order.limitPrice - entryPrice) * orderQty;
          remainingQty -= orderQty;
          
          if (remainingQty <= 0) break;
        }
      }
      
      // If we still have remaining quantity, use the weighted average target price
      if (remainingQty > 0) {
        totalProfit += (targetPrice - entryPrice) * remainingQty;
      }
      
      return totalProfit;
    }
    
    // Fall back to simple calculation if no specific target orders found
    return (targetPrice - entryPrice) * quantity;
  }
}

/**
 * Calculate profit percentage
 * @param {Object} symbolData - Object containing mainOrder and subOrders
 * @param {Function} getPositionType - Function to determine if position is short
 * @returns {number|null} Profit percentage or null if cannot be calculated
 */
export function getProfitPercent(symbolData, getPositionType) {
  if (!symbolData || !symbolData.mainOrder) return null
  
  const entryPrice = symbolData.mainOrder.limitPrice
  if (!entryPrice) return null
  
  const targetPrice = getTargetPrice(symbolData, getPositionType)
  if (!targetPrice) return null
  
  const isShort = getPositionType(symbolData.symbol || symbolData.mainOrder?.symbol)
  
  if (isShort) {
    // For short positions: percentage = ((entryPrice - targetPrice) / entryPrice) * 100
    return ((entryPrice - targetPrice) / entryPrice) * 100
  } else {
    // For long positions: percentage = ((targetPrice - entryPrice) / entryPrice) * 100
    return ((targetPrice - entryPrice) / entryPrice) * 100
  }
}

/**
 * Calculate risk/reward ratio
 * @param {Object} symbolData - Object containing mainOrder and subOrders
 * @param {Function} getPositionType - Function to determine if position is short
 * @returns {number|null} Risk/reward ratio or null if cannot be calculated
 */
export function getRiskReward(symbolData, getPositionType) {
  const profit = getPotentialProfit(symbolData, getPositionType)
  const risk = getStopLossRisk(symbolData, getPositionType)
  
  if (!profit || !risk || risk === 0) return null
  
  return Math.abs(profit / risk)
}

/**
 * Calculate stop loss percentage for individual orders (exit positions)
 * @param {Object} order - Individual order object
 * @param {Function} getPositionType - Function to determine if position is short
 * @returns {number|null} Stop loss percentage or null if cannot be calculated
 */
export function getStopLossPercentForOrder(order, getPositionType) {
  if (!order.limitPrice || !order.stopPrice) return null
  
  const isShort = getPositionType(order.symbol)
  
  if (isShort) {
    return ((order.stopPrice - order.limitPrice) / order.limitPrice) * 100
  } else {
    return ((order.limitPrice - order.stopPrice) / order.limitPrice) * 100
  }
}

/**
 * Calculate total risk across multiple positions
 * @param {Array} symbolDataArray - Array of symbol data objects
 * @param {Function} getPositionType - Function to determine if position is short
 * @returns {number} Total risk amount
 */
export function calculateTotalRisk(symbolDataArray, getPositionType) {
  if (!Array.isArray(symbolDataArray)) return 0
  
  return symbolDataArray.reduce((total, symbolData) => {
    const risk = getStopLossRisk(symbolData, getPositionType)
    return total + (risk || 0)
  }, 0)
}

/**
 * Calculate total potential profit across multiple positions
 * @param {Array} symbolDataArray - Array of symbol data objects
 * @param {Function} getPositionType - Function to determine if position is short
 * @returns {number} Total potential profit
 */
export function calculateTotalProfit(symbolDataArray, getPositionType) {
  if (!Array.isArray(symbolDataArray)) return 0
  
  return symbolDataArray.reduce((total, symbolData) => {
    const profit = getPotentialProfit(symbolData, getPositionType)
    return total + (profit || 0)
  }, 0)
}

/**
 * Calculate portfolio risk percentage
 * @param {number} totalRisk - Total risk amount
 * @param {number} totalValue - Total portfolio value
 * @returns {number} Risk percentage
 */
export function calculateRiskPercent(totalRisk, totalValue) {
  if (!totalValue || totalValue <= 0) return 0
  return (totalRisk / totalValue) * 100
}