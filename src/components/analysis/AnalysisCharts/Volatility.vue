<template>
  <div class="volatility-chart">
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Loading chart data...</p>
    </div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="chart-header">
        <h3>{{ ticker }} Volatility Analysis</h3>
      </div>
      <div class="charts-container">
        <div class="charts-row">
          <div class="chart-wrapper">
            <h4>Price Chart</h4>
            <div ref="priceChartCanvas" style="height: 100%;"></div>
          </div>
        </div>
        <div class="charts-row">
          <div class="chart-wrapper">
            <h4>{{ ticker }} Return Distribution</h4>
            <div class="controls-container mb-3">
              <div class="d-flex justify-content-end align-items-center">
                <span class="controls-label me-3">Chart Controls:</span>
                <div class="slider-container me-4">
                  <div class="d-flex align-items-center">
                    <label for="range-slider" class="slider-label me-2">Range:</label>
                    <input type="range" class="form-range" id="range-slider" min="10" max="100" step="5" v-model.number="rangeLimit" />
                    <span class="value-badge ms-2">±{{ rangeLimit }}%</span>
                  </div>
                </div>
                <div class="slider-container">
                  <div class="d-flex align-items-center">
                    <label for="step-slider" class="slider-label me-2">Bucket:</label>
                    <input type="range" class="form-range" id="step-slider" min="0.25" max="5" step="0.25" v-model.number="step" />
                    <span class="value-badge ms-2">{{ step.toFixed(2) }}%</span>
                  </div>
                </div>
              </div>
            </div>
            <div ref="distributionChartCanvas" style="height: 400px;"></div>
          </div>
        </div>
      </div>
      <div class="volatility-stats">
        <div class="stat-item">
          <span class="stat-label">Average Daily Volatility:</span>
          <span class="stat-value">{{ (avgVolatility * 100).toFixed(2) }}%</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Standard Deviation:</span>
          <span class="stat-value">{{ (stdVolatility * 100).toFixed(2) }}%</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Annualized Volatility:</span>
          <span class="stat-value">{{ (stdVolatility * 100 * Math.sqrt(252)).toFixed(2) }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import StockAnalysisClient from '../../../utils/stock-analysis-client';

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
  }
});

const priceChartCanvas = ref(null);
const distributionChartCanvas = ref(null);
let priceChart = null;
let distributionChart = null;
const loading = ref(true);
const error = ref(null);
const avgVolatility = ref(0);
const stdVolatility = ref(0);
const returnsDistribution = ref([]);
const priceData = ref({
  dates: [],
  prices: []
});

// Chart control parameters
const rangeLimit = ref(30);
const step = ref(1);

// Define colors locally
const cssColor87 = "rgba(255, 255, 255, 0.87)";
const cssColor60 = "rgba(255, 255, 255, 0.60)";
const cssColor38 = "rgba(255, 255, 255, 0.38)";
const blackbg7 = "hsl(0, 0%, 7%)";

const normalPDF = (x, mean, stdDev) => {
  if (stdDev <= 0) return 0;
  return (1 / (stdDev * Math.sqrt(2 * Math.PI))) * Math.exp(-0.5 * Math.pow((x - mean) / stdDev, 2));
};

const fetchData = async () => {
  if (!props.ticker) {
    error.value = "No ticker symbol provided";
    loading.value = false;
    return;
  }
  
  loading.value = true;
  error.value = null;
  
  try {
    const response = await StockAnalysisClient.getVolatility(
      props.ticker,
      props.startDate,
      props.endDate
    );
    
    if (!response || !response.price_data || !response.returns_distribution) {
      throw new Error('Invalid response data format');
    }
    
    avgVolatility.value = response.avg_volatility;
    stdVolatility.value = response.std_volatility;
    returnsDistribution.value = response.returns_distribution;
    priceData.value = response.price_data;
    
    loading.value = false;

    await nextTick();
    renderCharts();
  } catch (err) {
    error.value = `Failed to load volatility data: ${err.message}`;
    console.error('Error fetching volatility data:', err);
    loading.value = false;
  }
};

const renderCharts = () => {
  renderPriceChart();
  renderDistributionChart();
};

