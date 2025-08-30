<template>
  <div class="hurst-exponent-chart">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading chart data...</p>
    </div>
    <div v-else-if="error" class="error">
      <div class="error-icon">⚠️</div>
      <div class="error-message">
        <h4>Unable to Calculate Hurst Exponent</h4>
        <p>{{ error }}</p>
        <p>
          The Hurst exponent calculation requires sufficient historical data. 
          Try one of the following solutions:
        </p>
        <ul>
          <li>Select a smaller window size (try 126 or 63 days)</li>
          <li>Use a different ticker with more historical data</li>
          <li>Extend the date range to include more data points</li>
        </ul>
      </div>
    </div>
    <div v-else>
      <div class="chart-header">
        <h3>{{ ticker }} Hurst Exponent Analysis</h3>
        <div class="chart-controls">
          <div class="control-group">
            <label>Window Size:</label>
            <select v-model="windowSizeValue" @change="updateChart">
              <option :value="63">3 Months (63 days)</option>
              <option :value="126">6 Months (126 days)</option>
              <option :value="252">1 Year (252 days)</option>
              <option :value="504">2 Years (504 days)</option>
            </select>
          </div>
          <div class="control-group">
            <label>Step Size:</label>
            <select v-model="stepValue" @change="updateChart">
              <option :value="21">Monthly (21 days)</option>
              <option :value="63">Quarterly (63 days)</option>
              <option :value="126">Semi-Annual (126 days)</option>
            </select>
          </div>
        </div>
      </div>
      <div class="charts-container">
        <div class="chart-wrapper">
          <h4>Price Chart</h4>
          <canvas ref="priceChartCanvas"></canvas>
        </div>
        <div class="chart-wrapper">
          <h4>Rolling Hurst Exponent ({{ windowSizeValue }} days window)</h4>
          <canvas ref="hurstChartCanvas"></canvas>
        </div>
      </div>
      <div class="hurst-stats">
        <div class="stat-item">
          <span class="stat-label">Full Period Hurst Exponent:</span>
          <span class="stat-value" :class="getHurstClass(hurstExponent)">{{ hurstExponent.toFixed(3) }}</span>
        </div>
        <div class="stat-item interpretation">
          <span class="stat-label">Interpretation:</span>
          <span class="stat-value">{{ interpretation }}</span>
        </div>
        <div class="hurst-legend">
          <div class="legend-item trending">
            <div class="legend-color"></div>
            <span>Trending (H > 0.55): Past movements likely to continue</span>
          </div>
          <div class="legend-item random">
            <div class="legend-color"></div>
            <span>Random Walk (0.45 ≤ H ≤ 0.55): No memory effect</span>
          </div>
          <div class="legend-item mean-reverting">
            <div class="legend-color"></div>
            <span>Mean-Reverting (H < 0.45): Price tends to revert to mean</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import Chart from 'chart.js/auto';
import annotationPlugin from 'chartjs-plugin-annotation';
import StockAnalysisClient from '../../../utils/stock-analysis-client';

// Register the annotation plugin
Chart.register(annotationPlugin);

const props = defineProps({
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
  windowSize: {
    type: Number,
    default: 126  // Changed default from 252 to 126 for better compatibility
  },
  step: {
    type: Number,
    default: 21  // Changed default from 63 to 21 for better compatibility
  }
});

const priceChartCanvas = ref(null);
const hurstChartCanvas = ref(null);
const priceChart = ref(null);
const hurstChart = ref(null);
const loading = ref(true);
const error = ref(null);
const hurstExponent = ref(0);
const interpretation = ref('');
const windowSizeValue = ref(props.windowSize);
const stepValue = ref(props.step);
const rollingHurst = ref({
  dates: [],
  values: []
});
const priceData = ref({
  dates: [],
  prices: []
});
const resizeObserver = ref(null);

