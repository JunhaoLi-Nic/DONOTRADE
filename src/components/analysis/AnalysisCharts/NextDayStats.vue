<template>
  <div class="next-day-stats">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading chart data...</p>
    </div>
    <div v-else-if="error" class="error">
      <div class="error-icon">⚠️</div>
      <div class="error-message">
        <h4>Unable to Load Next-Day Statistics</h4>
        <p>{{ error }}</p>
        <p>
          This could be due to:
        </p>
        <ul>
          <li>Insufficient data for the selected ticker</li>
          <li>No price moves meeting the threshold criteria</li>
          <li>Server-side calculation error</li>
          <li>Network connectivity issues</li>
        </ul>
        <button @click="updateChart" class="retry-button">
          <i class="uil uil-redo"></i> Retry
        </button>
      </div>
    </div>
    <div v-else>
      <div class="chart-header">
        <h3>{{ ticker }} Next-Day Statistics (±{{ (parseFloat(threshold) * 100).toFixed(1) }}% Moves)</h3>
        <div class="chart-controls">
          <div class="control-group">
            <label>Threshold:</label>
            <div class="editable-select">
              <select 
                v-model="selectedThreshold" 
                @change="handleThresholdChange" 
                :class="{'hidden': isEditingThreshold}"
              >
                <option :value="0.01">1%</option>
                <option :value="0.02">2%</option>
                <option :value="0.03">3%</option>
                <option :value="0.05">5%</option>
                <option :value="0.10">10%</option>
                <option :value="0.15">15%</option>
                <option :value="0.20">20%</option>
                <option value="custom">Custom...</option>
              </select>
              <input
                v-model="customThreshold"
                type="number"
                min="0.01"
                max="1"
                step="0.01"
                class="editable-input"
                :class="{'active': isEditingThreshold}"
                @blur="handleCustomThresholdBlur"
                @keydown.enter="handleCustomThresholdEnter"
                ref="thresholdInput"
                placeholder="Enter %"
              />
              <button 
                v-if="isEditingThreshold" 
                class="edit-btn" 
                @click="handleCustomThresholdEnter"
              >
                Set
              </button>
            </div>
          </div>
          <div class="control-group">
            <label>Look Ahead:</label>
            <div class="editable-select">
              <select 
                v-model="lookAheadDays" 
                @change="handleLookAheadChange" 
                :class="{'hidden': isEditingLookAhead}"
              >
                <option :value="1">1 Day</option>
                <option :value="2">2 Days</option>
                <option :value="3">3 Days</option>
                <option :value="5">5 Days</option>
                <option :value="10">10 Days</option>
                <option :value="20">20 Days</option>
                <option value="custom">Custom...</option>
              </select>
              <input
                v-model="customLookAheadDays"
                type="number"
                min="1"
                max="60"
                step="1"
                class="editable-input"
                :class="{'active': isEditingLookAhead}"
                @blur="handleCustomLookAheadBlur"
                @keydown.enter="handleCustomLookAheadEnter"
                ref="daysInput"
                placeholder="Enter days"
              />
              <button 
                v-if="isEditingLookAhead" 
                class="edit-btn" 
                @click="handleCustomLookAheadEnter"
              >
                Set
              </button>
            </div>
          </div>
          <div class="control-group">
            <label>Direction:</label>
            <select v-model="selectedMovement" @change="updateChart">
              <option :value="null">Both</option>
              <option value="up">Up Moves</option>
              <option value="down">Down Moves</option>
            </select>
          </div>
        </div>
      </div>
      
      <div class="stats-panels">
        <!-- Up Moves Panel -->
        <div v-if="upMoves && (selectedMovement === 'up' || selectedMovement === null)" class="stats-panel up-moves">
          <h4>Up Moves ≥ +{{ (parseFloat(threshold) * 100).toFixed(1) }}% ({{ upMoves.count }} occurrences)</h4>
          
          <div class="chart-container">
            <div class="chart-wrapper">
              <h5>Return Distribution</h5>
              <canvas ref="upMovesChartCanvas"></canvas>
            </div>
            <div class="chart-wrapper">
              <h5>Scatter Plot</h5>
              <canvas ref="upMovesScatterCanvas"></canvas>
            </div>
          </div>
          
          <div class="stats-summary">
            <div class="stat-item">
              <span class="stat-label">Mean Return:</span>
              <span class="stat-value" :class="getReturnClass(upMoves.mean)">
                {{ (upMoves.mean * 100).toFixed(2) }}%
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Median Return:</span>
              <span class="stat-value" :class="getReturnClass(upMoves.median)">
                {{ (upMoves.median * 100).toFixed(2) }}%
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Std Dev:</span>
              <span class="stat-value">
                {{ (upMoves.std * 100).toFixed(2) }}%
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Min:</span>
              <span class="stat-value" :class="getReturnClass(upMoves.min)">
                {{ (upMoves.min * 100).toFixed(2) }}%
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Max:</span>
              <span class="stat-value" :class="getReturnClass(upMoves.max)">
                {{ (upMoves.max * 100).toFixed(2) }}%
              </span>
            </div>
          </div>
          
          <div v-if="upMoves.data && upMoves.data.length > 0" class="data-table">
            <h5>Recent Data Points</h5>
            <div class="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Change</th>
                    <th>1-Day</th>
                    <th>5-Day</th>
                    <th>10-Day</th>
                    <th>20-Day</th>
                    <th v-if="isCustomLookAhead">{{ customLookAheadDays }}-Day</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in upMoves.data.slice(0, 30)" :key="'up-'+index">
                    <td>{{ formatDate(item.date) }}</td>
                    <td class="positive-return">+{{ (item.Pct_Change * 100).toFixed(2) }}%</td>
                    
                    <!-- 1-Day Return -->
                    <td :class="getReturnClass(item.Forward_Return_1d || null)">
                      {{ item.Forward_Return_1d ? (item.Forward_Return_1d * 100).toFixed(2) + '%' : 'N/A' }}
                    </td>
                    
                    <!-- 5-Day Return -->
                    <td :class="getReturnClass(item.Forward_Return_5d || null)">
                      {{ item.Forward_Return_5d ? (item.Forward_Return_5d * 100).toFixed(2) + '%' : 'N/A' }}
                    </td>
                    
                    <!-- 10-Day Return -->
                    <td :class="getReturnClass(item.Forward_Return_10d || item.Forward_Return || null)">
                      {{ (item.Forward_Return_10d || item.Forward_Return) ? ((item.Forward_Return_10d || item.Forward_Return) * 100).toFixed(2) + '%' : 'N/A' }}
                    </td>
                    
                    <!-- 20-Day Return -->
                    <td :class="getReturnClass(item.Forward_Return_20d || null)">
                      {{ item.Forward_Return_20d ? (item.Forward_Return_20d * 100).toFixed(2) + '%' : 'N/A' }}
                    </td>
                    
                    <!-- Custom Days Return (if applicable) -->
                    <td v-if="isCustomLookAhead" :class="getReturnClass(getCustomDaysReturn(item) || null)">
                      {{ getCustomDaysReturn(item) ? (getCustomDaysReturn(item) * 100).toFixed(2) + '%' : 'N/A' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        
        <!-- Down Moves Panel -->
        <div v-if="downMoves && (selectedMovement === 'down' || selectedMovement === null)" class="stats-panel down-moves">
          <h4>Down Moves ≤ -{{ (parseFloat(threshold) * 100).toFixed(1) }}% ({{ downMoves.count }} occurrences)</h4>
          
          <div class="chart-container">
            <div class="chart-wrapper">
              <h5>Return Distribution</h5>
              <canvas ref="downMovesChartCanvas"></canvas>
            </div>
            <div class="chart-wrapper">
              <h5>Scatter Plot</h5>
              <canvas ref="downMovesScatterCanvas"></canvas>
            </div>
          </div>
          
          <div class="stats-summary">
            <div class="stat-item">
              <span class="stat-label">Mean Return:</span>
              <span class="stat-value" :class="getReturnClass(downMoves.mean)">
                {{ (downMoves.mean * 100).toFixed(2) }}%
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Median Return:</span>
              <span class="stat-value" :class="getReturnClass(downMoves.median)">
                {{ (downMoves.median * 100).toFixed(2) }}%
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Std Dev:</span>
              <span class="stat-value">
                {{ (downMoves.std * 100).toFixed(2) }}%
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Min:</span>
              <span class="stat-value" :class="getReturnClass(downMoves.min)">
                {{ (downMoves.min * 100).toFixed(2) }}%
              </span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Max:</span>
              <span class="stat-value" :class="getReturnClass(downMoves.max)">
                {{ (downMoves.max * 100).toFixed(2) }}%
              </span>
            </div>
          </div>
          
          <div v-if="downMoves.data && downMoves.data.length > 0" class="data-table">
            <h5>Recent Data Points</h5>
            <div class="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Change</th>
                    <th>1-Day</th>
                    <th>5-Day</th>
                    <th>10-Day</th>
                    <th>20-Day</th>
                    <th v-if="isCustomLookAhead">{{ customLookAheadDays }}-Day</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in downMoves.data.slice(0, 30)" :key="'down-'+index">
                    <td>{{ formatDate(item.date) }}</td>
                    <td class="negative-return">{{ (item.Pct_Change * 100).toFixed(2) }}%</td>
                    
                    <!-- 1-Day Return -->
                    <td :class="getReturnClass(item.Forward_Return_1d || null)">
                      {{ item.Forward_Return_1d ? (item.Forward_Return_1d * 100).toFixed(2) + '%' : 'N/A' }}
                    </td>
                    
                    <!-- 5-Day Return -->
                    <td :class="getReturnClass(item.Forward_Return_5d || null)">
                      {{ item.Forward_Return_5d ? (item.Forward_Return_5d * 100).toFixed(2) + '%' : 'N/A' }}
                    </td>
                    
                    <!-- 10-Day Return -->
                    <td :class="getReturnClass(item.Forward_Return_10d || item.Forward_Return || null)">
                      {{ (item.Forward_Return_10d || item.Forward_Return) ? ((item.Forward_Return_10d || item.Forward_Return) * 100).toFixed(2) + '%' : 'N/A' }}
                    </td>
                    
                    <!-- 20-Day Return -->
                    <td :class="getReturnClass(item.Forward_Return_20d || null)">
                      {{ item.Forward_Return_20d ? (item.Forward_Return_20d * 100).toFixed(2) + '%' : 'N/A' }}
                    </td>
                    
                    <!-- Custom Days Return (if applicable) -->
                    <td v-if="isCustomLookAhead" :class="getReturnClass(getCustomDaysReturn(item) || null)">
                      {{ getCustomDaysReturn(item) ? (getCustomDaysReturn(item) * 100).toFixed(2) + '%' : 'N/A' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, nextTick, computed } from 'vue';
import Chart from 'chart.js/auto';
import StockAnalysisClient from '../../../utils/stock-analysis-client';

export default {
  name: 'NextDayStats',
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
    }
  },
  setup(props) {
    const upMovesChartCanvas = ref(null);
    const downMovesChartCanvas = ref(null);
    const upMovesScatterCanvas = ref(null);
    const downMovesScatterCanvas = ref(null);
    const upMovesChart = ref(null);
    const downMovesChart = ref(null);
    const upMovesScatter = ref(null);
    const downMovesScatter = ref(null);
    const loading = ref(true);
    const error = ref(null);
    const selectedThreshold = ref(0.10);
    const lookAheadDays = ref(10);
    const selectedMovement = ref(null);
    const upMoves = ref(null);
    const downMoves = ref(null);
    const threshold = ref(0.10); 
    const customLookAheadDays = ref(15);
    const customThreshold = ref(0.07);
    const isEditingThreshold = ref(false);
    const isEditingLookAhead = ref(false);
    const thresholdInput = ref(null);
    const daysInput = ref(null);
    
    // Computed property to determine if we have a custom look ahead days value
    const isCustomLookAhead = computed(() => {
      const days = parseInt(customLookAheadDays.value);
      return days !== 1 && days !== 5 && days !== 10 && days !== 20 && !isNaN(days);
    });
    
    // Method to get the return value for custom days
    const getCustomDaysReturn = (item) => {
      const days = parseInt(customLookAheadDays.value);
      if (isNaN(days)) return null;
      
      // Check if the item already has this specific forward return
      const customDaysKey = `Forward_Return_${days}d`;
      if (item[customDaysKey]) return item[customDaysKey];
      
      // If the requested days is the same as the current lookAheadDays, use Forward_Return
      if (days === lookAheadDays.value || days === parseInt(lookAheadDays.value)) {
        return item.Forward_Return;
      }
      
      // Otherwise return null (not available)
      return null;
    };
    
    // Methods for handling direct input in dropdown
    const handleThresholdChange = () => {
      if (selectedThreshold.value === 'custom') {
        isEditingThreshold.value = true;
        nextTick(() => {
          if (thresholdInput.value) {
            thresholdInput.value.focus();
          }
        });
      } else {
        isEditingThreshold.value = false;
        threshold.value = parseFloat(selectedThreshold.value);
        updateChart();
      }
    };
    
    const handleLookAheadChange = () => {
      if (lookAheadDays.value === 'custom') {
        isEditingLookAhead.value = true;
        nextTick(() => {
          if (daysInput.value) {
            daysInput.value.focus();
          }
        });
      } else {
        isEditingLookAhead.value = false;
        updateChart();
      }
    };
    
    const handleCustomThresholdBlur = () => {
      applyCustomThreshold();
    };
    
    const handleCustomThresholdEnter = () => {
      applyCustomThreshold();
      isEditingThreshold.value = false;
    };
    
    const handleCustomLookAheadBlur = () => {
      applyCustomLookAhead();
    };
    
    const handleCustomLookAheadEnter = () => {
      applyCustomLookAhead();
      isEditingLookAhead.value = false;
    };
    
    // Methods for handling custom inputs
    const applyCustomThreshold = () => {
      const value = parseFloat(customThreshold.value);
      if (!isNaN(value) && value > 0 && value <= 1) {
        threshold.value = value;
        selectedThreshold.value = value; // Set the actual value in the dropdown
        isEditingThreshold.value = false;
        console.log("Applied custom threshold:", value);
        updateChart();
      }
    };
    
    const applyCustomLookAhead = () => {
      const value = parseInt(customLookAheadDays.value);
      if (!isNaN(value) && value > 0 && value <= 60) {
        lookAheadDays.value = value; // Set the actual value in the dropdown
        isEditingLookAhead.value = false;
        console.log("Applied custom look ahead days:", value);
        updateChart();
      }
    };
    
    // Watch for dropdown selection changes to focus the input field
    watch(selectedThreshold, (newValue) => {
      if (newValue === 'custom') {
        nextTick(() => {
          if (thresholdInput.value) {
            thresholdInput.value.focus();
          }
        });
      }
    });
    
    watch(lookAheadDays, (newValue) => {
      if (newValue === 'custom') {
        nextTick(() => {
          if (daysInput.value) {
            daysInput.value.focus();
          }
        });
      }
    });

    const fetchData = async () => {
      loading.value = true;
      error.value = null;
      
      try {
        // Always ensure threshold is a number
        let thresholdValue = threshold.value;
        if (typeof thresholdValue !== 'number') {
          thresholdValue = parseFloat(thresholdValue);
          if (isNaN(thresholdValue)) {
            thresholdValue = 0.10; // Default if parsing fails
          }
        }
        
        // Always ensure lookAheadDays is a number
        let lookAhead = lookAheadDays.value;
        if (typeof lookAhead !== 'number') {
          lookAhead = parseInt(lookAhead);
          if (isNaN(lookAhead)) {
            lookAhead = 10; // Default if parsing fails
          }
        }
        
        console.log(`Fetching next-day stats for ${props.ticker} with threshold ${thresholdValue}, lookAhead ${lookAhead}`);
        console.log(`Date range: startDate=${props.startDate}, endDate=${props.endDate}`);
        
        // Validate date range - don't allow future dates
        let startDate = props.startDate;
        let endDate = props.endDate;
        
        if (endDate) {
          const today = new Date();
          const endDateObj = new Date(endDate);
          if (endDateObj > today) {
            console.warn(`End date ${endDate} is in the future, using today's date instead`);
            endDate = today.toISOString().split('T')[0];
          }
        }

        const response = await StockAnalysisClient.getNextDayStats(
          props.ticker,
          thresholdValue,
          lookAhead,
          selectedMovement.value,
          startDate,
          endDate
        );
        
        console.log('API Response:', response);
        
        if (!response) {
          throw new Error('Empty response from server');
        }
        
        // Check for message field which indicates no data found
        if (response.message) {
          error.value = response.message || "No data returned from server";
          loading.value = false;
          return;
        }
        
        upMoves.value = response.up_moves;
        downMoves.value = response.down_moves;
        
        console.log('Up moves data:', upMoves.value);
        console.log('Down moves data:', downMoves.value);
        
        if (!upMoves.value && !downMoves.value) {
          error.value = "No significant price moves found matching the criteria";
          loading.value = false;
          return;
        }
        
        // Use Vue's nextTick to ensure DOM is updated before rendering charts
        nextTick(() => {
          // Add a timeout to give additional time for DOM elements to be ready
          setTimeout(() => {
            console.log('Rendering charts...');
            renderCharts();
          }, 300);
        });
      } catch (err) {
        console.error('Detailed error:', err);
        
        // Handle Axios errors specifically
        if (err.response) {
          // The server responded with an error status
          const serverMessage = err.response.data?.detail || err.message || 'Server error';
          error.value = `Failed to load next-day stats: ${serverMessage}`;
          console.error(`Server error ${err.response.status}: ${serverMessage}`);
        } else if (err.request) {
          // The request was made but no response was received
          error.value = "Network error. Please check your connection.";
          console.error('Network error:', err.request);
        } else {
          // Something else caused the error
          error.value = `Failed to load next-day stats: ${err.message || 'Unknown error'}`;
        }
        console.error('Error fetching next-day stats:', err);
      } finally {
        loading.value = false;
      }
    };

    const renderCharts = () => {
      console.log('In renderCharts, upMoves:', upMoves.value, 'downMoves:', downMoves.value);
      console.log('Canvas elements:', {
        upMovesCanvas: upMovesChartCanvas.value,
        downMovesCanvas: downMovesChartCanvas.value,
        upScatterCanvas: upMovesScatterCanvas.value,
        downScatterCanvas: downMovesScatterCanvas.value
      });
      
      // Add a small delay to ensure DOM elements are fully rendered
      setTimeout(() => {
        try {
          if (upMoves.value && (selectedMovement.value === 'up' || selectedMovement.value === null)) {
            console.log('Rendering up moves charts');
            if (upMovesChartCanvas.value) {
              renderBoxPlot(upMovesChartCanvas.value, upMovesChart, upMoves.value, 'rgba(76, 175, 80, 0.8)');
            } else {
              console.warn('Up moves chart canvas not found in DOM');
            }
            
            if (upMovesScatterCanvas.value) {
              renderScatterPlot(upMovesScatterCanvas.value, upMovesScatter, upMoves.value.data || [], 'rgba(76, 175, 80, 0.8)');
            } else {
              console.warn('Up moves scatter canvas not found in DOM');
            }
          }
          
          if (downMoves.value && (selectedMovement.value === 'down' || selectedMovement.value === null)) {
            console.log('Rendering down moves charts');
            if (downMovesChartCanvas.value) {
              renderBoxPlot(downMovesChartCanvas.value, downMovesChart, downMoves.value, 'rgba(244, 67, 54, 0.8)');
            } else {
              console.warn('Down moves chart canvas not found in DOM');
            }
            
            if (downMovesScatterCanvas.value) {
              renderScatterPlot(downMovesScatterCanvas.value, downMovesScatter, downMoves.value.data || [], 'rgba(244, 67, 54, 0.8)');
            } else {
              console.warn('Down moves scatter canvas not found in DOM');
            }
          }
        } catch (error) {
          console.error('Error rendering charts:', error);
        }
      }, 50);
    };

    const renderBoxPlot = (canvas, chartRef, data, color) => {
      if (!canvas) {
        console.error('Canvas element not found for box plot');
        return;
      }
      
      try {
        if (chartRef.value) {
          chartRef.value.destroy();
        }

        const ctx = canvas.getContext('2d');
        if (!ctx) {
          console.error('Could not get 2D context from canvas');
          return;
        }
        
        // Check if we have all required data
        const requiredProps = ['min', 'q1', 'median', 'q3', 'max'];
        const missingProps = requiredProps.filter(prop => data[prop] === undefined);
        
        if (missingProps.length > 0) {
          console.error(`Missing required properties for box plot: ${missingProps.join(', ')}`);
          return;
        }
        
        console.log('Box plot data:', [data.min, data.q1, data.median, data.q3, data.max]);
        
        // Create a bar chart to visualize the statistics
        chartRef.value = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: ['Min', 'Q1', 'Median', 'Q3', 'Max'],
            datasets: [{
              label: 'Return Distribution',
              data: [
                data.min,
                data.q1,
                data.median,
                data.q3,
                data.max
              ],
              backgroundColor: color,
              borderColor: color.replace('0.8', '1'),
              borderWidth: 1
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: false
              },
              tooltip: {
                callbacks: {
                  label: (context) => {
                    const value = (context.raw * 100).toFixed(2);
                    return `Return: ${value}%`;
                  }
                }
              }
            },
            scales: {
              y: {
                title: {
                  display: true,
                  text: `${lookAheadDays.value}-Day Forward Return`
                },
                ticks: {
                  callback: value => `${(value * 100).toFixed(0)}%`
                }
              }
            }
          }
        });
        console.log('Box plot rendered successfully');
      } catch (err) {
        console.error('Error rendering box plot:', err);
      }
    };
    
    const renderScatterPlot = (canvas, chartRef, data, color) => {
      if (!canvas || !data || data.length === 0) {
        console.error('Canvas element not found or no data for scatter plot');
        return;
      }
      
      try {
        if (chartRef.value) {
          chartRef.value.destroy();
        }

        const ctx = canvas.getContext('2d');
        if (!ctx) {
          console.error('Could not get 2D context from canvas');
          return;
        }
        
        // Extract data for scatter plot
        const scatterData = data.map(item => ({
          x: item.Pct_Change,
          y: item.Forward_Return
        }));
        
        console.log('Scatter plot data points:', scatterData.length);
        
        // Create a scatter plot to visualize the relationship
        chartRef.value = new Chart(ctx, {
          type: 'scatter',
          data: {
            datasets: [{
              label: 'Move vs Return',
              data: scatterData,
              backgroundColor: color,
              borderColor: color.replace('0.8', '1'),
              borderWidth: 1,
              pointRadius: 4,
              pointHoverRadius: 6
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                display: false
              },
              tooltip: {
                callbacks: {
                  label: (context) => {
                    const x = (context.raw.x * 100).toFixed(2);
                    const y = (context.raw.y * 100).toFixed(2);
                    return `Move: ${x}%, Return: ${y}%`;
                  }
                }
              }
            },
            scales: {
              x: {
                title: {
                  display: true,
                  text: 'Price Change (%)'
                },
                ticks: {
                  callback: value => `${(value * 100).toFixed(0)}%`
                }
              },
              y: {
                title: {
                  display: true,
                  text: `${lookAheadDays.value}-Day Forward Return`
                },
                ticks: {
                  callback: value => `${(value * 100).toFixed(0)}%`
                }
              }
            }
          }
        });
        console.log('Scatter plot rendered successfully');
      } catch (err) {
        console.error('Error rendering scatter plot:', err);
      }
    };

    const updateChart = () => {
      console.log("Updating chart with threshold:", threshold.value, "lookAhead:", lookAheadDays.value);
      // Reset any existing errors before fetching data
      error.value = null;
      fetchData();
    };

    const getReturnClass = (returnValue) => {
      if (returnValue > 0) return 'positive-return';
      if (returnValue < 0) return 'negative-return';
      return '';
    };
    
    const formatDate = (dateValue) => {
      if (!dateValue) return 'N/A';
      
      // Handle different date formats
      let dateStr;
      if (dateValue instanceof Date) {
        dateStr = dateValue.toISOString().split('T')[0];
      } else if (typeof dateValue === 'string') {
        // Try to parse the date string
        try {
          const date = new Date(dateValue);
          if (!isNaN(date.getTime())) {
            dateStr = date.toISOString().split('T')[0];
          } else {
            dateStr = dateValue;
          }
        } catch (e) {
          dateStr = dateValue;
        }
      } else {
        dateStr = String(dateValue);
      }
      
      return dateStr;
    };

    watch(() => props.ticker, fetchData);
    watch(() => props.startDate, fetchData);
    watch(() => props.endDate, fetchData);

    onMounted(() => {
      fetchData();
    });

    return {
      upMovesChartCanvas,
      downMovesChartCanvas,
      upMovesScatterCanvas,
      downMovesScatterCanvas,
      loading,
      error,
      selectedThreshold,
      lookAheadDays,
      selectedMovement,
      upMoves,
      downMoves,
      threshold,
      customThreshold,
      customLookAheadDays,
      isEditingThreshold,
      isEditingLookAhead,
      applyCustomThreshold,
      applyCustomLookAhead,
      handleThresholdChange,
      handleLookAheadChange,
      handleCustomThresholdBlur,
      handleCustomThresholdEnter,
      handleCustomLookAheadBlur,
      handleCustomLookAheadEnter,
      updateChart,
      getReturnClass,
      formatDate,
      thresholdInput,
      daysInput,
      isCustomLookAhead,
      getCustomDaysReturn
    };
  }
};
</script>