const renderPriceChart = () => {
  if (!priceChartCanvas.value) return;
  if (priceChart) priceChart.dispose();
  priceChart = echarts.init(priceChartCanvas.value);
  
  const option = {
    tooltip: { trigger: 'axis', backgroundColor: blackbg7, borderColor: blackbg7, textStyle: { color: cssColor87 } },
    xAxis: {
      type: 'category',
      data: priceData.value.dates,
      axisLabel: { color: cssColor60 },
    },
    yAxis: { 
      type: 'value',
      scale: true,
      splitLine: { lineStyle: { type: 'dashed', color: cssColor38 } },
      axisLabel: { color: cssColor60 },
    },
    grid: { left: '5%', right: '5%', bottom: '10%', containLabel: true },
    series: [{
      name: 'Price',
      data: priceData.value.prices,
      type: 'line',
      smooth: true,
      itemStyle: { color: '#26a69a' }
    }]
  };
  priceChart.setOption(option);
};

const renderDistributionChart = () => {
  if (!distributionChartCanvas.value) return;
  if (distributionChart) distributionChart.dispose();
  distributionChart = echarts.init(distributionChartCanvas.value);

  const returns = returnsDistribution.value.map(r => r * 100);
  if (returns.length === 0) {
      distributionChart.clear();
      return;
  }

  const green = '#26a69a';
  const red = '#FF6960';
  const curveColor = '#68CFE8';

  const buckets = [];
  const localRange = rangeLimit.value;
  const localStep = step.value;

  buckets.push({ min: -Infinity, max: -localRange, label: `< -${localRange}`, trades: [] });
  for (let i = -localRange; i < localRange; i += localStep) {
    const min = i;
    const max = i + localStep;
    const label = `${min.toFixed(localStep < 1 ? 2 : 0)} to ${max.toFixed(localStep < 1 ? 2 : 0)}`;
    buckets.push({ min, max, label, trades: [] });
  }
  buckets.push({ min: localRange, max: Infinity, label: `> ${localRange}`, trades: [] });

  returns.forEach(returnPercent => {
    const bucket = buckets.find(b => returnPercent >= b.min && returnPercent < b.max);
    if (bucket) {
      bucket.trades.push(returnPercent);
    }
  });

  const chartData = buckets.map(bucket => ({
      value: bucket.trades.length,
      itemStyle: { color: bucket.max <= 0 ? red : green },
      bucketInfo: {
          range: bucket.label,
          trades: bucket.trades.length,
      }
  }));
  const xAxisData = buckets.map(bucket => bucket.label);

  const normalCurveData = [];
  let mean = 0;
  let stdDev = 0;

  if (returns.length > 1) {
      mean = returns.reduce((sum, val) => sum + val, 0) / returns.length;
      stdDev = Math.sqrt(returns.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / (returns.length -1));

      if (stdDev > 0) {
          const maxBucketValue = Math.max(...chartData.map(d => d.value));
          const maxPdfValue = normalPDF(mean, mean, stdDev);
          const scaleFactor = maxBucketValue / maxPdfValue;
          
          buckets.forEach(bucket => {
              if (bucket.min === -Infinity || bucket.max === Infinity) {
                  normalCurveData.push(null);
                  return;
              }
              const x = (bucket.min + bucket.max) / 2;
              const pdfValue = normalPDF(x, mean, stdDev) * scaleFactor;
              normalCurveData.push(pdfValue);
          });
      }
  }

  const option = {
      tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          backgroundColor: blackbg7,
          borderColor: blackbg7,
          textStyle: { color: cssColor87 },
          formatter: function (params) {
              let result = '';
              params.forEach(p => {
                  if (p.seriesType === 'bar') {
                      const info = p.data.bucketInfo;
                      if (info) {
                          result += `<b>${info.range}%</b><br/>Count: ${info.trades}<br/>`;
                      }
                  } else if (p.seriesType === 'line' && p.value != null) {
                      result += `<b>Normal Distribution</b><br/>Density: ${p.value.toFixed(4)}<br/>`;
                  }
              });
              return result;
          }
      },
      grid: { left: '5%', right: '5%', bottom: '15%', containLabel: true },
      xAxis: {
          type: 'category',
          data: xAxisData,
          axisLabel: { color: cssColor60, rotate: 45, interval: 'auto' },
          name: 'Daily Return (%)',
          nameLocation: 'middle',
          nameGap: 85,
          nameTextStyle: { color: cssColor60 }
      },
      yAxis: [
          {
              type: 'value',
              name: 'Count',
              nameLocation: 'middle',
              nameGap: 50,
              splitLine: { lineStyle: { type: 'dashed', color: cssColor38 } },
              axisLabel: { color: cssColor60 },
              nameTextStyle: { color: cssColor60 }
          },
          {
              type: 'value',
              name: 'Density',
              nameLocation: 'middle',
              nameGap: 40,
              splitLine: { show: false },
              axisLabel: { color: cssColor60, formatter: (value) => value.toFixed(3) },
              nameTextStyle: { color: cssColor60 }
          }
      ],
      legend: { 
          data: ['Returns', 'Normal Distribution'], 
          right: 10, 
          top: 10, 
          textStyle: { color: cssColor87 },
          tooltip: {
              show: true,
              formatter: function(params) {
                  if (params.name === 'Normal Distribution') {
                      return `Normal Distribution<br/>Mean (μ): ${mean.toFixed(2)}%<br/>Std Dev (σ): ${stdDev.toFixed(2)}%`;
                  }
                  return params.name;
              }
          }
      },
      series: [
          {
              name: 'Returns',
              type: 'bar',
              yAxisIndex: 0,
              data: chartData,
              barWidth: '95%',
          },
          {
              name: 'Normal Distribution',
              type: 'line',
              yAxisIndex: 0,
              smooth: true,
              data: normalCurveData,
              symbol: 'none',
              itemStyle: { color: curveColor },
              lineStyle: { width: 3 }
          }
      ]
  };

  distributionChart.setOption(option);
};

