<template>
  <div class="price-distribution-chart">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading chart data...</p>
    </div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="chart-header">
        <h3>
          <span class="ticker-symbol">{{ ticker }}</span>
          <span class="chart-title">Price Distribution</span>
          <span class="method-badge">{{ methodLabel }}</span>
        </h3>
        <!-- Chart Controls -->
        <div class="chart-controls">
          <select v-model="selectedMethod" @change="updateChart" class="control-select">
            <option value="hist">Histogram</option>
            <option value="kde">KDE</option>
            <option value="mc_kde">Monte Carlo KDE</option>
          </select>
          
          <!-- KDE Parameters -->
          <div v-if="selectedMethod === 'kde'" class="param-controls">
            <div class="param-slider">
              <label>Bandwidth:</label>
              <input 
                type="range" 
                v-model.number="bwMethod" 
                min="0.01"
                max="1"
                step="0.01"
                @change="updateChart"
              >
              <span class="param-value">{{ bwMethod.toFixed(2) }}</span>
            </div>
            <div class="param-slider">
              <label>Grid Size:</label>
              <input 
                type="range" 
                v-model.number="gridSize" 
                min="100" 
                max="1000" 
                step="50" 
                @change="updateChart"
              >
              <span class="param-value">{{ gridSize }}</span>
            </div>
            
            <!-- Volume Indicators Toggle -->
            <div class="volume-toggle">
              <label>
                <input type="checkbox" v-model="includeVolumeIndicators" @change="updateChart">
                <span>Volume Indicators</span>
              </label>
            </div>
          </div>
          
          <!-- Monte Carlo Parameters -->
          <div v-if="selectedMethod === 'mc_kde'" class="param-controls">
            <div class="horizon-days">
              <label>Horizon Days:</label>
              <input type="number" v-model.number="horizonDays" min="1" max="30" @change="updateChart">
            </div>
            
            <!-- Volume Indicators Toggle -->
            <div class="volume-toggle">
              <label>
                <input type="checkbox" v-model="includeVolumeIndicators" @change="updateChart">
                <span>Volume Indicators</span>
              </label>
            </div>
          </div>
          
          <!-- Show Volume Toggle for Histogram -->
          <div v-if="selectedMethod === 'hist'" class="param-controls">
            <div class="volume-toggle">
              <label>
                <input type="checkbox" v-model="includeVolumeIndicators" @change="updateChart">
                <span>Volume Indicators</span>
              </label>
            </div>
          </div>
        </div>
      </div>
      
      <!-- CSS-only chart implementation -->
      <div class="css-chart-container">
        <!-- Y-axis labels -->
        <div class="y-axis">
          <div class="y-label">High</div>
          <div class="y-label">Medium</div>
          <div class="y-label">Low</div>
          <div class="y-label">Low</div>
        </div>
        
        <!-- Chart grid with vertical and horizontal lines -->
        <div class="chart-grid">
          <div class="grid-line" v-for="i in 5" :key="i" :style="{ bottom: `${i * 20}%` }"></div>
          <div class="grid-line vertical" v-for="i in 4" :key="`v-${i}`" :style="{ left: `${i * 20}%` }"></div>
        </div>
        
        <!-- Chart bars with data points -->
        <div class="chart-bars">
          <div 
            v-for="(value, index) in normalizedValues" 
            :key="index" 
            class="bar"
            :class="{'hist-bar': selectedMethod === 'hist'}"
            :style="{ height: value + '%' }"
            :title="`Price: $${distribution.x[index].toFixed(2)}, ${selectedMethod === 'hist' ? 'Frequency' : 'Density'}: ${distribution.y[index].toFixed(4)}`"
          ></div>
          
          <!-- Current price marker -->
          <div 
            v-if="!currentPriceError && currentPriceBarIndex !== null" 
            class="current-price-marker"
            :style="{ left: (currentPriceBarIndex / normalizedValues.length * 100) + '%' }"
          >
            <div class="marker-line"></div>
            <div class="marker-label" :class="{'label-top': currentPriceBarIndex > normalizedValues.length * 0.7}">
              ${{ currentPrice.toFixed(2) }}
            </div>
          </div>
          
          <!-- Distribution markers for TVC, VV, VA -->
          <div v-if="includeVolumeIndicators && normalizedValues.length > 0" class="distribution-markers">
            <!-- TVC Marker (at peak - highest point) -->
            <div 
              class="dist-marker tvc-marker" 
              :style="{ left: `${getPeakPosition()}%`, bottom: `${getPeakHeight()}%` }"
            >
              <div class="marker-label">TVC</div>
              <div class="marker-point"></div>
            </div>
            
            <!-- VV Marker (at valley - lowest point between peaks) -->
            <div 
              class="dist-marker vv-marker" 
              :style="{ left: `${getValleyPosition()}%`, bottom: `${getValleyHeight()}%` }"
            >
              <div class="marker-label">VV</div>
              <div class="marker-point"></div>
            </div>
            
            <!-- VA Marker (at secondary peak) -->
            <div 
              class="dist-marker va-marker" 
              :style="{ left: `${getSecondPeakPosition()}%`, bottom: `${getSecondPeakHeight()}%` }"
            >
              <div class="marker-label">VA</div>
              <div class="marker-point"></div>
            </div>
          </div>
          
          <!-- Update the SVG path styling -->
          <svg v-if="selectedMethod !== 'hist'" class="line-path-overlay" :viewBox="`0 0 ${normalizedValues.length} 100`" preserveAspectRatio="none">
            <defs>
              <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="rgba(36, 139, 188, 0.5)" />
                <stop offset="100%" stop-color="rgba(36, 139, 188, 0.05)" />
              </linearGradient>
              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>
            <path :d="linePath" fill="url(#chartGradient)" stroke="rgba(36, 139, 188, 0.8)" stroke-width="1.5" filter="url(#glow)" />
          </svg>
        </div>
        
        <!-- X-axis labels -->
        <div class="x-axis">
          <div class="x-label">${{ minPrice.toFixed(0) }}</div>
          <div class="x-label">${{ ((minPrice + maxPrice) / 4).toFixed(0) }}</div>
          <div class="x-label">${{ ((minPrice + maxPrice) / 2).toFixed(0) }}</div>
          <div class="x-label">${{ ((minPrice + maxPrice) * 3/4).toFixed(0) }}</div>
          <div class="x-label">${{ maxPrice.toFixed(0) }}</div>
        </div>
        <div class="axis-labels">
          <div class="x-axis-title">Price ($)</div>
          <div class="y-axis-title">{{ selectedMethod === 'hist' ? 'Frequency' : 'Density' }}</div>
        </div>
        
        <!-- Add hover overlay and tooltip -->
        <div 
          class="chart-hover-overlay"
          @mousemove="handleChartHover"
          @mouseleave="hideHoverTooltip"
        ></div>
        
        <div 
          class="hover-tooltip"
          v-show="hoverTooltipVisible"
          :style="{ left: tooltipLeft + 'px', top: tooltipTop + 'px' }"
        >
          <div class="tooltip-price">${{ tooltipPrice }}</div>
          <div class="tooltip-value">{{ tooltipValue }}</div>
        </div>
      </div>
      
      <div class="chart-stats">
        <div class="stat-item">
          <span class="stat-label">Min:</span>
          <span class="stat-value">${{ stats.min.toFixed(2) }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Max:</span>
          <span class="stat-value">${{ stats.max.toFixed(2) }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Mean:</span>
          <span class="stat-value">${{ stats.mean.toFixed(2) }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Median:</span>
          <span class="stat-value">${{ stats.median.toFixed(2) }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Std Dev:</span>
          <span class="stat-value">${{ stats.std.toFixed(2) }}</span>
        </div>
        <div class="stat-item" :class="{'current-price-stat': !currentPriceError, 'current-price-error': currentPriceError}">
          <span class="stat-label">Current Price:</span>
          <span v-if="!currentPriceError" class="stat-value">${{ currentPrice.toFixed(2) }}</span>
          <span v-else class="stat-value error-value">{{ currentPriceError }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import StockAnalysisClient from '../../../utils/stock-analysis-client';

export default {
  name: 'PriceDistribution',
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
    const loading = ref(true);
    const error = ref(null);
    const selectedMethod = ref('kde');
    const horizonDays = ref(5);
    const binSize = ref(5);
    const smoothWindow = ref(3);
    const simulations = ref(10000);
    const bwMethod = ref(0.15);  // Default bandwidth for KDE
    const gridSize = ref(500);   // Default grid size for KDE
    const includeVolumeIndicators = ref(true); // Default to include volume indicators
    const distribution = ref({ x: [], y: [] });
    const currentPrice = ref(0);
    const currentPriceError = ref(null);
    const fetchingPrice = ref(false);
    const currentPriceBarIndex = ref(null);
    const stats = ref({
      min: 0,
      max: 0,
      mean: 0,
      median: 0,
      std: 0
    });
    
    // Computed properties for CSS chart
    const normalizedValues = computed(() => {
      if (!distribution.value.y || distribution.value.y.length === 0) return [];
      
      const maxVal = Math.max(...distribution.value.y);
      // Use 90% of the height to ensure peaks don't get cut off
      return distribution.value.y.map(val => (val / maxVal) * 90);
    });
    
    const yAxisLabels = computed(() => {
      if (!distribution.value.y || distribution.value.y.length === 0) return ['1.0', '0.5', '0.0'];
      
      const maxVal = Math.max(...distribution.value.y);
      return [
        maxVal.toFixed(2),
        (maxVal / 2).toFixed(2),
        '0.00'
      ];
    });
    
    const minPrice = computed(() => {
      if (!distribution.value.x || distribution.value.x.length === 0) return 0;
      return Math.min(...distribution.value.x);
    });
    
    const maxPrice = computed(() => {
      if (!distribution.value.x || distribution.value.x.length === 0) return 0;
      return Math.max(...distribution.value.x);
    });

    const methodLabel = computed(() => {
      switch (selectedMethod.value) {
        case 'hist':
          return 'Histogram';
        case 'kde':
          return `Kernel Density Estimation (BW: ${bwMethod.value.toFixed(2)})`;
        case 'mc_kde':
          return `Monte Carlo KDE (${horizonDays.value} days)`;
        default:
          return selectedMethod.value.toUpperCase();
      }
    });

    const fetchCurrentPrice = async () => {
      if (!props.ticker) return;
      
      try {
        fetchingPrice.value = true;
        currentPriceError.value = null; // Clear previous errors
        
        const priceData = await StockAnalysisClient.getCurrentPrice(props.ticker);
        currentPrice.value = priceData.current_price;
        console.log(`Current price for ${props.ticker}: $${currentPrice.value}`);
        
        // Update current price bar index
        updateCurrentPriceMarker();
      } catch (err) {
        console.error(`Failed to fetch current price for ${props.ticker}:`, err);
        currentPrice.value = 0;
        currentPriceError.value = "Not available";
      } finally {
        fetchingPrice.value = false;
      }
    };
    
    const updateCurrentPriceMarker = () => {
      if (currentPrice.value > 0 && distribution.value.x && distribution.value.x.length > 0) {
        // Find the closest price point
        let closestIndex = 0;
        let minDistance = Number.MAX_VALUE;
        
        distribution.value.x.forEach((price, index) => {
          const distance = Math.abs(price - currentPrice.value);
          if (distance < minDistance) {
            minDistance = distance;
            closestIndex = index;
          }
        });
        
        const priceRange = maxPrice.value - minPrice.value;
        
        // Only show if price is within a reasonable range of the distribution
        if (minDistance < priceRange * 0.1) {
          currentPriceBarIndex.value = closestIndex;
        } else {
          currentPriceBarIndex.value = null;
          currentPriceError.value = "Out of range";
        }
      } else {
        currentPriceBarIndex.value = null;
      }
    };

    const fetchData = async () => {
      if (!props.ticker) {
        error.value = "No ticker symbol provided";
        loading.value = false;
        return;
      }
      
      // Validate dates
      if (props.startDate && props.endDate) {
        const start = new Date(props.startDate);
        const end = new Date(props.endDate);
        const today = new Date();
        
        if (start > today || end > today) {
          error.value = "Cannot analyze future dates. Please select a date range in the past.";
          loading.value = false;
          return;
        }
        
        if (start > end) {
          error.value = "Start date cannot be after end date";
          loading.value = false;
          return;
        }
      }
      
      loading.value = true;
      error.value = null;
      
      try {
        // Fetch current price alongside distribution data
        if (!fetchingPrice.value) {
          fetchCurrentPrice();
        }
        
        const response = await StockAnalysisClient.getPriceDistribution(
          props.ticker,
          selectedMethod.value,
          binSize.value,
          smoothWindow.value,
          simulations.value,
          horizonDays.value,
          props.startDate,
          props.endDate,
          bwMethod.value,
          gridSize.value,
          includeVolumeIndicators.value
        );
        
        if (!response || !response.distribution || !response.stats) {
          throw new Error('Invalid response data format');
        }
        
        distribution.value = response.distribution;
        stats.value = response.stats;
        
        // Ensure we have data to render
        if (!distribution.value.x || !distribution.value.y || 
            distribution.value.x.length === 0 || distribution.value.y.length === 0) {
          throw new Error('No distribution data available');
        }
        
        // Update current price marker position
        updateCurrentPriceMarker();
        
        await nextTick();
      } catch (err) {
        error.value = `Failed to load price distribution data: ${err.message}`;
        console.error('Error fetching price distribution data:', err);
      } finally {
        loading.value = false;
      }
    };

    const updateChart = () => {
      fetchData();
    };

    watch(() => props.ticker, () => {
      fetchData();
      fetchCurrentPrice();
    });
    watch(() => props.startDate, fetchData);
    watch(() => props.endDate, fetchData);
    watch(() => currentPrice.value, updateCurrentPriceMarker);

    onMounted(() => {
      fetchData();
    });

    // Add line path calculation
    const linePath = computed(() => {
      if (!normalizedValues.value || normalizedValues.value.length === 0) return '';
      
      // Create SVG path starting at the bottom left
      let path = `M0,100 L0,${100 - normalizedValues.value[0]}`;
      
      // Add line segments for each data point
      for (let i = 1; i < normalizedValues.value.length; i++) {
        path += ` L${i},${100 - normalizedValues.value[i]}`;
      }
      
      // Close the path back to the bottom right and bottom left
      path += ` L${normalizedValues.value.length - 1},100 L0,100 Z`;
      
      return path;
    });

    // Add hover overlay to the css-chart-container without changing other parameters
    const hoverTooltipVisible = ref(false);
    const tooltipLeft = ref(0);
    const tooltipTop = ref(0);
    const tooltipPrice = ref('');
    const tooltipValue = ref('');

    // Add hover handler methods
    const handleChartHover = (event) => {
      if (!distribution.value?.x?.length) return;
      
      const chartBars = event.currentTarget.parentNode.querySelector('.chart-bars');
      const chartRect = chartBars.getBoundingClientRect();
      const relativeX = event.clientX - chartRect.left;
      const width = chartRect.width;
      
      // Find the closest index based on position
      const index = Math.min(
        Math.max(
          Math.round((relativeX / width) * (distribution.value.x.length - 1)),
          0
        ),
        distribution.value.x.length - 1
      );
      
      // Get values for the tooltip
      tooltipPrice.value = distribution.value.x[index].toFixed(2);
      tooltipValue.value = selectedMethod.value === 'hist' 
        ? `Frequency: ${distribution.value.y[index].toFixed(4)}`
        : `Density: ${distribution.value.y[index].toFixed(4)}`;
      
      // Position tooltip
      tooltipLeft.value = relativeX;
      tooltipTop.value = chartRect.height - (normalizedValues.value[index] * chartRect.height / 100) - 40;
      
      // Show tooltip
      hoverTooltipVisible.value = true;
    };

    const hideHoverTooltip = () => {
      hoverTooltipVisible.value = false;
    };

    // Methods to find peaks and valleys for markers
    const getPeakPosition = () => {
      if (!normalizedValues.value || normalizedValues.value.length === 0) return 30;
      
      // Find the position of the highest peak (around 1/3 of the width)
      const firstThird = Math.floor(normalizedValues.value.length / 3);
      const twoThirds = Math.floor(normalizedValues.value.length * 2 / 3);
      let maxIndex = 0;
      let maxValue = 0;
      
      for (let i = 0; i < twoThirds; i++) {
        if (normalizedValues.value[i] > maxValue) {
          maxValue = normalizedValues.value[i];
          maxIndex = i;
        }
      }
      
      return (maxIndex / normalizedValues.value.length) * 100;
    };
    
    const getPeakHeight = () => {
      if (!normalizedValues.value || normalizedValues.value.length === 0) return 0;
      
      // Find the height of the highest peak
      const firstThird = Math.floor(normalizedValues.value.length / 3);
      const twoThirds = Math.floor(normalizedValues.value.length * 2 / 3);
      let maxValue = 0;
      
      for (let i = 0; i < twoThirds; i++) {
        if (normalizedValues.value[i] > maxValue) {
          maxValue = normalizedValues.value[i];
        }
      }
      
      return maxValue;
    };
    
    const getValleyPosition = () => {
      if (!normalizedValues.value || normalizedValues.value.length === 0) return 50;
      
      // Find the position of the valley (typically in the middle)
      const middleStart = Math.floor(normalizedValues.value.length * 0.4);
      const middleEnd = Math.floor(normalizedValues.value.length * 0.7);
      let minIndex = middleStart;
      let minValue = normalizedValues.value[middleStart];
      
      for (let i = middleStart; i < middleEnd; i++) {
        if (normalizedValues.value[i] < minValue) {
          minValue = normalizedValues.value[i];
          minIndex = i;
        }
      }
      
      return (minIndex / normalizedValues.value.length) * 100;
    };
    
    const getValleyHeight = () => {
      if (!normalizedValues.value || normalizedValues.value.length === 0) return 0;
      
      // Find the height of the valley
      const middleStart = Math.floor(normalizedValues.value.length * 0.4);
      const middleEnd = Math.floor(normalizedValues.value.length * 0.7);
      let minValue = normalizedValues.value[middleStart];
      
      for (let i = middleStart; i < middleEnd; i++) {
        if (normalizedValues.value[i] < minValue) {
          minValue = normalizedValues.value[i];
        }
      }
      
      return minValue;
    };
    
    const getSecondPeakPosition = () => {
      if (!normalizedValues.value || normalizedValues.value.length === 0) return 70;
      
      // Find the position of the second peak (last third)
      const twoThirds = Math.floor(normalizedValues.value.length * 2 / 3);
      let maxIndex = twoThirds;
      let maxValue = normalizedValues.value[twoThirds];
      
      for (let i = twoThirds; i < normalizedValues.value.length; i++) {
        if (normalizedValues.value[i] > maxValue) {
          maxValue = normalizedValues.value[i];
          maxIndex = i;
        }
      }
      
      return (maxIndex / normalizedValues.value.length) * 100;
    };
    
    const getSecondPeakHeight = () => {
      if (!normalizedValues.value || normalizedValues.value.length === 0) return 0;
      
      // Find the height of the second peak
      const twoThirds = Math.floor(normalizedValues.value.length * 2 / 3);
      let maxValue = normalizedValues.value[twoThirds];
      
      for (let i = twoThirds; i < normalizedValues.value.length; i++) {
        if (normalizedValues.value[i] > maxValue) {
          maxValue = normalizedValues.value[i];
        }
      }
      
      return maxValue;
    };

    return {
      loading,
      error,
      selectedMethod,
      horizonDays,
      bwMethod,
      gridSize,
      includeVolumeIndicators,
      distribution,
      stats,
      methodLabel,
      updateChart,
      currentPrice,
      currentPriceError,
      normalizedValues,
      yAxisLabels,
      minPrice,
      maxPrice,
      currentPriceBarIndex,
      linePath,
      hoverTooltipVisible,
      tooltipLeft,
      tooltipTop,
      tooltipPrice,
      tooltipValue,
      handleChartHover,
      hideHoverTooltip,
      getPeakPosition,
      getPeakHeight,
      getValleyPosition,
      getValleyHeight,
      getSecondPeakPosition,
      getSecondPeakHeight
    };
  }
};
</script>

<style scoped>
.price-distribution-chart {
  position: relative;
  width: 100%;
  margin-bottom: 20px;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
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
  border: 4px solid rgba(255, 255, 255, 0.1);
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

/* Enhanced header styling */
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(99, 179, 237, 0.1);
}

.chart-header h3 {
  font-size: 1.1rem;
  font-weight: 500;
  margin: 0;
  color: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.ticker-symbol {
  font-weight: 700;
  color: rgba(36, 139, 188, 1);
}

.chart-title {
  font-weight: 400;
  color: rgba(255, 255, 255, 0.8);
}

.method-badge {
  background: rgba(36, 139, 188, 0.1);
  color: rgba(36, 139, 188, 0.9);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid rgba(36, 139, 188, 0.2);
}

.chart-controls {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 20px;
}

.param-controls {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: nowrap;
}

@media (max-width: 1100px) {
  .chart-controls {
    flex-wrap: wrap;
  }
  
  .param-controls {
    flex-wrap: wrap;
    margin-top: 10px;
  }
}

.control-select {
  background: linear-gradient(180deg, rgba(22, 30, 46, 0.8) 0%, rgba(15, 23, 42, 0.8) 100%);
  border: 1px solid rgba(99, 179, 237, 0.3);
  border-radius: 6px;
  padding: 8px 12px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.85rem;
  transition: all 0.2s;
  cursor: pointer;
  outline: none;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  height: 36px;
}

.control-select:hover {
  border-color: rgba(99, 179, 237, 0.5);
  box-shadow: 0 2px 8px rgba(99, 179, 237, 0.2);
}

.control-select option {
  background-color: rgba(15, 23, 42, 1);
  color: rgba(255, 255, 255, 0.9);
}

.param-slider {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
}

.param-slider label,
.horizon-days label,
.volume-toggle label {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
}

.param-slider input[type="range"] {
  width: 100px;
  height: 4px;
  background-color: rgba(255, 255, 255, 0.15);
  border-radius: 2px;
  -webkit-appearance: none;
  appearance: none;
}

.param-slider input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  background: var(--blue-color, #2196F3);
  border-radius: 50%;
  cursor: pointer;
}

.param-value {
  font-size: 0.8rem;
  min-width: 30px;
  text-align: right;
  color: rgba(255, 255, 255, 0.8);
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  padding: 2px 5px;
}

.horizon-days {
  display: flex;
  align-items: center;
  gap: 5px;
  height: 36px;
}

.horizon-days input {
  width: 60px;
  background-color: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  color: inherit;
  padding: 4px 8px;
  font-size: 0.8rem;
  height: 28px;
}

/* Volume toggle styling */
.volume-toggle {
  display: flex;
  align-items: center;
  height: 36px;
  margin-left: 5px;
}

.volume-toggle label {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  height: 100%;
}

.volume-toggle input[type="checkbox"] {
  cursor: pointer;
  width: 16px;
  height: 16px;
  margin: 0;
}

.css-chart-container {
  position: relative;
  height: 350px;
  background-color: rgba(10, 15, 30, 0.95);
  border-radius: 12px;
  padding: 30px 15px 40px;
  display: flex;
  align-items: stretch;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(36, 139, 188, 0.1);
  backdrop-filter: blur(4px);
}

.y-axis {
  width: 50px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding-top: 5px;
  padding-bottom: 5px;
}

.y-label {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
  padding-right: 5px;
  text-align: right;
}

/* Distribution markers styling */
.distribution-markers {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 15;
}

.dist-marker {
  position: absolute;
  transform: translate(-50%, 10%);
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 20;
}

.marker-point {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.5);
}

.dist-marker .marker-label {
  position: relative;
  padding: 2px 6px;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
  margin-top: 3px;
}

/* Volume toggle styling */
.volume-toggle {
  display: flex;
  align-items: center;
  height: 36px;
}

.volume-toggle label {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  height: 100%;
}

.volume-toggle input[type="checkbox"] {
  cursor: pointer;
  width: 16px;
  height: 16px;
  margin: 0;
}

.chart-grid {
  position: absolute;
  top: 0;
  left: 65px;
  right: 15px;
  bottom: 0;
  z-index: 0;
  pointer-events: none;
}

.grid-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background-color: rgba(255, 255, 255, 0.03);
}

.grid-line.vertical {
  width: 1px;
  height: 100%;
  top: 0;
  bottom: 0;
}

.chart-bars {
  flex: 1;
  display: flex;
  position: relative;
  align-items: flex-end;
  height: 100%;
  gap: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  border-left: 1px solid rgba(255, 255, 255, 0.2);
}

.bar {
  flex: 1;
  background-color: transparent;
  position: relative;
  z-index: 1;
}

/* Only show points for line chart */
.bar::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 100%;
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background-color: rgba(36, 139, 188, 0.8);
  transform: translateX(-50%);
  z-index: 3;
  opacity: 0.6;
}

/* Style histogram bars differently */
.hist-bar {
  background-color: rgba(36, 139, 188, 0.4);
  border-top-left-radius: 2px;
  border-top-right-radius: 2px;
  margin: 0 1px;
  transition: background-color 0.2s ease;
}

.hist-bar:hover {
  background-color: rgba(36, 139, 188, 0.6);
}

.hist-bar::after {
  display: none;
}

/* SVG line overlay */
.line-path-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 2;
  pointer-events: none; /* Allow clicks to pass through */
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.2));
}

