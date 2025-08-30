<template>
  <div>
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
    <div ref="chartContainer" class="chartClass" style="height: 400px;"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import { amountCase } from '../stores/globals.js';

const props = defineProps({
  trades: {
    type: Array,
    required: true,
  },
});

// Define colors locally to fix the import error
const cssColor87 = "rgba(255, 255, 255, 0.87)";
const cssColor60 = "rgba(255, 255, 255, 0.60)";
const cssColor38 = "rgba(255, 255, 255, 0.38)";
const blackbg7 = "hsl(0, 0%, 7%)";

const chartContainer = ref(null);
let myChart = null;

const rangeLimit = ref(30);
const step = ref(1);

// Helper function to check if a trade is valid and completed
const isValidCompletedTrade = (trade) => {
  return trade && 
         trade.buyQuantity && 
         trade.entryPrice && 
         trade.exitPrice &&
         trade.exitPrice > 0 &&
         trade[amountCase.value + 'Proceeds'] !== undefined &&
         trade.status !== 'open' && 
         trade.status !== 'pending';
};

// Normal distribution PDF function
const normalPDF = (x, mean, stdDev) => {
  return (1 / (stdDev * Math.sqrt(2 * Math.PI))) * Math.exp(-0.5 * Math.pow((x - mean) / stdDev, 2));
};

