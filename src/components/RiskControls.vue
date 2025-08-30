<template>
  <div class="risk-controls-container">
    <!-- Account Statistics -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-title">Total Account Balance</div>
        <div class="stat-value">{{ formatCurrency(accountData.balance) }}</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-title">Total P&L</div>
        <div class="stat-value" :class="accountData.totalProfitLoss >= 0 ? 'profit' : 'loss'">
          {{ formatCurrency(accountData.totalProfitLoss) }}
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-title">P&L %</div>
        <div class="stat-value" :class="accountData.totalProfitLossPercent >= 0 ? 'profit' : 'loss'">
          {{ formatPercent(accountData.totalProfitLossPercent) }}
        </div>
      </div>
    </div>
    
    <!-- Risk Parameters -->
    <div class="risk-parameters">
      <div class="parameter-section">
        <div class="parameter-header">
          Maximum Drawdown: {{ accountData.maxDrawdown }}%
        </div>
        <div class="parameter-controls">
          <div class="slider-container">
            <input
              type="range"
              :min="1"
              :max="20"
              :step="0.5"
              v-model.number="maxDrawdownValue"
              @change="handleMaxDrawdownChange"
            />
          </div>
          <div class="value-input">
            <input
              type="number"
              :min="1"
              :max="20"
              :step="0.5"
              v-model.number="maxDrawdownValue"
              @change="handleMaxDrawdownChange"
            />
          </div>
          <div class="label">% of portfolio</div>
        </div>
      </div>
      
      <div class="parameter-section">
        <div class="parameter-header">
          Risk Per Trade: {{ accountData.riskPerTrade }}%
        </div>
        <div class="parameter-controls">
          <div class="slider-container">
            <input
              type="range"
              :min="0.1"
              :max="5"
              :step="0.1"
              v-model.number="riskPerTradeValue"
              @change="handleRiskPerTradeChange"
            />
          </div>
          <div class="value-input">
            <input
              type="number"
              :min="0.1"
              :max="5"
              :step="0.1"
              v-model.number="riskPerTradeValue"
              @change="handleRiskPerTradeChange"
            />
          </div>
          <div class="label">% of portfolio</div>
        </div>
      </div>

      <!-- New: Max Expected Stop Loss Parameter -->
      <div class="parameter-section">
        <div class="parameter-header">
          Max Expected SL %: {{ accountData.maxExpectedStopLossPercent || 0 }}%
        </div>
        <div class="parameter-controls">
          <div class="slider-container">
            <input
              type="range"
              :min="0.5"
              :max="10"
              :step="0.1"
              v-model.number="maxExpectedStopLossPercentValue"
              @change="handleMaxExpectedStopLossPercentChange"
            />
          </div>
          <div class="value-input">
            <input
              type="number"
              :min="0.5"
              :max="10"
              :step="0.1"
              v-model.number="maxExpectedStopLossPercentValue"
              @change="handleMaxExpectedStopLossPercentChange"
            />
          </div>
          <div class="label">% of position</div>
        </div>
      </div>
    </div>
    
    <!-- Risk Calculations -->
    <div class="risk-calculations">
      <div class="stat-card">
        <div class="stat-title">Maximum Portfolio Loss</div>
        <div class="stat-value loss">{{ formatCurrency(maxDrawdownAmount) }}</div>
      </div>
      
      <div class="stat-card">
        <div class="stat-title">Risk per Trade</div>
        <div class="stat-value loss">{{ formatCurrency(riskPerTradeAmount) }}</div>
      </div>
      
      <!-- Current Risk Exposure -->
      <div class="stat-card" :class="{'risk-exceeded': !riskExposure.withinMaxDrawdown}">
        <div class="stat-title">
          Current Total Risk
          <span v-if="!riskExposure.withinMaxDrawdown" class="risk-warning">
            (Exceeds Maximum Drawdown)
          </span>
        </div>
        <div class="stat-value loss">
          {{ formatCurrency(riskExposure.totalRiskAmount) }}
          <span class="risk-percent">({{ formatPercent(riskExposure.totalRiskPercent) }})</span>
        </div>
      </div>
      
      <!-- Highest risk position -->
      <div class="stat-card" v-if="riskExposure.highestRiskPosition">
        <div class="stat-title">Highest Risk Position</div>
        <div class="stat-value">
          {{ riskExposure.highestRiskPosition }}
          <span class="risk-amount loss">
            {{ formatCurrency(riskExposure.highestRiskAmount) }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- Risk Status -->
    <div class="risk-status" v-if="stockHoldings.length > 0">
      <div class="risk-status-card" :class="riskExposure.withinMaxDrawdown ? 'safe' : 'danger'">
        <div class="status-icon">
          <i :class="riskExposure.withinMaxDrawdown ? 'fa fa-check-circle' : 'fa fa-warning'"></i>
        </div>
        <div class="status-message">
          <div class="status-title">
            {{ riskExposure.withinMaxDrawdown ? 'Risk Within Limits' : 'Risk Exceeds Limits' }}
          </div>
          <div class="status-details">
            Total risk exposure {{ formatPercent(riskExposure.totalRiskPercent) }} 
            {{ riskExposure.withinMaxDrawdown ? 'is within' : 'exceeds' }} 
            maximum drawdown of {{ formatPercent(accountData.maxDrawdown) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';
import { calculateRiskExposure } from '../utils/riskUtils';

export default {
  name: 'RiskControls',
  props: {
    accountData: {
      type: Object,
      required: true
    },
    stockHoldings: {
      type: Array,
      required: true
    }
  },
  emits: ['max-drawdown-change', 'risk-per-trade-change', 'max-expected-stop-loss-percent-change'],
  setup(props, { emit }) {
    // Local state for slider/input values
    const maxDrawdownValue = ref(props.accountData.maxDrawdown);
    const riskPerTradeValue = ref(props.accountData.riskPerTrade);
    const maxExpectedStopLossPercentValue = ref(props.accountData.maxExpectedStopLossPercent || 5);
    
    // Watch for prop changes to update local sliders
    watch(() => props.accountData.maxDrawdown, (newVal) => {
      maxDrawdownValue.value = newVal;
    });
    
    watch(() => props.accountData.riskPerTrade, (newVal) => {
      riskPerTradeValue.value = newVal;
    });
    
    watch(() => props.accountData.maxExpectedStopLossPercent, (newVal) => {
      if (newVal !== undefined) {
        maxExpectedStopLossPercentValue.value = newVal;
      }
    });
    
    // Computed values for dollar amounts
    const maxDrawdownAmount = computed(() => {
      return props.accountData.balance * (props.accountData.maxDrawdown / 100);
    });
    
    const riskPerTradeAmount = computed(() => {
      return props.accountData.balance * (props.accountData.riskPerTrade / 100);
    });
    
    // Calculate current risk exposure
    const riskExposure = computed(() => {
      return calculateRiskExposure(props.stockHoldings, props.accountData.balance);
    });
    
    // Format utilities
    const formatCurrency = (value) => {
      if (value === null || value === undefined) return '-';
      return new Intl.NumberFormat('en-US', { 
        style: 'currency', 
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(value);
    };
    
    const formatPercent = (value) => {
      if (value === null || value === undefined) return '-';
      return new Intl.NumberFormat('en-US', { 
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(value / 100);
    };
    
    // Event handlers
    const handleMaxDrawdownChange = () => {
      emit('max-drawdown-change', maxDrawdownValue.value);
    };
    
    const handleRiskPerTradeChange = () => {
      emit('risk-per-trade-change', riskPerTradeValue.value);
    };
    
    const handleMaxExpectedStopLossPercentChange = () => {
      emit('max-expected-stop-loss-percent-change', maxExpectedStopLossPercentValue.value);
    };
    
    return {
      maxDrawdownValue,
      riskPerTradeValue,
      maxExpectedStopLossPercentValue,
      maxDrawdownAmount,
      riskPerTradeAmount,
      riskExposure,
      handleMaxDrawdownChange,
      handleRiskPerTradeChange,
      handleMaxExpectedStopLossPercentChange,
      formatCurrency,
      formatPercent
    };
  }
};
</script>

<style scoped>
.risk-controls-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.stat-card {
  border: 1px solid #3a3a3a;
  border-radius: 4px;
  padding: 15px;
  background-color: #2a2a2a;
}

.stat-title {
  font-size: 14px;
  color: #a0a0a0;
  margin-bottom: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #e0e0e0;
}

.profit {
  color: #4caf50;
}

.loss {
  color: #f44336;
}

.risk-warning {
  color: #ff9800;
  font-size: 12px;
  margin-left: 5px;
}

.risk-percent {
  font-size: 14px;
  margin-left: 5px;
}

.risk-exceeded {
  border-color: #f44336;
  box-shadow: 0 0 0 1px rgba(244, 67, 54, 0.3);
}

.risk-parameters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.parameter-section {
  background-color: #2a2a2a;
  border-radius: 4px;
  padding: 15px;
  border: 1px solid #3a3a3a;
}

.parameter-header {
  font-weight: 500;
  margin-bottom: 10px;
  color: #e0e0e0;
}

.parameter-controls {
  display: grid;
  grid-template-columns: 1fr 80px 100px;
  gap: 10px;
  align-items: center;
}

.slider-container {
  width: 100%;
}

.slider-container input {
  width: 100%;
  background-color: #4a6cf7;
}

.value-input input {
  width: 100%;
  padding: 5px;
  border-radius: 4px;
  border: 1px solid #3a3a3a;
  background-color: #1e1e1e;
  color: #e0e0e0;
}

.label {
  color: #a0a0a0;
}

.risk-calculations {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.risk-status {
  margin-top: 10px;
}

.risk-status-card {
  padding: 15px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 15px;
}

.risk-status-card.safe {
  background-color: rgba(76, 175, 80, 0.1);
  border: 1px solid rgba(76, 175, 80, 0.3);
}

.risk-status-card.danger {
  background-color: rgba(244, 67, 54, 0.1);
  border: 1px solid rgba(244, 67, 54, 0.3);
}

.status-icon {
  font-size: 24px;
}

.risk-status-card.safe .status-icon {
  color: #4caf50;
}

.risk-status-card.danger .status-icon {
  color: #f44336;
}

.status-message {
  display: flex;
  flex-direction: column;
}

.status-title {
  font-size: 16px;
  font-weight: 500;
}

.risk-status-card.safe .status-title {
  color: #4caf50;
}

.risk-status-card.danger .status-title {
  color: #f44336;
}

.status-details {
  font-size: 14px;
  color: #a0a0a0;
}

@media (max-width: 768px) {
  .stats-grid,
  .risk-parameters,
  .risk-calculations {
    grid-template-columns: 1fr;
  }
  
  .parameter-controls {
    grid-template-columns: 1fr;
  }
}
</style> 