const fetchData = async () => {
  if (!props.ticker) {
    error.value = "No ticker symbol provided";
    loading.value = false;
    return;
  }
  
  loading.value = true;
  error.value = null;
  
  try {
    // Validate and adjust dates
    let startDateStr = props.startDate;
    let endDateStr = props.endDate;
    
    if (startDateStr && endDateStr) {
      const start = new Date(startDateStr);
      const end = new Date(endDateStr);
      const today = new Date();
      
      // Remove time portion for comparison
      today.setHours(0, 0, 0, 0);
      
      // Check for future dates and adjust
      if (end > today) {
        console.log(`End date ${endDateStr} is in the future, using today's date instead`);
        endDateStr = today.toISOString().split('T')[0];
      }
      
      if (start > today) {
        console.log(`Start date ${startDateStr} is in the future, using 1 year before today instead`);
        const oneYearAgo = new Date(today);
        oneYearAgo.setFullYear(today.getFullYear() - 1);
        startDateStr = oneYearAgo.toISOString().split('T')[0];
      }
      
      if (start > end) {
        console.log(`Start date ${startDateStr} is after end date ${endDateStr}, swapping dates`);
        [startDateStr, endDateStr] = [endDateStr, startDateStr];
      }
      
      // Ensure date range is sufficient for Hurst calculation
      const diffTime = Math.abs(end - start);
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      // If date range is too short for the selected window size, extend it
      if (diffDays < windowSizeValue.value * 1.5) {
        console.log(`Date range (${diffDays} days) may be too short for window size ${windowSizeValue.value}, extending start date`);
        const newStart = new Date(end);
        newStart.setDate(newStart.getDate() - Math.ceil(windowSizeValue.value * 2)); // Ensure enough data
        startDateStr = newStart.toISOString().split('T')[0];
        console.log(`Extended date range: ${startDateStr} to ${endDateStr}`);
      }
      
      // For very large date ranges, limit to 5 years to prevent backend overload
      if (diffDays > 1825) { // 5 years
        console.log(`Date range (${diffDays} days) is very large, limiting to 5 years`);
        const newStart = new Date(end);
        newStart.setFullYear(newStart.getFullYear() - 5);
        startDateStr = newStart.toISOString().split('T')[0];
        console.log(`Limited date range: ${startDateStr} to ${endDateStr}`);
      }
    } else {
      // If no date range is provided, use a reasonable default (2 years)
      const today = new Date();
      endDateStr = today.toISOString().split('T')[0];
      
      const twoYearsAgo = new Date(today);
      twoYearsAgo.setFullYear(today.getFullYear() - 2);
      startDateStr = twoYearsAgo.toISOString().split('T')[0];
      
      console.log(`No date range provided, using default: ${startDateStr} to ${endDateStr}`);
    }
    
    // Try with progressively smaller window sizes until one works
    let response;
    let currentWindowSize = windowSizeValue.value;
    let currentStepSize = stepValue.value;
    let attempts = 0;
    const maxAttempts = 3;
    
    while (attempts < maxAttempts) {
      try {
        console.log(`Attempting with window size ${currentWindowSize} and step ${currentStepSize} (attempt ${attempts + 1}/${maxAttempts})`);
        
        response = await StockAnalysisClient.getHurstExponent(
          props.ticker,
          currentWindowSize,
          currentStepSize,
          startDateStr,
          endDateStr
        );
        
        // If we get here, the request succeeded
        console.log(`Success with window size ${currentWindowSize}`);
        break;
        
      } catch (err) {
        console.log(`Error with window size ${currentWindowSize}:`, err.message);
        
        // Check if we've reached the max attempts
        if (attempts === maxAttempts - 1) {
          throw err; // Rethrow the last error
        }
        
        // Reduce window size and step size for the next attempt
        currentWindowSize = Math.max(21, Math.floor(currentWindowSize / 2));
        currentStepSize = Math.max(7, Math.floor(currentStepSize / 2));
        attempts++;
        
        console.log(`Retrying with window size ${currentWindowSize} and step ${currentStepSize}`);
      }
    }
    
    // Update the displayed window size if it changed
    if (currentWindowSize !== windowSizeValue.value) {
      windowSizeValue.value = currentWindowSize;
      stepValue.value = currentStepSize;
    }
    
    if (!response || !response.rolling_hurst || !response.price_data) {
      throw new Error('Invalid response data format');
    }
    
    hurstExponent.value = response.hurst_exponent;
    interpretation.value = response.interpretation;
    rollingHurst.value = response.rolling_hurst;
    priceData.value = response.price_data;
    
    // Validate data
    if (!rollingHurst.value.dates || !rollingHurst.value.values || 
        rollingHurst.value.dates.length === 0 || rollingHurst.value.values.length === 0) {
      throw new Error('No rolling Hurst data available');
    }
    
    if (!priceData.value.dates || !priceData.value.prices || 
        priceData.value.dates.length === 0 || priceData.value.prices.length === 0) {
      throw new Error('No price data available');
    }
    
    // Wait for the next DOM update cycle before rendering charts
    await nextTick();
    renderCharts();
  } catch (err) {
    error.value = `Failed to load Hurst exponent data: ${err.message}`;
    console.error('Error fetching Hurst exponent data:', err);
  } finally {
    loading.value = false;
  }
};

