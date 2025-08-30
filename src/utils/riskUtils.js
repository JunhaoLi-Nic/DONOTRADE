import { reactive } from 'vue';
import { positionTypes } from './positionUtils';

// Reactive store for risk parameters
export const riskParameters = reactive({
  maxDrawdown: 5, // Default 5%
  riskPerTrade: 0.5, // Default 0.5%
  maxExpectedStopLossPercent: 5, // Default 5%
});

/**
 * Calculate stop losses based on risk settings, correctly distributing risk
 * across positions and respecting maximum drawdown limits
 * 
 * @param {Array} holdings - Array of position objects 
 * @param {Number} maxDrawdown - Maximum drawdown percentage for the entire portfolio
 * @param {Number} riskPerTrade - Risk per trade percentage
 * @param {Number} accountBalance - Total account balance
 * @returns {Array} - Holdings with updated stop loss calculations
 */
export const calculateStopLosses = (
  holdings,
  maxDrawdown,
  riskPerTrade,
  accountBalance
) => {
  // Store risk parameters in the reactive store
  riskParameters.maxDrawdown = maxDrawdown;
  riskParameters.riskPerTrade = riskPerTrade;

  // Get total portfolio value
  const totalValue = holdings.reduce((sum, pos) => sum + (pos.value || 0), 0);
  
  // Total positions with value (to distribute risk)
  const positionsWithValue = holdings.filter(pos => pos.value > 0 && pos.shares !== 0 && pos.currentPrice > 0);
  const positionCount = positionsWithValue.length;
  
  if (positionCount === 0) return holdings;
  
  // Calculate maximum allowed loss for the entire account 
  const maxDrawdownAmount = accountBalance * (maxDrawdown / 100);
  
  // Calculate per trade risk amount
  const riskPerTradeAmount = accountBalance * (riskPerTrade / 100);
  
  console.log('Risk calculation:', { 
    accountBalance,
    totalValue,
    riskPerTrade,
    riskPerTradeAmount,
    maxDrawdown,
    maxDrawdownAmount,
    positionCount
  });
  
  // Calculate total risk if we applied risk per trade to all positions
  const totalRiskIfPerTrade = riskPerTradeAmount * positionCount;
  
  // If total risk exceeds max drawdown, we need to scale back each position's risk
  const shouldScaleRisk = totalRiskIfPerTrade > maxDrawdownAmount;
  
  // Determine risk allocation per position
  let riskPerPosition;
  
  if (shouldScaleRisk) {
    // Scale back risk to stay within max drawdown
    console.log('Scaling back risk to stay within max drawdown');
    riskPerPosition = maxDrawdownAmount / positionCount;
  } else {
    // Use risk per trade - already within max drawdown limits
    console.log('Using risk per trade (within max drawdown limits)');
    riskPerPosition = riskPerTradeAmount;
  }
  
  // Special handling for few positions
  if (positionCount <= 3) {
    // With few positions, we need to balance between max drawdown and risk per trade
    // This ensures proper risk allocation when portfolio is concentrated
    const balancedRisk = maxDrawdownAmount / positionCount;
    
    // Take the smaller of balanced risk or risk per trade
    if (riskPerTradeAmount < balancedRisk) {
      console.log('Using risk per trade for few positions');
      riskPerPosition = riskPerTradeAmount;
    } else {
      console.log('Using balanced risk for few positions');
      riskPerPosition = balancedRisk;
    }
  }
  
  console.log('Final risk per position:', riskPerPosition);
  
  // Calculate stop losses based on risk allocation
  return holdings.map(pos => {
    let expectedStopLoss = null;
    let expectedStopLossPercent = null;
    
    if (pos.value > 0 && pos.shares !== 0 && pos.currentPrice > 0) {
      // Check if position is short (from stored preference or auto-detect)
      const isShort = positionTypes[pos.symbol] || (pos.strategy === 'short');
      
      // Calculate risk amount for this position
      const positionRiskAmount = riskPerPosition;
      
      // Account for share quantity for proper risk allocation
      const absShares = Math.abs(pos.shares);
      const lossPerShare = positionRiskAmount / absShares;
      
      if (isShort) {
        // For short positions, stop loss is ABOVE current price
        expectedStopLoss = pos.currentPrice + lossPerShare;
        
        // Calculate percentage increase from current price
        expectedStopLossPercent = ((expectedStopLoss - pos.currentPrice) / pos.currentPrice) * 100;
      } else {
        // For long positions, stop loss is BELOW current price
        expectedStopLoss = Math.max(0, pos.currentPrice - lossPerShare);
        
        // Calculate percentage drop from current price
        expectedStopLossPercent = ((pos.currentPrice - expectedStopLoss) / pos.currentPrice) * 100;
      }
      
      // Log the calculated stop loss
      console.log(`${pos.symbol}: ${isShort ? 'SHORT' : 'LONG'} position - Stop loss: ${expectedStopLoss.toFixed(2)}, Risk: ${positionRiskAmount.toFixed(2)}`);
    }
    
    return {
      ...pos,
      expectedStopLoss,
      expectedStopLossPercent
    };
  });
};

