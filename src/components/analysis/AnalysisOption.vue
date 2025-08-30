<script setup>
import { ref } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart,
  LineElement,
  PointElement,
  LinearScale,
  Title,
  Tooltip,
  Legend,
  CategoryScale
} from 'chart.js'
Chart.register(LineElement, PointElement, LinearScale, Title, Tooltip, Legend, CategoryScale)

const symbol = ref('')
const expiry = ref('')
const strike = ref('')
const loading = ref(false)
const result = ref(null)
const error = ref('')
const chartData = ref(null)
const chartOptions = ref({
  responsive: true,
  plugins: {
    legend: { display: true },
    title: { display: true, text: 'Option Rolling Analysis: Before vs After' }
  },
  scales: {
    x: { title: { display: true, text: 'Stock Price at Expiration ($)' }, grid: { color: '#444' } },
    y: { title: { display: true, text: 'Profit ($)' }, grid: { color: '#444' } }
  }
})

async function calculateOptionRolling() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    const response = await fetch('/api/option/rolling', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol: symbol.value, expiry: expiry.value, strike: strike.value })
    })
    if (!response.ok) throw new Error('API error')
    const data = await response.json()
    result.value = data
    updateChart(data)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function updateChart(data) {
  if (!data) return
  chartData.value = {
    labels: data.S,
    datasets: [
      {
        label: `Before Roll (${data.strike_old}C)`,
        data: data.profit_old,
        borderColor: '#3b82f6',
        borderDash: [4,2],
        fill: false,
        pointRadius: 0
      },
      ...Object.entries(data.scenarios).map(([dir, v]) => ({
        label: `After Roll (${v.strike_new}C, ${dir})`,
        data: v.profit_new,
        borderColor: dir === 'up' ? '#ef4444' : dir === 'down' ? '#22c55e' : '#f59e42',
        fill: false,
        pointRadius: 0
      }))
    ]
  }
}
</script>

<template>
  <div class="option-analysis-outer">
    <div class="option-analysis-card">
      <h2>Option Rolling Analysis</h2>
      <form class="option-form" @submit.prevent="calculateOptionRolling">
        <div class="form-row">
          <label for="symbol">Symbol</label>
          <input id="symbol" v-model="symbol" required placeholder="e.g. AAPL" autocomplete="off" />
        </div>
        <div class="form-row">
          <label for="expiry">Expiry</label>
          <input id="expiry" v-model="expiry" required placeholder="YYYY-MM-DD" autocomplete="off" />
        </div>
        <div class="form-row">
          <label for="strike">Strike Price</label>
          <input id="strike" v-model="strike" required type="number" placeholder="e.g. 425" autocomplete="off" />
        </div>
        <button class="analyze-btn" type="submit" :disabled="loading">{{ loading ? 'Analyzing...' : 'Analyze' }}</button>
      </form>
      <div v-if="error" class="error">{{ error }}</div>
    </div>
    <div class="chart-card">
      <h3>Profit/Loss Comparison</h3>
      <div v-if="loading" class="chart-loading-overlay">
        <div class="spinner"></div>
      </div>
      <div v-if="!chartData && !loading" class="no-data">No analysis yet. Fill the form and click Analyze.</div>
      <div v-if="chartData && !loading">
        <Line :data="chartData" :options="chartOptions" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.option-analysis-outer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  margin-top: 2rem;
}
.option-analysis-card {
  background: #181a20;
  color: #f3f4f6;
  padding: 2rem 2.5rem 1.5rem 2.5rem;
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.25);
  min-width: 350px;
  max-width: 420px;
  width: 100%;
  margin-bottom: 0.5rem;
}
.option-analysis-card h2 {
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}
.option-form {
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}
.form-row {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
label {
  font-size: 1rem;
  font-weight: 500;
  color: #cbd5e1;
}
input {
  padding: 0.5rem 0.8rem;
  border-radius: 6px;
  border: 1px solid #333;
  background: #23272f;
  color: #f3f4f6;
  font-size: 1rem;
  outline: none;
  transition: border 0.2s;
}
input:focus {
  border: 1.5px solid #3b82f6;
}
.analyze-btn {
  margin-top: 0.5rem;
  padding: 0.6rem 2.2rem;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.analyze-btn:disabled {
  background: #64748b;
  cursor: not-allowed;
}
.error {
  color: #ef4444;
  margin-top: 1rem;
  font-size: 1rem;
}
.chart-card {
  background: #181a20;
  color: #f3f4f6;
  padding: 1.5rem 2rem 2rem 2rem;
  border-radius: 16px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.18);
  min-width: 350px;
  max-width: 900px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.chart-card h3 {
  margin-bottom: 1.2rem;
  font-size: 1.2rem;
  font-weight: 500;
  letter-spacing: 0.01em;
}
.no-data {
  color: #64748b;
  font-size: 1.1rem;
  margin-top: 2rem;
  text-align: center;
}
.chart-loading-overlay {
  position: absolute;
  left: 0; right: 0; top: 0; bottom: 0;
  background: rgba(24,26,32,0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  border-radius: 16px;
}
.spinner {
  border: 4px solid #23272f;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  width: 38px;
  height: 38px;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
@media (max-width: 700px) {
  .option-analysis-card, .chart-card {
    min-width: 90vw;
    max-width: 98vw;
    padding: 1rem;
  }
}
</style> 