<style scoped>
.next-day-stats {
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
}

.error-icon {
  font-size: 4rem;
  margin-bottom: 10px;
}

.error-message {
  text-align: center;
  padding: 20px;
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.error-message h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #ff5252;
}

.error-message p {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 10px;
}

.error-message ul {
  list-style: none;
  padding: 0;
  margin-bottom: 20px;
}

.error-message li {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 3px;
}

.retry-button {
  background-color: var(--blue-color, #2196F3);
  color: white;
  padding: 8px 15px;
  border-radius: 5px;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: background-color 0.3s ease;
}

.retry-button:hover {
  background-color: var(--blue-darker, #1976D2);
}

.retry-button:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.5);
}

.chart-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 15px;
}

@media (min-width: 768px) {
  .chart-header {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
}

.chart-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  align-items: center;
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

.custom-input-container {
  display: flex;
  align-items: center;
  gap: 5px;
}

.custom-input {
  background-color: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  color: inherit;
  padding: 4px 8px;
  width: 60px; /* Adjust width as needed */
  text-align: center;
}

.stats-panels {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

@media (min-width: 992px) {
  .stats-panels {
    flex-direction: row;
  }
}

.stats-panel {
  flex: 1;
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 15px;
}

.stats-panel h4 {
  margin-top: 0;
  margin-bottom: 15px;
  text-align: center;
  font-size: 1rem;
}

.chart-container {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 15px;
}

@media (min-width: 768px) {
  .chart-container {
    flex-direction: row;
  }
}

.chart-wrapper {
  flex: 1;
  height: 180px;
}

.chart-wrapper h5 {
  margin-top: 0;
  margin-bottom: 10px;
  text-align: center;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
}

.stats-summary {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  padding: 10px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 15px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 80px;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 3px;
}

.stat-value {
  font-weight: bold;
  font-size: 1rem;
}

.positive-return {
  color: #4CAF50;
}

.negative-return {
  color: #F44336;
}

.up-moves h4 {
  color: #4CAF50;
}

.down-moves h4 {
  color: #F44336;
}

.data-table h5 {
  margin-top: 0;
  margin-bottom: 10px;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

th {
  text-align: left;
  padding: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.7);
}

td {
  padding: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.editable-select {
  position: relative;
  display: inline-flex;
  align-items: center;
  min-width: 120px;
}

.editable-select select {
  width: 100%;
}

.editable-select select.hidden {
  opacity: 0;
  position: absolute;
  pointer-events: none;
}

.editable-input {
  background-color: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  color: inherit;
  padding: 4px 8px;
  width: 80px;
  display: none;
}

.editable-input.active {
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

.table-container {
  max-height: 400px;
  overflow-y: auto;
  overflow-x: auto;
  margin-bottom: 15px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

.table-container table {
  width: 100%;
  border-collapse: collapse;
}

.table-container thead {
  position: sticky;
  top: 0;
  background-color: rgba(0, 0, 0, 0.3);
  z-index: 1;
}

.table-container th {
  border-bottom: 2px solid rgba(255, 255, 255, 0.2);
  padding: 10px 8px;
}

.table-container td {
  padding: 8px;
  white-space: nowrap;
}

/* Alternating row colors */
.table-container tbody tr:nth-child(odd) {
  background-color: rgba(255, 255, 255, 0.03);
}

.table-container tbody tr:hover {
  background-color: rgba(33, 150, 243, 0.1);
}
</style> 