const renderChart = () => {
  if (!chartContainer.value) return;

  if (myChart) {
    myChart.dispose();
  }
  myChart = echarts.init(chartContainer.value);

  const green = '#26a69a';
  const red = '#FF6960';
  const curveColor = '#68CFE8';

  const buckets = [];
  const localRange = rangeLimit.value;
  const localStep = step.value;

  buckets.push({ min: -Infinity, max: -localRange, label: `< -${localRange}`, trades: [], winners: 0, losers: 0, breakevens: 0 });
  for (let i = -localRange; i < localRange; i += localStep) {
    const min = i;
    const max = i + localStep;
    const label = `${min.toFixed(localStep < 1 ? 2 : 0)} to ${max.toFixed(localStep < 1 ? 2 : 0)}`;
    buckets.push({ min, max, label, trades: [], winners: 0, losers: 0, breakevens: 0 });
  }
  buckets.push({ min: localRange, max: Infinity, label: `> ${localRange}`, trades: [], winners: 0, losers: 0, breakevens: 0 });

  let returnPercentages = [];
  let extremeValueCount = 0;
  let incompleteTradeCount = 0;
  let zeroExitPriceCount = 0;

  if (props.trades) {
    props.trades.forEach(day => {
      if (day && day.trades) {
        day.trades.forEach(trade => {
          // Check for incomplete trades and log issues
          if (!trade) {
            incompleteTradeCount++;
            return;
          }
          if (!trade.exitPrice) {
            incompleteTradeCount++;
            return;
          }
          if (trade.exitPrice === 0) {
            zeroExitPriceCount++;
            return;
          }
          if (!isValidCompletedTrade(trade)) {
            incompleteTradeCount++;
            return;
          }
          
          const cost = trade.buyQuantity * trade.entryPrice;
          
          // Check if cost is valid
          if (!cost || cost === 0) {
            incompleteTradeCount++;
            console.log('Trade cost is zero or invalid:', trade);
            return;
          }
          
          const proceeds = trade[amountCase.value + 'Proceeds'];
          
          // Check if proceeds are valid
          if (proceeds === undefined || proceeds === null) {
            incompleteTradeCount++;
            console.log('Trade proceeds invalid:', trade);
            return;
          }
          
          const returnPercent = (proceeds / cost) * 100;
          
          // Check if it's a valid number
          if (isNaN(returnPercent) || !isFinite(returnPercent)) {
            incompleteTradeCount++;
            console.log('Trade return calculation error:', returnPercent, 'Trade:', trade);
            return;
          }
          
          // Filter out extreme values that might skew the distribution
          if (Math.abs(returnPercent) > 200) {  // Lower extreme value threshold to 200%
            extremeValueCount++;
            console.log('Extreme return value detected:', returnPercent, 'Trade:', trade);
            return;
          }
          
          returnPercentages.push(returnPercent);
          const bucket = buckets.find(b => returnPercent >= b.min && returnPercent < b.max);
          if (bucket) {
            bucket.trades.push(trade);
            if (proceeds > 0) bucket.winners++;
            else if (proceeds < 0) bucket.losers++;
            else bucket.breakevens++;
          }
        });
      }
    });
  }
  
  // Log statistics about filtered trades
  if (extremeValueCount > 0 || incompleteTradeCount > 0 || zeroExitPriceCount > 0) {
    console.log(`Filtering statistics: ${incompleteTradeCount} incomplete trades, ${zeroExitPriceCount} trades with zero exit price, ${extremeValueCount} trades with extreme returns (>200% or <-200%)`);
  }
  console.log(`Total valid trades in chart: ${returnPercentages.length}`);
  
  if (returnPercentages.length > 0) {
    const minReturn = Math.min(...returnPercentages).toFixed(2);
    const maxReturn = Math.max(...returnPercentages).toFixed(2);
    console.log(`Valid trade return range: ${minReturn}% to ${maxReturn}%`);
  }

  const chartData = buckets.map(bucket => ({
      value: bucket.trades.length,
      itemStyle: { color: bucket.max <= 0 ? red : green },
      bucketInfo: {
          range: bucket.label,
          trades: bucket.trades.length,
          winners: bucket.winners,
          losers: bucket.losers,
          breakevens: bucket.breakevens
      }
  }));
  const xAxisData = buckets.map(bucket => bucket.label);

  const normalCurveData = [];
  let mean = 0;
  let stdDev = 0;

  if (returnPercentages.length > 20) {
      // 1.1 Calculate mean (μ) of the return percentages
      // Here we use reduce to sum all values in returnPercentages, then divide by the count to get the mean.
      // Unlike map, which transforms each element and returns a new array of the same length,
      // reduce accumulates a single result (in this case, the sum) by applying a function to each element.
      mean = returnPercentages.reduce((sum, val) => sum + val, 0) / returnPercentages.length;
      
      // 1.2 Calculate standard deviation (σ) of the return percentages
      stdDev = Math.sqrt(
          // The reduce function here iterates over each value in returnPercentages,
          // accumulating the sum of squared differences from the mean.
          // For each 'val', it computes (val - mean)^2 and adds it to 'sum'.
          // The initial value of 'sum' is 0.
          // The final result is the total sum of squared differences, which is then divided by the number of elements to get the variance.
          returnPercentages.reduce(function(sum, val) {
              return sum + Math.pow(val - mean, 2);
          }, 0) / returnPercentages.length
      );

      // 2.1 Compute normal distribution PDF for range of values
      if (stdDev > 0) {
          // Calculate scaling factor for the PDF to match histogram height
          const maxBucketValue = Math.max(...chartData.map(d => d.value));
          const maxPdfValue = normalPDF(mean, mean, stdDev); // Max PDF value is at the mean
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
                          result += `<b>${info.range}%</b><br/>Trades: ${info.trades}<br/>`;
                          if (info.winners > 0) result += `Winners: ${info.winners}<br/>`;
                          if (info.losers > 0) result += `Losers: ${info.losers}<br/>`;
                          if (info.breakevens > 0) result += `Breakeven: ${info.breakevens}<br/>`;
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
          name: 'Return, gain sum (%)',
          nameLocation: 'middle',
          nameGap: 85,
          nameTextStyle: { color: cssColor60, }
      },
      yAxis: [
          {
              type: 'value',
              name: 'Number of Trades',
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
          data: ['Trades', 'Normal Distribution'], 
          right: 10, 
          top: 10, 
          textStyle: { color: cssColor87 },
          tooltip: {
              show: true,
              formatter: function(params) {
                  if (params.name === 'Normal Distribution') {
                      return `Normal Distribution<br/>Mean (μ): ${mean.toFixed(2)}%<br/>Standard Deviation (σ): ${stdDev.toFixed(2)}%`;
                  }
                  return params.name;
              }
          }
      },
      series: [
          {
              name: 'Trades',
              type: 'bar',
              yAxisIndex: 0,
              data: chartData,
              barWidth: '95%',
              barCategoryGap: '5%',
              markLine: {
                  silent: true,
                  symbol: 'none',
                  label: {
                      show: false
                  },
                  lineStyle: {
                      color: cssColor60,
                      type: 'dashed',
                      width: 5
                  },
                  data: [
                      { xAxis: buckets.findIndex(b => b.min <= 0 && b.max > 0) }
                  ]
              }
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

  myChart.setOption(option);
};

let resizeObserver = null;

onMounted(() => {
  nextTick(() => {
    renderChart();
    
    // Use ResizeObserver to handle chart resizing
    if (chartContainer.value) {
      resizeObserver = new ResizeObserver(() => {
        if (myChart) {
          myChart.resize();
        }
      });
      resizeObserver.observe(chartContainer.value);
    }
  });
});

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
  if (myChart) {
    myChart.dispose();
  }
});

watch([rangeLimit, step, () => props.trades], () => {
  renderChart();
  // Ensure chart is properly sized after data changes
  setTimeout(() => {
    if (myChart) {
      myChart.resize();
    }
  }, 50);
}, { deep: true });
</script>

<style scoped>
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