/**
 * Calculate total risk exposure based on current stop losses
 * 
 * @param {Array} holdings - Array of position objects with stop losses
 * @param {Number} accountBalance - Total account balance
 * @returns {Object} - Risk exposure statistics
 */
export const calculateRiskExposure = (holdings, accountBalance) => {
  let totalRiskAmount = 0;
  let totalRiskPercent = 0;
  let highestRiskPosition = null;
  let highestRiskAmount = 0;
  
  // Calculate risk for each position
  const positionsWithRisk = holdings.map(position => {
    if (!position.currentPrice || position.shares === 0) {
      return { ...position, riskAmount: 0, riskPercent: 0 };
    }
    
    const isShort = positionTypes[position.symbol] || (position.strategy === 'short');
    const absShares = Math.abs(position.shares);
    
    // If max expected stop loss percent is set, apply it to calculate effective stop loss
    let effectiveStopLoss = position.expectedStopLoss;
    if (position.currentPrice && riskParameters.maxExpectedStopLossPercent) {
      const maxAllowedPercentStopLoss = riskParameters.maxExpectedStopLossPercent;
      
      // Calculate max allowed stop loss price based on percentage
      let maxAllowedStopLossPrice;
      if (isShort) {
        // For shorts: stop loss is above current price
        maxAllowedStopLossPrice = position.currentPrice * (1 + maxAllowedPercentStopLoss / 100);
      } else {
        // For longs: stop loss is below current price
        maxAllowedStopLossPrice = position.currentPrice * (1 - maxAllowedPercentStopLoss / 100);
      }
      
      // Use the original stop loss or the max allowed, whichever is less risky
      if (effectiveStopLoss) {
        if (isShort) {
          // For shorts: lower stop loss price is better (less risky)
          effectiveStopLoss = Math.min(effectiveStopLoss, maxAllowedStopLossPrice);
        } else {
          // For longs: higher stop loss price is better (less risky)
          effectiveStopLoss = Math.max(effectiveStopLoss, maxAllowedStopLossPrice);
        }
      } else {
        effectiveStopLoss = maxAllowedStopLossPrice;
      }
    }
    
    // If no effective stop loss after all calculations, return zero risk
    if (!effectiveStopLoss) {
      return { ...position, riskAmount: 0, riskPercent: 0 };
    }
    
    // Calculate risk amount based on position type
    let riskAmount;
    if (isShort) {
      // For shorts: risk is when price goes up to stop loss
      riskAmount = (effectiveStopLoss - position.currentPrice) * absShares;
    } else {
      // For longs: risk is when price goes down to stop loss
      riskAmount = (position.currentPrice - effectiveStopLoss) * absShares;
    }
    
    // Calculate risk as percentage of account
    const riskPercent = (riskAmount / accountBalance) * 100;
    
    // Track highest risk position
    if (riskAmount > highestRiskAmount) {
      highestRiskAmount = riskAmount;
      highestRiskPosition = position.symbol;
    }
    
    // Add to total
    totalRiskAmount += riskAmount;
    
    return {
      ...position,
      effectiveStopLoss,
      riskAmount,
      riskPercent
    };
  });
  
  // Calculate total risk as percentage of account
  totalRiskPercent = (totalRiskAmount / accountBalance) * 100;
  
  return {
    positionsWithRisk,
    totalRiskAmount,
    totalRiskPercent,
    highestRiskPosition,
    highestRiskAmount,
    maxDrawdownTarget: riskParameters.maxDrawdown,
    withinMaxDrawdown: totalRiskPercent <= riskParameters.maxDrawdown
  };
}; 