<script setup>
import { ref, watch, onMounted } from 'vue'
import stockDataService from '../services/stockDataService.js'

const lookbackDays = ref(90)
const correlationMatrix = ref(null)
const correlationTickers = ref([])
const loading = ref(false)
const error = ref(null)
const colorScale = [
  { color: "#053061", label: "Strong Negative (-1, -0.8)" },   // Dark Blue
  { color: "#2166ac", label: "Negative (-0.8, -0.5)" },        // Blue
  { color: "#4393c3", label: "Weak Negative (-0.5, 0)" },      // Light Blue
  { color: "#4daf4a", label: "Neutral (0, 0.5)" },             // Green
  { color: "#f4a582", label: "Weak Positive (0.5, 0.8)" },     // Light Red
  { color: "#ca0020", label: "Positive (0.8, 1)" },            // Red
  { color: "#67001f", label: "Strong Positive (1)" }           // Dark Red
]

const props = defineProps({
    stockholdings: [String]
})

// Get the background color for a correlation value
const getCorrelationColor = (value) => {
  if (value === null || value === undefined) {
    return '#000000'
  }
  // Handle the last "1" value
  if (value === 1) {
    return colorScale[colorScale.length - 1].color
  }
  for (let i = 0; i < colorScale.length - 1; i++) {
    // Check if value is within the interval
    const match = colorScale[i].label.match(/\(([-\d.]+), ([-\d.]+)\)/)
    if (match) {
      const min = parseFloat(match[1])
      const max = parseFloat(match[2])
      if (value > min && value <= max) {
        return colorScale[i].color
      }
    }
  }
  // fallback color
  return '#000000'
}

// Calculate the average of an array of correlation values
const getAverage = (arr) => {
  if (!arr || !arr.length) return '-'
  const valid = arr.filter(v => v !== null && v !== undefined)
  if (!valid.length) return '-'
  const sum = valid.reduce((a, b) => a + b, 0)
  return (sum / valid.length).toFixed(2)
}

// Calculate the average correlation coefficient for the whole matrix (excluding diagonal)
const getPortfolioAverageCorrelation = () => {
  if (!correlationMatrix.value || !correlationMatrix.value.length) return '-'
  let sum = 0
  let count = 0
  for (let i = 0; i < correlationMatrix.value.length; i++) {
    for (let j = 0; j < correlationMatrix.value[i].length; j++) {
      if (i !== j && correlationMatrix.value[i][j] !== null && correlationMatrix.value[i][j] !== undefined) {
        sum += correlationMatrix.value[i][j]
        count++
      }
    }
  }
  if (count === 0) return '-'
  return (sum / count).toFixed(2)
}

const getCorrelationMatrix = async () => {
    if (!props.stockholdings || props.stockholdings.length === 0) {
        correlationMatrix.value = null
        correlationTickers.value = []
        return
    }
    loading.value = true
    error.value = null
    try {
        const result = await stockDataService.getCorrelationMatrix(props.stockholdings, lookbackDays.value)
        correlationMatrix.value = result.matrix
        correlationTickers.value = result.tickers
    } catch (e) {
        error.value = 'Failed to fetch correlation matrix.'
        correlationMatrix.value = null
        correlationTickers.value = []
    } finally {
        loading.value = false
    }
}

onMounted(getCorrelationMatrix)
watch([() => props.stockholdings, lookbackDays], getCorrelationMatrix)
</script>

<template>
    <div>
        <div class="color-scale-container">
            <div class="color-scale-left">
                <div class="section-title"> 
                    Correlation Coefficient Risk Assessment 
                </div>
            </div>
            <div class="color-scale-right">
                <div class="color-scale-items">
                    <div v-for="(item, index) in colorScale" :key="index" :style="{ backgroundColor: item.color }" class="color-scale-item"></div>
                </div>
                <div class="color-scale-labels">
                    <div v-for="(item, index) in colorScale" :key="index" class="color-scale-label">{{ item.label }}</div>
                </div>
            </div>
        </div>
        <label>
        Lookback Period: {{ lookbackDays }} days
            <input 
                type="range"
                min="30"
                max="1825"
                step="1"
                v-model="lookbackDays"
            />
        </label>
        <div v-if="loading">Loading correlation matrix...</div>
        <div v-if="error" style="color: red;">{{ error }}</div>
        <div v-if="correlationMatrix && correlationTickers.length">
            <div class="portfolio-average">
              Portfolio Average Correlation: <b>{{ getPortfolioAverageCorrelation() }}</b>
            </div>
            <table class="cor-table">
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th v-for="(ticker, index) in correlationTickers" :key="index">
                            {{ ticker }}
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(row, rowIndex) in correlationMatrix" :key="rowIndex">
                        <td>{{ correlationTickers[rowIndex] }}</td>
                        <td v-for="(value, colIndex) in row" :key="colIndex" :style="{ backgroundColor: getCorrelationColor(value) }">
                            {{ value !== null && value !== undefined ? value.toFixed(2) : '-' }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<style>
.color-scale-container {
  display: flex;
  flex-direction: row;
  width: 100%;
  align-items: flex-start;
  margin-bottom: 20px;
}
.color-scale-left {
  flex: 0 0 300px; 
  display: flex;
  align-items: flex-start;
}
.color-scale-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.cor-table{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}
.section-title{
    font-size: 16px;
    font-weight: 500;
    color: #e0e0e0;
    margin-bottom: 10px;
}
.table-container {
    width: 100%;
    overflow-x:auto;
    margin-bottom: 24px;
}
input[type="range"] {
  width: 300px;
  margin-bottom: 30px;
}
.color-scale-items {
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
  margin-bottom: 2px;
}
.color-scale-item {
  width: 90px;
  height: 16px;
  margin: 0 2px;
  border-radius: 2px;
  border: 1px solid #888;
}
.color-scale-labels {
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
  margin-bottom: 10px;
}
.color-scale-label {
  width: 90px;
  text-align: center;
  font-size: 12px;
  color: #e0e0e0;
  margin: 0 2px;
}
.portfolio-average {
  font-size: 16px;
  font-weight: bold;
  margin: 12px 0;
  color: #4daf4a;
}
</style>