.line-path-overlay path {
  transition: all 0.5s ease;
  stroke-dasharray: 2000;
  stroke-dashoffset: 2000;
  animation: dash 1.5s ease-in-out forwards;
}

@keyframes dash {
  to {
    stroke-dashoffset: 0;
  }
}

.line-path-overlay:hover path {
  stroke-width: 2px;
}

.x-axis {
  position: absolute;
  bottom: 20px;
  left: 65px;
  right: 15px;
  display: flex;
  justify-content: space-between;
}

.x-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
}

.axis-labels {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
}

.x-axis-title {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
}

.y-axis-title {
  position: absolute;
  top: 50%;
  left: -5px;
  transform: rotate(-90deg) translateX(-50%);
  transform-origin: left;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
}

.current-price-marker {
  position: absolute;
  bottom: 0;
  top: 0;
  width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 10;
}

.marker-line {
  height: 100%;
  width: 2px;
  background-color: rgba(236, 72, 153, 0.8);
  z-index: 5;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    opacity: 0.6;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0.6;
  }
}

.marker-label {
  position: absolute;
  top: 5px;
  padding: 4px 8px;
  background-color: rgba(236, 72, 153, 0.9);
  color: white;
  border-radius: 4px;
  font-size: 0.75rem;
  white-space: nowrap;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
  transform: translateY(-5px);
  z-index: 10; /* Ensure label is above other elements */
}