const renderCharts = async () => {
  // Ensure the DOM is updated and canvas elements are available
  await nextTick();
  
  // Clear any previous charts to prevent memory leaks
  if (priceChart.value) {
    priceChart.value.destroy();
    priceChart.value = null;
  }
  
  if (hurstChart.value) {
    hurstChart.value.destroy();
    hurstChart.value = null;
  }
  
  // Add a small delay to ensure canvas is fully ready
  setTimeout(() => {
    try {
      renderPriceChart();
      renderHurstChart();
    } catch (err) {
      console.error('Error rendering charts:', err);
    }
  }, 200); // Increased delay for better reliability
};

const renderPriceChart = () => {
  if (!priceChartCanvas.value) {
    console.error('Price chart canvas element not found');
    return;
  }
  
  if (priceChart.value) {
    priceChart.value.destroy();
  }

  const ctx = priceChartCanvas.value.getContext('2d');
  if (!ctx) {
    console.error('Failed to get price chart canvas context');
    return;
  }
  
  priceChart.value = new Chart(ctx, {
    type: 'line',
    data: {
      labels: priceData.value.dates,
      datasets: [{
        label: 'Price',
        data: priceData.value.prices,
        borderColor: '#4CAF50',
        backgroundColor: 'rgba(76, 175, 80, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.1,
        pointRadius: 0
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
              return `Price: $${context.raw.toFixed(2)}`;
            }
          }
        }
      },
      scales: {
        x: {
          ticks: {
            maxTicksLimit: 10
          },
          title: {
            display: true,
            text: 'Date'
          }
        },
        y: {
          title: {
            display: true,
            text: 'Price ($)'
          }
        }
      }
    }
  });
};

