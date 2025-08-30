<template>
  <div class="consecutive-moves-chart">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading chart data...</p>
    </div>
    <div v-else-if="error" class="error">
      <div class="error-icon">⚠️</div>
      <div class="error-message">
        <h4>Unable to Load Consecutive Moves Analysis</h4>
        <p>{{ error }}</p>
        <p>
          This could be due to:
        </p>
        <ul>
          <li>Insufficient data for the selected ticker</li>
          <li>Server-side calculation error</li>
          <li>Network connectivity issues</li>
        </ul>
        <button @click="retryFetch" class="retry-button">
          <i class="uil uil-redo"></i> Retry
        </button>
      </div>
    </div>
    <div v-else>
      <div class="chart-header">
        <h3>{{ ticker }} Consecutive {{ directionLabel }} Days Analysis</h3>
        <div class="chart-controls">
          <div class="control-group">
            <label>Direction:</label>
            <select v-model="selectedDirection" @change="updateChart">
              <option value="up">Up Days</option>
              <option value="down">Down Days</option>
            </select>
          </div>
          
          <div class="control-group">
            <label>Min Days:</label>
            <div class="editable-select">
              <select 
                v-model="minDaysValue" 
                @change="handleMinDaysChange"
                class="select-input"
                :class="{'hidden': isMinDaysCustom}"
              >
                <option :value="2">2</option>
                <option :value="3">3</option>
                <option :value="4">4</option>
                <option value="custom">Custom...</option>
              </select>
              <input 
                v-model="customMinDays"
                type="number" 
                class="custom-input"
                :class="{'active': isMinDaysCustom}"
                @blur="handleCustomMinDaysBlur"
                @keydown.enter="handleCustomMinDaysEnter"
                ref="minDaysInput"
                min="1"
                max="10"
                placeholder="Enter days"
              />
              <button 
                v-if="isMinDaysCustom" 
                class="edit-btn" 
                @click="handleCustomMinDaysEnter"
              >
                Set
              </button>
            </div>
          </div>
          
          <div class="control-group">
            <label>Max Days:</label>
            <div class="editable-select">
              <select 
                v-model="maxDaysValue" 
                @change="handleMaxDaysChange"
                class="select-input"
                :class="{'hidden': isMaxDaysCustom}"
              >
                <option :value="5">5</option>
                <option :value="7">7</option>
                <option :value="10">10</option>
                <option :value="15">15</option>
                <option value="custom">Custom...</option>
              </select>
              <input 
                v-model="customMaxDays"
                type="number" 
                class="custom-input"
                :class="{'active': isMaxDaysCustom}"
                @blur="handleCustomMaxDaysBlur"
                @keydown.enter="handleCustomMaxDaysEnter"
                ref="maxDaysInput"
                min="3"
                max="30"
                placeholder="Enter days"
              />
              <button 
                v-if="isMaxDaysCustom" 
                class="edit-btn" 
                @click="handleCustomMaxDaysEnter"
              >
                Set
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div class="charts-container">
        <div class="chart-wrapper">
          <h4>Next Day Probability</h4>
          <div class="chart-container">
            <canvas ref="probabilityChartCanvas"></canvas>
          </div>
        </div>
        <div class="chart-wrapper">
          <h4>Average Next Day Return</h4>
          <div class="chart-container">
            <canvas ref="returnChartCanvas"></canvas>
          </div>
        </div>
      </div>
      
      <div class="consecutive-stats">
        <table class="stats-table">
          <thead>
            <tr>
              <th>Consecutive Days</th>
              <th>Occurrences</th>
              <th>Next Day Probability</th>
              <th>Avg Next Day Return</th>
              <th>Std Dev</th>
              <th>Min Return</th>
              <th>Max Return</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(stats, days) in probabilities" :key="days">
              <td>{{ days }} days</td>
              <td>{{ stats.count }}</td>
              <td :class="getProbabilityClass(stats.next_day_probability)">
                {{ (stats.next_day_probability * 100).toFixed(1) }}%
              </td>
              <td :class="getReturnClass(stats.avg_next_day_return)">
                {{ (stats.avg_next_day_return * 100).toFixed(2) }}%
              </td>
              <td>{{ stats.std_dev ? (stats.std_dev * 100).toFixed(2) + '%' : 'N/A' }}</td>
              <td :class="getReturnClass(stats.min_return)">
                {{ stats.min_return ? (stats.min_return * 100).toFixed(2) + '%' : 'N/A' }}
              </td>
              <td :class="getReturnClass(stats.max_return)">
                {{ stats.max_return ? (stats.max_return * 100).toFixed(2) + '%' : 'N/A' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div v-if="selectedStreak && selectedStreak.examples" class="streak-examples">
        <h4>Examples of {{ selectedStreak.days }}-Day {{ directionLabel }} Streaks</h4>
        <table class="examples-table">
          <thead>
            <tr>
              <th>End Date</th>
              <th>Next Day</th>
              <th>Return</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(example, index) in selectedStreak.examples.slice(0, 5)" :key="index">
              <td>{{ example.end_date }}</td>
              <td :class="example.continued ? 'continued' : 'broken'">
                {{ example.continued ? 'Continued' : 'Broken' }}
              </td>
              <td :class="getReturnClass(example.next_day_return)">
                {{ (example.next_day_return * 100).toFixed(2) }}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import Chart from 'chart.js/auto';
import StockAnalysisClient from '../../../utils/stock-analysis-client';

export default {
  name: 'ConsecutiveMovesChart',
  props: {
    ticker: {
      type: String,
      required: true
    },
    startDate: {
      type: String,
      default: null
    },
    endDate: {
      type: String,
      default: null
    },
    minDays: {
      type: Number,
      default: 2
    },
    maxDays: {
      type: Number,
      default: 10
    }
  },
  setup(props) {
    const probabilityChartCanvas = ref(null);
    const returnChartCanvas = ref(null);
    const probabilityChart = ref(null);
    const returnChart = ref(null);
    const loading = ref(true);
    const error = ref(null);
    const selectedDirection = ref('down');
    const minDaysValue = ref(props.minDays);
    const maxDaysValue = ref(props.maxDays);
    const customMinDays = ref(props.minDays);
    const customMaxDays = ref(props.maxDays);
    const probabilities = ref({});
    const selectedStreak = ref(null);
    const isMinDaysCustom = ref(false);
    const isMaxDaysCustom = ref(false);
    const minDaysInput = ref(null);
    const maxDaysInput = ref(null);

    const directionLabel = computed(() => {
      return selectedDirection.value === 'up' ? 'Up' : 'Down';
    });

    const handleMinDaysChange = () => {
      if (minDaysValue.value === 'custom') {
        isMinDaysCustom.value = true;
        nextTick(() => {
          if (minDaysInput.value) {
            minDaysInput.value.focus();
          }
        });
      } else {
        isMinDaysCustom.value = false;
        updateChart();
      }
    };

    const handleMaxDaysChange = () => {
      if (maxDaysValue.value === 'custom') {
        isMaxDaysCustom.value = true;
        nextTick(() => {
          if (maxDaysInput.value) {
            maxDaysInput.value.focus();
          }
        });
      } else {
        isMaxDaysCustom.value = false;
        updateChart();
      }
    };

    const handleCustomMinDaysBlur = () => {
      applyCustomMinDays();
    };

    const handleCustomMinDaysEnter = () => {
      applyCustomMinDays();
      isMinDaysCustom.value = false;
    };

    const handleCustomMaxDaysBlur = () => {
      applyCustomMaxDays();
    };

    const handleCustomMaxDaysEnter = () => {
      applyCustomMaxDays();
      isMaxDaysCustom.value = false;
    };

    const applyCustomMinDays = () => {
      const value = parseInt(customMinDays.value);
      if (!isNaN(value) && value >= 1 && value < maxDaysValue.value) {
        minDaysValue.value = value;
        isMinDaysCustom.value = false;
        updateChart();
      } else {
        // Reset to previous valid value
        customMinDays.value = minDaysValue.value;
      }
    };

    const applyCustomMaxDays = () => {
      const value = parseInt(customMaxDays.value);
      if (!isNaN(value) && value > minDaysValue.value && value <= 30) {
        maxDaysValue.value = value;
        isMaxDaysCustom.value = false;
        updateChart();
      } else {
        // Reset to previous valid value
        customMaxDays.value = maxDaysValue.value;
      }
    };

    // Watch for dropdown selection changes to focus the input field
    watch(minDaysValue, (newValue) => {
      if (newValue === 'custom') {
        nextTick(() => {
          if (minDaysInput.value) {
            minDaysInput.value.focus();
          }
        });
      }
    });
    
    watch(maxDaysValue, (newValue) => {
      if (newValue === 'custom') {
        nextTick(() => {
          if (maxDaysInput.value) {
            maxDaysInput.value.focus();
          }
        });
      }
    });

    const fetchData = async () => {
      if (!props.ticker) {
        error.value = "No ticker symbol provided";
        loading.value = false;
        return;
      }
      
      loading.value = true;
      error.value = null;
      
      try {
        console.log(`Fetching consecutive analysis for ${props.ticker} with direction ${selectedDirection.value}`);
        
        // Validate dates
        let startDate = props.startDate;
        let endDate = props.endDate;
        
        // Check if dates are in the future
        if (startDate && endDate) {
          const today = new Date().toISOString().split('T')[0];
          
          if (startDate > today) {
            console.log(`Start date ${startDate} is in the future, using today instead`);
            startDate = today;
          }
          
          if (endDate > today) {
            console.log(`End date ${endDate} is in the future, using today instead`);
            endDate = today;
          }
        }
        
        const response = await StockAnalysisClient.getConsecutiveAnalysis(
          props.ticker,
          selectedDirection.value,
          minDaysValue.value,
          maxDaysValue.value,
          startDate,
          endDate
        );
        
        if (!response || !response.probabilities) {
          throw new Error('Invalid response data format');
        }
        
        // Check if we have any data
        if (Object.keys(response.probabilities).length === 0) {
          throw new Error('No consecutive patterns found in the selected date range');
        }
        
        probabilities.value = response.probabilities;
        
        // Select the first streak for examples display
        const firstStreakDays = Object.keys(response.probabilities)[0];
        if (firstStreakDays) {
          selectedStreak.value = {
            days: firstStreakDays,
            ...response.probabilities[firstStreakDays]
          };
        }
        
        // Wait for the next DOM update cycle before rendering charts
        await nextTick();
        renderCharts();
      } catch (err) {
        console.error('Error fetching consecutive moves data:', err);
        
        // Extract more useful error message
        let errorMessage = 'Failed to load consecutive moves data';
        
        if (err.response) {
          // Server responded with an error status
          const status = err.response.status;
          const serverMessage = err.response.data?.detail || 'Unknown server error';
          errorMessage = `Server error (${status}): ${serverMessage}`;
        } else if (err.request) {
          // Request was made but no response received
          errorMessage = 'No response from server. Please check your network connection.';
        } else {
          // Error in setting up the request
          errorMessage = `Request error: ${err.message}`;
        }
        
        error.value = errorMessage;
      } finally {
        loading.value = false;
      }
    };

    const renderCharts = async () => {
      // Ensure the DOM is updated and canvas elements are available
      await nextTick();
      // Add a small delay to ensure canvas is fully ready
      setTimeout(() => {
        renderProbabilityChart();
        renderReturnChart();
      }, 50);
    };

    const renderProbabilityChart = () => {
      if (!probabilityChartCanvas.value) {
        console.error('Probability chart canvas element not found');
        return;
      }
      
      if (probabilityChart.value) {
        probabilityChart.value.destroy();
      }

      const ctx = probabilityChartCanvas.value.getContext('2d');
      if (!ctx) {
        console.error('Failed to get probability chart canvas context');
        return;
      }
      
      // Extract data for chart
      const labels = Object.keys(probabilities.value).map(days => `${days} days`);
      const probData = Object.values(probabilities.value).map(data => data.next_day_probability);
      
      // Calculate baseline probability (50% for random)
      const baseline = 0.5;
      
      probabilityChart.value = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Next Day Probability',
              data: probData,
              backgroundColor: probData.map(p => p > baseline ? 'rgba(76, 175, 80, 0.7)' : 'rgba(244, 67, 54, 0.7)'),
              borderColor: probData.map(p => p > baseline ? 'rgba(76, 175, 80, 1)' : 'rgba(244, 67, 54, 1)'),
              borderWidth: 1
            },
            {
              label: 'Baseline (50%)',
              data: Array(labels.length).fill(baseline),
              type: 'line',
              borderColor: 'rgba(128, 128, 128, 0.7)',
              borderWidth: 2,
              borderDash: [5, 5],
              fill: false,
              pointRadius: 0
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              max: 1,
              title: {
                display: true,
                text: 'Probability'
              },
              ticks: {
                callback: value => `${(value * 100).toFixed(0)}%`
              }
            },
            x: {
              title: {
                display: true,
                text: 'Consecutive Days'
              }
            }
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: (context) => {
                  if (context.datasetIndex === 0) {
                    return `Probability: ${(context.raw * 100).toFixed(1)}%`;
                  } else {
                    return `Baseline: ${(context.raw * 100).toFixed(1)}%`;
                  }
                }
              }
            }
          }
        }
      });
    };

    const renderReturnChart = () => {
      if (!returnChartCanvas.value) {
        console.error('Return chart canvas element not found');
        return;
      }
      
      if (returnChart.value) {
        returnChart.value.destroy();
      }

      const ctx = returnChartCanvas.value.getContext('2d');
      if (!ctx) {
        console.error('Failed to get return chart canvas context');
        return;
      }
      
      // Extract data for chart
      const labels = Object.keys(probabilities.value).map(days => `${days} days`);
      const returnData = Object.values(probabilities.value).map(data => data.avg_next_day_return);
      
      returnChart.value = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            label: 'Average Next Day Return',
            data: returnData,
            backgroundColor: returnData.map(r => r > 0 ? 'rgba(76, 175, 80, 0.7)' : 'rgba(244, 67, 54, 0.7)'),
            borderColor: returnData.map(r => r > 0 ? 'rgba(76, 175, 80, 1)' : 'rgba(244, 67, 54, 1)'),
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              title: {
                display: true,
                text: 'Return'
              },
              ticks: {
                callback: value => `${(value * 100).toFixed(2)}%`
              }
            },
            x: {
              title: {
                display: true,
                text: 'Consecutive Days'
              }
            }
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: (context) => {
                  return `Return: ${(context.raw * 100).toFixed(2)}%`;
                }
              }
            }
          }
        }
      });
    };

    const updateChart = () => {
      fetchData();
    };

    const selectStreakExample = (days) => {
      if (probabilities.value[days]) {
        selectedStreak.value = {
          days: days,
          ...probabilities.value[days]
        };
      }
    };

    const getProbabilityClass = (value) => {
      if (value > 0.55) return 'high-probability';
      if (value < 0.45) return 'low-probability';
      return 'neutral-probability';
    };

    const getReturnClass = (value) => {
      if (value > 0.01) return 'positive-return';
      if (value < -0.01) return 'negative-return';
      return 'neutral-return';
    };

    // Add a retry function
    const retryFetch = () => {
      fetchData();
    };

    // Watch for prop changes
    watch(() => props.ticker, (newVal) => {
      if (newVal) fetchData();
    });
    
    watch(() => props.startDate, (newVal, oldVal) => {
      if (newVal !== oldVal && props.ticker) fetchData();
    });
    
    watch(() => props.endDate, (newVal, oldVal) => {
      if (newVal !== oldVal && props.ticker) fetchData();
    });

    onMounted(async () => {
      if (props.ticker) {
        await nextTick();
        fetchData();
      }
    });

    return {
      probabilityChartCanvas,
      returnChartCanvas,
      loading,
      error,
      selectedDirection,
      minDaysValue,
      maxDaysValue,
      customMinDays,
      customMaxDays,
      probabilities,
      selectedStreak,
      isMinDaysCustom,
      isMaxDaysCustom,
      minDaysInput,
      maxDaysInput,
      directionLabel,
      updateChart,
      selectStreakExample,
      getProbabilityClass,
      getReturnClass,
      handleMinDaysChange,
      handleMaxDaysChange,
      handleCustomMinDaysBlur,
      handleCustomMinDaysEnter,
      handleCustomMaxDaysBlur,
      handleCustomMaxDaysEnter,
      retryFetch,
      ticker: props.ticker
    };
  }
};
</script>