/* Position label to the right for data points near the right edge */
.label-top {
  right: 0;
  top: -30px; /* Move above the line instead of below */
  left: auto;
}

.chart-stats {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  margin-top: 15px;
  background-color: rgba(10, 15, 30, 0.8);
  border-radius: 12px;
  padding: 18px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(36, 139, 188, 0.1);
  backdrop-filter: blur(4px);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 80px;
  padding: 8px 12px;
  border-radius: 6px;
  background-color: rgba(255, 255, 255, 0.04);
  transition: background-color 0.2s ease;
}

.stat-item:hover {
  background-color: rgba(255, 255, 255, 0.08);
  transform: translateY(-2px);
  border: 1px solid rgba(99, 179, 237, 0.2);
}

.stat-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 5px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-weight: 600;
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.95);
}

.current-price-stat {
  background-color: rgba(236, 72, 153, 0.15);
  padding: 8px 12px;
  border-radius: 8px;
  border-left: 3px solid rgba(236, 72, 153, 0.8);
  box-shadow: 0 0 15px rgba(236, 72, 153, 0.2);
  animation: highlight 2s infinite;
}

@keyframes highlight {
  0% {
    background-color: rgba(236, 72, 153, 0.1);
  }
  50% {
    background-color: rgba(236, 72, 153, 0.15);
  }
  100% {
    background-color: rgba(236, 72, 153, 0.1);
  }
}