const renderHurstChart = () => {
  if (!hurstChartCanvas.value) {
    console.error('Hurst chart canvas element not found');
    return;
  }
  
  if (hurstChart.value) {
    hurstChart.value.destroy();
  }

  const ctx = hurstChartCanvas.value.getContext('2d');
  if (!ctx) {
    console.error('Failed to get Hurst chart canvas context');
    return;
  }
  
  // Check if annotation plugin is available
  const hasAnnotationPlugin = Chart.registry.getPlugin('annotation') !== undefined;
  if (!hasAnnotationPlugin) {
    console.warn('Annotation plugin not available, using fallback method');
  }
  
  // Define the threshold lines
  const trendingThreshold = 0.55;
  const randomWalkLower = 0.45;
  const randomWalkUpper = 0.55;
  
  // Filter out NaN values from the data
  const validIndices = [];
  const validValues = [];
  const validDates = [];
  
  for (let i = 0; i < rollingHurst.value.values.length; i++) {
    if (!isNaN(rollingHurst.value.values[i])) {
      validIndices.push(i);
      validValues.push(rollingHurst.value.values[i]);
      validDates.push(rollingHurst.value.dates[i]);
    }
  }
  
  // Create datasets for the zones if annotation plugin is not available
  const datasets = [
    {
      label: 'Hurst Exponent',
      data: validValues,
      borderColor: '#3498db',
      backgroundColor: 'rgba(52, 152, 219, 0.1)',
      borderWidth: 2,
      fill: false,
      tension: 0.1,
      pointRadius: 2,
      zIndex: 10
    },
    {
      label: 'Trending Threshold (0.55)',
      data: Array(validDates.length).fill(trendingThreshold),
      borderColor: '#4CAF50',
      borderWidth: 1,
      borderDash: [5, 5],
      fill: false,
      pointRadius: 0
    },
    {
      label: 'Random Walk Lower (0.45)',
      data: Array(validDates.length).fill(randomWalkLower),
      borderColor: '#FFC107',
      borderWidth: 1,
      borderDash: [5, 5],
      fill: false,
      pointRadius: 0
    }
  ];
  
  // Add zone background datasets if annotation plugin is not available
  if (!hasAnnotationPlugin) {
    // Add trending zone
    datasets.push({
      label: 'Trending Zone',
      data: Array(validDates.length).fill(0.775), // Midpoint between 0.55 and 1
      borderColor: 'transparent',
      backgroundColor: 'rgba(76, 175, 80, 0.1)',
      fill: {
        target: '+1',
        above: 'rgba(76, 175, 80, 0.1)'
      },
      pointRadius: 0
    });
    
    // Add random walk zone
    datasets.push({
      label: 'Random Walk Zone',
      data: Array(validDates.length).fill(0.5), // Midpoint between 0.45 and 0.55
      borderColor: 'transparent',
      backgroundColor: 'rgba(255, 193, 7, 0.1)',
      fill: {
        target: 'origin',
        below: 'rgba(255, 193, 7, 0.1)'
      },
      pointRadius: 0
    });
    
    // Add mean-reverting zone
    datasets.push({
      label: 'Mean-Reverting Zone',
      data: Array(validDates.length).fill(0.225), // Midpoint between 0 and 0.45
      borderColor: 'transparent',
      backgroundColor: 'rgba(244, 67, 54, 0.1)',
      fill: {
        target: 'origin',
        below: 'rgba(244, 67, 54, 0.1)'
      },
      pointRadius: 0
    });
  }
  
  // Create chart options
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: {
          usePointStyle: true,
          boxWidth: 10,
          padding: 10,
          color: 'rgba(255, 255, 255, 0.8)',
          filter: (legendItem) => {
            // Only show main datasets in legend
            return ['Hurst Exponent', 'Trending Threshold (0.55)', 'Random Walk Lower (0.45)'].includes(legendItem.text);
          }
        }
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            if (context.datasetIndex === 0) {
              return `Hurst: ${context.raw.toFixed(3)}`;
            }
            return context.dataset.label;
          }
        }
      }
    },
    scales: {
      x: {
        ticks: {
          maxTicksLimit: 10,
          color: 'rgba(255, 255, 255, 0.7)'
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.1)'
        },
        title: {
          display: true,
          text: 'Date',
          color: 'rgba(255, 255, 255, 0.9)'
        }
      },
      y: {
        title: {
          display: true,
          text: 'Hurst Exponent',
          color: 'rgba(255, 255, 255, 0.9)'
        },
        min: 0,
        max: 1,
        ticks: {
          stepSize: 0.1,
          color: 'rgba(255, 255, 255, 0.7)'
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.1)'
        }
      }
    }
  };
  
  // Add annotation plugin options if available
  if (hasAnnotationPlugin) {
    options.plugins.annotation = {
      annotations: {
        trendingZone: {
          type: 'box',
          xMin: 0,
          xMax: validDates.length - 1,
          yMin: trendingThreshold,
          yMax: 1,
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          borderColor: 'rgba(76, 175, 80, 0.3)',
          borderWidth: 1
        },
        randomWalkZone: {
          type: 'box',
          xMin: 0,
          xMax: validDates.length - 1,
          yMin: randomWalkLower,
          yMax: trendingThreshold,
          backgroundColor: 'rgba(255, 193, 7, 0.1)',
          borderColor: 'rgba(255, 193, 7, 0.3)',
          borderWidth: 1
        },
        meanRevertingZone: {
          type: 'box',
          xMin: 0,
          xMax: validDates.length - 1,
          yMin: 0,
          yMax: randomWalkLower,
          backgroundColor: 'rgba(244, 67, 54, 0.1)',
          borderColor: 'rgba(244, 67, 54, 0.3)',
          borderWidth: 1
        },
        trendingLabel: {
          type: 'label',
          xValue: validDates.length - 1,
          yValue: 0.85,
          //content: ['Trending (H > 0.55):', 'Past movements likely to continue'],
          color: '#4CAF50',
          font: {
            size: 11,
            weight: 'bold'
          },
          padding: {
            top: 4,
            bottom: 4,
            left: 6,
            right: 6
          },
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          borderRadius: 3
        },
        randomWalkLabel: {
          type: 'label',
          xValue: validDates.length - 1,
          yValue: 0.5,
          //content: ['Random Walk (0.45 ≤ H ≤ 0.55):', 'No memory effect'],
          color: '#FFC107',
          font: {
            size: 11,
            weight: 'bold'
          },
          padding: {
            top: 4,
            bottom: 4,
            left: 6,
            right: 6
          },
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          borderRadius: 3
        },
        meanRevertingLabel: {
          type: 'label',
          xValue: validDates.length - 1,
          yValue: 0.2,
          //content: ['Mean-Reverting (H < 0.45):', 'Price tends to revert to mean'],
          color: '#F44336',
          font: {
            size: 11,
            weight: 'bold'
          },
          padding: {
            top: 4,
            bottom: 4,
            left: 6,
            right: 6
          },
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          borderRadius: 3
        }
      }
    };
  }
  
  // Create the chart
  hurstChart.value = new Chart(ctx, {
    type: 'line',
    data: {
      labels: validDates,
      datasets: datasets
    },
    options: options
  });
  
  // If annotation plugin is not available, add text directly to canvas
  if (!hasAnnotationPlugin && ctx) {
    // Add a hook to draw text after render
    hurstChart.value.options.plugins.afterRender = (chart) => {
      const ctx = chart.ctx;
      ctx.save();
      
      // Draw trending zone text
      ctx.fillStyle = '#4CAF50';
      ctx.font = 'bold 11px Arial';
      ctx.textAlign = 'right';
      ctx.fillText('Trending (H > 0.55): Past movements likely to continue', chart.chartArea.right - 10, chart.chartArea.top + 30);
      
      // Draw random walk zone text
      ctx.fillStyle = '#FFC107';
      ctx.fillText('Random Walk (0.45 ≤ H ≤ 0.55): No memory effect', chart.chartArea.right - 10, chart.chartArea.top + chart.chartArea.height / 2);
      
      // Draw mean-reverting zone text
      ctx.fillStyle = '#F44336';
      ctx.fillText('Mean-Reverting (H < 0.45): Price tends to revert to mean', chart.chartArea.right - 10, chart.chartArea.bottom - 20);
      
      ctx.restore();
    };
  }
};