<style scoped>
.consecutive-moves-chart {
  position: relative;
  width: 100%;
  margin-bottom: 20px;
}

.loading {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 300px;
  width: 100%;
}

.spinner {
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top: 4px solid var(--blue-color, #2196F3);
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  width: 100%;
  color: #ff5252;
  padding: 20px;
  background-color: rgba(255, 82, 82, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(255, 82, 82, 0.2);
}

.error-icon {
  font-size: 4rem;
  margin-right: 15px;
  color: #ff5252;
}

.error-message {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  text-align: left;
}

.error-message h4 {
  margin-top: 0;
  margin-bottom: 5px;
  color: #ff5252;
}

.error-message p {
  margin-bottom: 5px;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
}

.error-message ul {
  margin-top: 5px;
  margin-bottom: 10px;
  padding-left: 20px;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
}

.error-message li {
  margin-bottom: 5px;
}

.retry-button {
  background-color: #2196F3;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.9rem;
  margin-top: 10px;
}

.retry-button:hover {
  background-color: #1976D2;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.chart-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 5px;
}

.control-group label {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
}

.control-group select {
  background-color: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  color: inherit;
  padding: 4px 8px;
}

/* Custom editable select styles */
.editable-select {
  position: relative;
  display: inline-flex;
  align-items: center;
  min-width: 70px;
}

.editable-select .select-input,
.editable-select .custom-input {
  background-color: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  color: inherit;
  padding: 4px 8px;
  width: 70px;
}

.editable-select .select-input {
  width: 100%;
}

.editable-select .select-input.hidden {
  opacity: 0;
  position: absolute;
  pointer-events: none;
}

.editable-select .custom-input {
  display: none;
}

.editable-select .custom-input.active {
  display: inline-block;
}

.edit-btn {
  background-color: var(--blue-color, #2196F3);
  color: white;
  border: none;
  border-radius: 4px;
  padding: 4px 8px;
  margin-left: 5px;
  cursor: pointer;
  font-size: 0.8rem;
}

.edit-btn:hover {
  background-color: var(--blue-darker, #1976D2);
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 20px;
}

@media (min-width: 992px) {
  .charts-container {
    flex-direction: row;
  }
}

.chart-wrapper {
  flex: 1;
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 15px;
}

.chart-wrapper h4 {
  margin-top: 0;
  margin-bottom: 10px;
  text-align: center;
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.7);
}

.chart-container {
  height: 300px;
}

canvas {
  width: 100%;
  height: 100%;
}

.consecutive-stats {
  margin-top: 20px;
}

.stats-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
  background-color: rgba(255, 255, 255, 0.05);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  overflow: hidden;
}

.stats-table th, .stats-table td {
  padding: 10px;
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.stats-table th {
  background-color: rgba(255, 255, 255, 0.1);
  font-weight: bold;
}

.stats-table tr:hover {
  background-color: rgba(255, 255, 255, 0.05);
  cursor: pointer;
}

.streak-examples {
  margin-top: 20px;
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 15px;
}

.streak-examples h4 {
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.7);
}

.examples-table {
  width: 100%;
  border-collapse: collapse;
}

.examples-table th, .examples-table td {
  padding: 8px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.examples-table th {
  color: rgba(255, 255, 255, 0.7);
  font-weight: bold;
}

.high-probability {
  color: #4CAF50;
  font-weight: bold;
}

.low-probability {
  color: #F44336;
  font-weight: bold;
}

.positive-return {
  color: #4CAF50;
  font-weight: bold;
}

.negative-return {
  color: #F44336;
  font-weight: bold;
}

.continued {
  color: #4CAF50;
}

.broken {
  color: #F44336;
}
</style> 