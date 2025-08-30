import { computed } from 'vue'
import { getTargetPrice, getStopPrice } from '../utils/priceCalculations'
import { 
  getStopLossRisk, 
  getStopLossPercent, 
  getPotentialProfit, 
  getProfitPercent, 
  getRiskReward, 
  getStopLossPercentForOrder,
  calculateTotalRisk,
  calculateTotalProfit
} from '../utils/riskCalculations'
import { 
  getPositionValue, 
  getAllocationPercent,
  calculateTotalPositionValue,
  calculateTotalAllocationPercent
} from '../utils/positionCalculations'

/**
 * Composable for order calculation utilities
 * Now uses dedicated utility modules for better organization
 */
export function useOrderCalculations(newPositionsBySymbol, newPositionOrdersProcessed, getPositionType) {
  
  // Wrapper functions that include getPositionType parameter
  const getTargetPriceWrapper = (symbolData) => getTargetPrice(symbolData, getPositionType)
  const getStopPriceWrapper = (symbolData) => getStopPrice(symbolData, getPositionType)
  const getPositionValueWrapper = (symbolData) => getPositionValue(symbolData)
  const getAllocationPercentWrapper = (symbolData, accountBalance = 100000) => getAllocationPercent(symbolData, accountBalance)
  const getStopLossRiskWrapper = (symbolData) => getStopLossRisk(symbolData, getPositionType)
  const getStopLossPercentWrapper = (symbolData) => getStopLossPercent(symbolData, getPositionType)
  const getPotentialProfitWrapper = (symbolData) => getPotentialProfit(symbolData, getPositionType)
  const getProfitPercentWrapper = (symbolData) => getProfitPercent(symbolData, getPositionType)
  const getRiskRewardWrapper = (symbolData) => getRiskReward(symbolData, getPositionType)
  const getStopLossPercentForOrderWrapper = (order) => getStopLossPercentForOrder(order, getPositionType)

  // Computed totals using utility functions
  const totalPositionValue = computed(() => {
    return calculateTotalPositionValue(newPositionsBySymbol.value)
  })

  const totalAllocationPercent = computed(() => {
    const accountBalance = 100000 // This should be passed as a prop
    return calculateTotalAllocationPercent(totalPositionValue.value, accountBalance)
  })

  const totalStopLossRisk = computed(() => {
    return calculateTotalRisk(newPositionsBySymbol.value, getPositionType)
  })

  const totalRiskPercent = computed(() => {
    if (totalPositionValue.value <= 0) return 0
    return (totalStopLossRisk.value / totalPositionValue.value) * 100
  })

  const totalPotentialProfit = computed(() => {
    return calculateTotalProfit(newPositionsBySymbol.value, getPositionType)
  })

  const ordersNeedingPrices = computed(() => {
    return newPositionOrdersProcessed.value.filter(o => !o.currentPrice).length
  })

  return {
    getTargetPrice: getTargetPriceWrapper,
    getStopPrice: getStopPriceWrapper,
    getPositionValue: getPositionValueWrapper,
    getAllocationPercent: getAllocationPercentWrapper,
    getStopLossRisk: getStopLossRiskWrapper,
    getStopLossPercent: getStopLossPercentWrapper,
    getPotentialProfit: getPotentialProfitWrapper,
    getProfitPercent: getProfitPercentWrapper,
    getRiskReward: getRiskRewardWrapper,
    getStopLossPercentForOrder: getStopLossPercentForOrderWrapper,
    totalPositionValue,
    totalAllocationPercent,
    totalStopLossRisk,
    totalRiskPercent,
    totalPotentialProfit,
    ordersNeedingPrices
  }
}