const updateChart = () => {
  fetchData();
};

const getHurstClass = (value) => {
  if (value > 0.55) return 'trending';
  if (value < 0.45) return 'mean-reverting';
  return 'random';
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
  
  // Set up resize observer to handle chart resizing
  resizeObserver.value = new ResizeObserver(() => {
    if (priceChart.value || hurstChart.value) {
      // Debounce resize events
      if (window.resizeTimer) clearTimeout(window.resizeTimer);
      window.resizeTimer = setTimeout(() => {
        console.log("Resize detected, re-rendering charts");
        renderCharts();
      }, 250);
    }
  });
  
  // Observe the chart containers
  const chartWrappers = document.querySelectorAll('.chart-wrapper');
  chartWrappers.forEach(wrapper => {
    resizeObserver.value.observe(wrapper);
  });
});

// Add cleanup when component is unmounted
onUnmounted(() => {
  // Destroy charts to prevent memory leaks
  if (priceChart.value) {
    priceChart.value.destroy();
    priceChart.value = null;
  }
  
  if (hurstChart.value) {
    hurstChart.value.destroy();
    hurstChart.value = null;
  }
  
  // Clean up resize observer
  if (resizeObserver.value) {
    resizeObserver.value.disconnect();
    resizeObserver.value = null;
  }
  
  // Clear any pending timers
  if (window.resizeTimer) {
    clearTimeout(window.resizeTimer);
  }
});
</script>

<style scoped>
.hurst-exponent-chart {
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
  margin-bottom: 0;
  padding-left: 20px;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
}

.error-message li {
  margin-bottom: 5px;
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

.charts-container {
  display: grid;
  grid-template-rows: auto auto;
  gap: 20px;
  height: auto;
  margin-bottom: 20px;
}

.chart-wrapper {
  position: relative;
  height: 300px;
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  padding: 15px;
}

.chart-wrapper h4 {
  margin-top: 0;
  margin-bottom: 10px;
  text-align: center;
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.7);
}

.hurst-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 20px;
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 15px;
}

.stat-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.interpretation {
  flex-direction: column;
  align-items: flex-start;
}

.stat-label {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
  font-weight: bold;
  min-width: 120px;
}

.stat-value {
  font-size: 1rem;
}

.interpretation .stat-value {
  margin-top: 5px;
  font-style: italic;
}

.hurst-legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 3px;
}

.trending .legend-color {
  background-color: #4CAF50;
}

.random .legend-color {
  background-color: #FFC107;
}

.mean-reverting .legend-color {
  background-color: #F44336;
}

.trending {
  color: #4CAF50;
}

.random-walk {
  color: #FFC107;
}

.mean-reverting {
  color: #F44336;
}

@media (min-width: 768px) {
  .charts-container {
    grid-template-columns: 1fr;
  }
  
  .chart-wrapper {
    height: 350px;
  }
}

@media (min-width: 1200px) {
  .charts-container {
    grid-template-columns: 1fr;
  }
  
  .chart-wrapper {
    height: 400px;
  }
}
</style> 