.current-price-error {
  background-color: rgba(236, 72, 153, 0.05);
  padding: 8px 12px;
  border-radius: 6px;
  border-left: 3px solid rgba(236, 72, 153, 0.3);
}

.error-value {
  color: rgba(255, 99, 132, 0.7);
  font-size: 0.9rem;
  font-style: italic;
}

/* Add grid lines to the chart */
.chart-grid {
  position: absolute;
  top: 0;
  left: 65px;
  right: 15px;
  bottom: 0;
  z-index: 0;
  pointer-events: none;
}

.grid-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background-color: rgba(255, 255, 255, 0.03);
}

.grid-line.vertical {
  width: 1px;
  height: 100%;
  top: 0;
  bottom: 0;
}

/* Improved transition effects */
.chart-bars {
  transition: opacity 0.3s ease;
}

.line-path-overlay path {
  transition: all 0.5s ease;
  stroke-dasharray: 2000;
  stroke-dashoffset: 2000;
  animation: dash 1.5s ease-in-out forwards;
}

@keyframes dash {
  to {
    stroke-dashoffset: 0;
  }
}

/* Enhance hover effects */
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 80px;
  padding: 8px 12px;
  border-radius: 8px;
  background-color: rgba(255, 255, 255, 0.04);
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.stat-item:hover {
  background-color: rgba(255, 255, 255, 0.08);
  transform: translateY(-2px);
  border: 1px solid rgba(99, 179, 237, 0.2);
}

/* More vibrant colors for the current price */
.current-price-stat {
  background-color: rgba(236, 72, 153, 0.15);
  padding: 8px 12px;
  border-radius: 8px;
  border-left: 3px solid rgba(236, 72, 153, 0.8);
  box-shadow: 0 0 15px rgba(236, 72, 153, 0.2);
  animation: highlight 2s infinite;
}

/* Add styles for hover tooltip */
.chart-hover-overlay {
  position: absolute;
  top: 10px;
  left: 40px; /* Account for y-axis width */
  right: 10px;
  bottom: 30px; /* Account for x-axis height */
  z-index: 20;
  cursor: crosshair;
}

.hover-tooltip {
  position: absolute;
  transform: translate(-50%, -100%);
  background-color: rgba(20, 30, 50, 0.9);
  border: 1px solid rgba(36, 139, 188, 0.6);
  border-radius: 6px;
  padding: 6px 10px;
  pointer-events: none;
  z-index: 50;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(5px);
  transition: opacity 0.15s ease;
}

.tooltip-price {
  font-size: 0.8rem;
  font-weight: 600;
  color: rgba(236, 72, 153, 1);
}

.tooltip-value {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 2px;
}
</style>
