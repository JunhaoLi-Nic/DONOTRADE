<template>
  <div class="risk-summary">
    <div class="risk-summary-header">
      <h3>Total Risk Summary</h3>
    </div>
    <div class="risk-summary-content">
      <div class="risk-item">
        <span class="risk-label">Open Orders Stop Loss Risk:</span>
        <span class="risk-value">{{ formatCurrency(totalStopLossRisk) }}</span>
      </div>
      <div class="risk-item">
        <span class="risk-label">Current Positions Stop Loss Risk:</span>
        <span class="risk-value">{{ formatCurrency(holdingsStopLossRisk) }}</span>
      </div>
      <div class="risk-item total">
        <span class="risk-label">Total Combined Risk:</span>
        <span class="risk-value">{{ formatCurrency(totalStopLossRisk + holdingsStopLossRisk) }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent } from 'vue'
import { formatCurrency } from '../utils/orderUtils'

export default defineComponent({
  name: 'RiskSummary',
  props: {
    totalStopLossRisk: {
      type: Number,
      default: 0
    },
    holdingsStopLossRisk: {
      type: Number,
      default: 0
    }
  },
  setup() {
    return {
      formatCurrency
    }
  }
})
</script>

<style scoped>
.risk-summary {
  background-color: #1a1a1a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
}

.risk-summary-header {
  margin-bottom: 16px;
}

.risk-summary-header h3 {
  color: #e0e0e0;
  font-size: 18px;
  font-weight: 500;
  margin: 0;
}

.risk-summary-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.risk-item.total {
  border-top: 1px solid #3a3a3a;
  padding-top: 12px;
  margin-top: 8px;
  font-weight: 600;
}

.risk-label {
  color: #a0a0a0;
  font-size: 14px;
}

.risk-value {
  color: #f44336;
  font-size: 16px;
  font-weight: 500;
}

.risk-item.total .risk-label {
  color: #e0e0e0;
  font-weight: 600;
}

.risk-item.total .risk-value {
  font-size: 18px;
  font-weight: 600;
}
</style>