let priceChartResizeObserver = null;
let distributionChartResizeObserver = null;

onMounted(async () => {
  if (props.ticker) {
    await fetchData();
  }
  
  await nextTick();

  if (priceChartCanvas.value) {
    priceChartResizeObserver = new ResizeObserver(() => {
      if(priceChart) {
        priceChart.resize();
      }
    });
    priceChartResizeObserver.observe(priceChartCanvas.value);
  }

  if (distributionChartCanvas.value) {
    distributionChartResizeObserver = new ResizeObserver(() => {
      if(distributionChart) {
        distributionChart.resize();
      }
    });
    distributionChartResizeObserver.observe(distributionChartCanvas.value);
  }
});

onUnmounted(() => {
  if (priceChartResizeObserver) {
    priceChartResizeObserver.disconnect();
  }
  if (distributionChartResizeObserver) {
    distributionChartResizeObserver.disconnect();
  }
  
  if (priceChart) {
    priceChart.dispose();
  }
  if (distributionChart) {
    distributionChart.dispose();
  }
});

watch(() => [props.ticker, props.startDate, props.endDate], () => {
  fetchData();
});

watch([rangeLimit, step], () => {
  renderDistributionChart();
});

</script>

<style scoped>
.volatility-chart {
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

.chart-header {
  margin-bottom: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
}

.charts-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.charts-row {
  display: flex;
  width: 100%;
}

.chart-wrapper {
  flex: 1;
  min-height: 300px;
  background-color: rgb(0, 0, 0);
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  padding: 15px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
}

.chart-wrapper h4 {
  margin-top: 0;
  margin-bottom: 10px;
  text-align: center;
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.9);
}

.volatility-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 20px;
  background-color: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 15px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-item {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 150px;
  align-items: center;
}

.stat-label {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 5px;
}

.stat-value {
  font-weight: bold;
  font-size: 1.2rem;
}

.controls-container {
  padding: 0.5rem;
  background-color: rgba(30, 30, 47, 0.7);
  border-radius: 8px;
}

.controls-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #6a8dff;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.slider-container {
  width: 220px;
}

.slider-label {
  font-size: 0.8rem;
  color: #a0a0a0;
  margin-bottom: 0;
  min-width: 55px;
}

.form-range {
  width: 100px;
}

.value-badge {
  background: rgba(106, 141, 255, 0.2);
  color: #6a8dff;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
  min-width: 48px;
  text-align: center;
}

@media (max-width: 768px) {
  .d-flex.justify-content-end {
    flex-direction: column;
    align-items: flex-end;
  }
  
  .slider-container {
    margin-top: 0.5rem;
    width: 100%;
  }
}
</style>
