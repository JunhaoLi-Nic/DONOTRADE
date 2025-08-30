<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { Chart, registerables } from 'chart.js';
import { amountCase } from '../../stores/globals';
import { useCreatedDateFormat } from '../../utils/utils';
Chart.register(...registerables);

const props = defineProps({
  playbook: {
    type: Object,
    required: true
  },
  trades: {
    type: Array,
    default: () => []
  }
});

// Reference to chart canvas
const chartCanvas = ref(null);
let pnlChart = null;

// Tooltip state management
const activeTooltip = ref(null);
const tooltipPosition = ref({ x: 0, y: 0 });

// Function to show tooltip
function showTooltip(event, metricKey) {
  activeTooltip.value = metricKey;
  
  // Use a small timeout to ensure DOM is updated before calculating position
  setTimeout(() => {
    // Get the tooltip element
    const tooltip = document.querySelector('.custom-tooltip');
    if (!tooltip) return;
    
    // Position tooltip relative to the viewport
    const iconRect = event.target.getBoundingClientRect();
    
    // Position tooltip above the icon
    tooltipPosition.value = {
      x: iconRect.left + (iconRect.width / 2),
      y: iconRect.top - 10
    };
  }, 10);
}

// Function to hide tooltip
function hideTooltip() {
  activeTooltip.value = null;
}

// Metric descriptions for tooltips
const metricDescriptions = {
  netPnL: "Total profit or loss across all trades in this playbook.",
  trades: "Total number of trades executed using this playbook.",
  winRate: "Percentage of trades that resulted in a profit.",
  winLossRatio: "Ratio of winning trades to losing trades. Higher is better.",
  profitFactor: "Ratio of gross profits to gross losses. Values above 1 indicate a profitable strategy.",
  averageROI: "Average Return on Investment across all trades in this playbook.",
  totalWins: "Sum of all profits from winning trades.",
  totalLosses: "Sum of all losses from losing trades.",
  biggestWin: "Largest profit from a single trade.",
  biggestLoss: "Largest loss from a single trade.",
  avgWinner: "Average profit from winning trades.",
  avgLoser: "Average loss from losing trades.",
  avgPnL: "Average profit or loss per trade."
};

// Calculate Win/Loss Ratio
function calculateWinLossRatio() {
  if (!props.trades || props.trades.length === 0) return 'N/A';
  
  // Count wins and losses
  const winCount = props.trades.filter(trade => trade.status === 'WIN').length;
  const lossCount = props.trades.filter(trade => trade.status === 'LOSS').length;
  
  // Calculate ratio
  if (lossCount === 0) return '∞'; // Avoid division by zero
  if (winCount === 0) return '0.00'; // No wins
  
  // Return formatted ratio with 2 decimal places
  return (winCount / lossCount).toFixed(2);
}

// Calculate Average ROI
function calculateAverageROI() {
  if (!props.trades || props.trades.length === 0) {
    return { value: 'N/A', class: '' };
  }
  
  // Calculate total ROI
  let totalROI = 0;
  let validTradeCount = 0;
  
  props.trades.forEach(trade => {
    // Debug log to see what ROI values we're working with
    console.log(`Trade ${trade.id || 'unknown'} (${trade.symbol || 'unknown'}): netROI = ${trade.netROI}, type: ${typeof trade.netROI}`);
    
    let roiValue = null;
    
    // First try to use the existing netROI if it's valid and not zero
    if (trade.netROI !== undefined && trade.netROI !== null && trade.netROI !== 0) {
      try {
        // Convert to number if it's a string and add to total
        roiValue = typeof trade.netROI === 'string' 
          ? parseFloat(trade.netROI.replace('%', '')) 
          : parseFloat(trade.netROI);
      } catch (e) {
        console.error(`Error processing ROI for trade:`, e);
      }
    }
    
    // If netROI is 0 or invalid, calculate it from scratch
    if (!roiValue || isNaN(roiValue) || roiValue === 0) {
      // Calculate ROI from P&L and entry price
      if (trade.netPnL && trade.entryPrice && trade.quantity) {
        const investment = trade.entryPrice * trade.quantity;
        if (investment !== 0) {
          roiValue = (trade.netPnL / investment) * 100;
          console.log(`  - Recalculated ROI: ${roiValue}% from P&L: ${trade.netPnL}, investment: ${investment}`);
        }
      }
    }
    
    // Add to total if we have a valid ROI value
    if (roiValue !== null && !isNaN(roiValue)) {
      console.log(`  - Valid ROI value: ${roiValue}`);
      totalROI += roiValue;
      validTradeCount++;
    } else {
      console.log(`  - Invalid or zero ROI value: ${trade.netROI}`);
    }
  });
  
  // If no valid trades, return N/A
  if (validTradeCount === 0) {
    console.log('No valid ROI values found in trades');
    return { value: 'N/A', class: '' };
  }
  
  // Calculate average
  const averageROI = totalROI / validTradeCount;
  console.log(`Average ROI calculation: ${totalROI} / ${validTradeCount} = ${averageROI}`);
  
  // Return formatted value and class
  return {
    value: formatPercent(averageROI),
    class: averageROI >= 0 ? 'text-success' : 'text-danger'
  };
}

// Calculate cumulative P&L from trades data
const cumulativePnLData = computed(() => {
  const dates = [];
  const cumulativePnL = [];
  let runningTotal = 0;
  
  if (props.trades && props.trades.length > 0) {
    // Sort trades by date (using the trade's close date if available, otherwise open date)
    const sortedTrades = [...props.trades].sort((a, b) => {
      const aDate = a.closeDate !== 0 ? a.closeDate : a.openDate;
      const bDate = b.closeDate !== 0 ? b.closeDate : b.openDate;
      return new Date(aDate) - new Date(bDate);
    });
    
    sortedTrades.forEach(trade => {
      // Use the appropriate amount case if available, default to 'netPnL'
      const proceedKey = amountCase?.value ? `${amountCase.value}Proceeds` : 'netPnL';
      const proceeds = trade[proceedKey] || trade.netPnL || 0;
      
      // Use the consistent date format from utils.js
      const tradeDate = trade.closeDate !== 0 ? trade.closeDate : trade.openDate;
      const formattedDate = useCreatedDateFormat(tradeDate);
      
      // Add to running total and push to arrays
      runningTotal += proceeds;
      dates.push(formattedDate);
      cumulativePnL.push(runningTotal);
    });
  } else if (props.playbook && props.playbook.trades && props.playbook.trades.length > 0) {
    // If no trades prop provided, try to use playbook.trades instead
    const sortedTrades = [...props.playbook.trades].sort((a, b) => {
      const aDate = a.closeDate !== 0 ? a.closeDate : a.openDate;
      const bDate = b.closeDate !== 0 ? b.closeDate : b.openDate;
      return new Date(aDate) - new Date(bDate);
    });
    
    sortedTrades.forEach(trade => {
      // Use the appropriate amount case if available, default to 'netPnL'
      const proceedKey = amountCase?.value ? `${amountCase.value}Proceeds` : 'netPnL';
      const proceeds = trade[proceedKey] || trade.netPnL || 0;
      
      // Use the consistent date format from utils.js
      const tradeDate = trade.closeDate !== 0 ? trade.closeDate : trade.openDate;
      const formattedDate = useCreatedDateFormat(tradeDate);
      
      // Add to running total and push to arrays
      runningTotal += proceeds;
      dates.push(formattedDate);
      cumulativePnL.push(runningTotal);
    });
  }
  
  // If no trades data, provide fallback
  if (dates.length === 0) {
    // Return mock data as fallback with formatted dates
    return {
      dates: ['Sun 13 November 2022', 'Mon 14 November 2022', 'Thu 01 December 2022', 'Mon 19 December 2022'],
      pnl: [0, -711.76, 59637.52, 87996.97]
    };
  }
  
  return {
    dates,
    pnl: cumulativePnL
  };
});

// Helper functions for formatting
function formatCurrency(value) {
  if (value === undefined || value === null) return '';
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPercent(value) {
  if (value === undefined || value === null) return '';
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '%';
}

onMounted(() => {
  console.log('PlaybookOverview component mounted');
  console.log('Playbook data:', props.playbook);
  console.log('Trades data:', props.trades);
  
  // Render chart once DOM is ready
  renderChart();
  
  // Log ROI calculation for debugging
  console.log('Initial ROI calculation:', calculateAverageROI());
});

// Re-render chart if props change
watch(() => [props.playbook, props.trades], () => {
  console.log('Props changed, re-rendering chart');
  renderChart();
  
  // Log ROI calculation for debugging
  console.log('Updated ROI calculation:', calculateAverageROI());
}, { deep: true });

function renderChart() {
  console.log('Rendering chart...');
  
  // Ensure chartCanvas is available
  if (!chartCanvas.value) {
    console.warn('Chart canvas not found');
    setTimeout(renderChart, 200);
    return;
  }
  
  const ctx = chartCanvas.value.getContext('2d');
  
  // Destroy previous chart if it exists
  if (pnlChart) {
    pnlChart.destroy();
  }
  
  // Use real P&L data
  const { dates, pnl } = cumulativePnLData.value;
  
  pnlChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: dates,
      datasets: [{
        label: 'Cumulative P&L ($)',
        data: pnl,
        fill: true,
        backgroundColor: 'rgba(94, 114, 228, 0.1)',
        borderColor: 'rgba(94, 114, 228, 1)',
        borderWidth: 2,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: 'rgba(94, 114, 228, 1)',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: {
            color: 'rgba(255, 255, 255, 0.05)',
          },
          ticks: {
            color: '#999'
          }
        },
        y: {
          grid: {
            color: 'rgba(255, 255, 255, 0.05)',
          },
          ticks: {
            color: '#999',
            callback: function(value) {
              return '$' + value.toLocaleString();
            }
          }
        }
      },
      plugins: {
        tooltip: {
          mode: 'index',
          intersect: false,
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              if (context.parsed.y !== null) {
                label += new Intl.NumberFormat('en-US', {
                  style: 'currency',
                  currency: 'USD'
                }).format(context.parsed.y);
              }
              return label;
            }
          }
        },
        legend: {
          display: false
        }
      }
    }
  });
  console.log('Chart rendered successfully');
}
</script>

<template>
  <div class="overview-container">
    <!-- Debug info -->
    <div v-if="!props.playbook || !props.playbook.stats" class="alert alert-warning">
      No playbook data available or missing stats. Check console for details.
    </div>
    
    <!-- Tag filtering indicator -->
    <div v-if="props.playbook && props.playbook.stats && props.playbook.tagFilterActive" class="alert alert-info mb-3">
      <i class="uil uil-filter me-1"></i> Showing statistics for trades matching selected tags
      <span v-if="props.playbook.stats.tradesCount === 0" class="fw-bold ms-2">
        (No trades match the current tag filter)
      </span>
    </div>
    
    <!-- Stats Grid -->
    <div v-if="props.playbook && props.playbook.stats" class="stats-grid">
      <!-- Row 1: Main Stats -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-title">
            Net P&L
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'netPnL')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value" :class="props.playbook.stats.netPnL >= 0 ? 'text-success' : 'text-danger'">
            ${{ (props.playbook.stats.netPnL || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-title">
            Trades
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'trades')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value">
            {{ props.playbook.stats.tradesCount || 0 }}
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-title">
            Win Rate %
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'winRate')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value">
            {{ ((props.playbook.stats.winRate || 0).toFixed(1)) }}%
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-title">
            Win/Loss Ratio
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'winLossRatio')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value">
            {{ calculateWinLossRatio() }}
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-title">
            Profit Factor
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'profitFactor')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value">
            {{ props.playbook.stats.profitFactor === Infinity ? '∞' : (props.playbook.stats.profitFactor || 0).toFixed(2) }}
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-title">
            Average ROI
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'averageROI')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value" :class="calculateAverageROI().class">
            {{ calculateAverageROI().value }}
          </div>
        </div>
      </div>
      
      <!-- Row 2: Additional Stats -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-title">
            Total Wins
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'totalWins')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value text-success">
            ${{ (props.playbook.stats.totalWins || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-title">
            Total Losses
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'totalLosses')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value text-danger">
            ${{ (Math.abs(props.playbook.stats.totalLosses || 0)).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-title">
            Biggest Win
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'biggestWin')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value text-success">
            ${{ (props.playbook.stats.biggestWin || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-title">
            Biggest Loss
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'biggestLoss')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value text-danger">
            ${{ (Math.abs(props.playbook.stats.biggestLoss || 0)).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-title">
            Avg. Winner
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'avgWinner')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value text-success">
            ${{ (props.playbook.stats.avgWin || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-title">
            Avg. Loser
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'avgLoser')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value text-danger">
            ${{ (props.playbook.stats.avgLoss || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
          </div>
        </div>
        
        <div class="stat-card">
          <div class="stat-title">
            Average P&L
            <i class="uil uil-info-circle stat-info" @mouseenter="showTooltip($event, 'avgPnL')" @mouseleave="hideTooltip"></i>
          </div>
          <div class="stat-value" 
              :class="props.playbook.stats.netPnL && props.trades.length ? 
                    (props.playbook.stats.netPnL / props.trades.length >= 0 ? 'text-success' : 'text-danger') : ''">
            ${{ props.playbook.stats.netPnL && props.trades.length ? 
                formatCurrency(props.playbook.stats.netPnL / props.trades.length) : 'N/A' }}
          </div>
        </div>
      </div>
      
      <!-- Cumulative P&L Chart -->
      <div class="chart-section">
        <h6>Cumulative P&L</h6>
        <div class="chart-container">
          <canvas ref="chartCanvas"></canvas>
        </div>
      </div>
    </div>
    
    <!-- Description -->
    <div v-if="props.playbook.description" class="description-section">
      <h3 class="section-title">Description</h3>
      <div class="description-content" v-html="props.playbook.description"></div>
    </div>
    
    <div v-else-if="props.playbook.playbook" class="description-section">
      <h3 class="section-title">Description</h3>
      <div class="description-content" v-html="props.playbook.playbook"></div>
    </div>
    
    <!-- Custom Tooltip -->
    <div v-if="activeTooltip" class="custom-tooltip" :style="{ left: tooltipPosition.x + 'px', top: tooltipPosition.y + 'px' }">
      {{ metricDescriptions[activeTooltip] }}
      <div class="tooltip-arrow"></div>
    </div>
  </div>
</template>

<style scoped>
.overview-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.alert {
  padding: 0.75rem 1.25rem;
  border-radius: 0.375rem;
  margin-bottom: 1rem;
}

.alert-warning {
  background-color: rgba(251, 99, 64, 0.1);
  color: #fb6340;
  border: 1px solid rgba(251, 99, 64, 0.2);
}

.alert-info {
  background-color: rgba(0, 123, 255, 0.1);
  color: #007bff;
  border: 1px solid rgba(0, 123, 255, 0.2);
}

.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
}

.row-title {
  font-size: 1rem;
  font-weight: 500;
  margin-bottom: 0.75rem;
  color: #fff;
}

.stat-card {
  background-color: #252525;
  border-radius: 0.5rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

.stat-title {
  font-size: 0.85rem;
  color: #999;
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stat-info {
  cursor: help;
  font-size: 0.85rem;
  transition: color 0.2s ease;
  position: relative;
}

.stat-info:hover {
  color: #5e72e4;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 600;
}

.text-success {
  color: #2dce89;
}

.text-danger {
  color: #f5365c;
}

/* Chart styling */
.chart-section {
  background-color: #252525;
  border-radius: 0.5rem;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  margin: 1rem 0;
}

.chart-section h6 {
  margin-bottom: 1rem;
  font-size: 1rem;
  font-weight: 500;
}

.chart-container {
  position: relative;
  height: 500px;
  width: 100%;
  max-width: 2500px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Trade stats section */
.trade-stats-section {
  margin-top: 0.5rem;
  margin-bottom: 1rem;
}

.trade-stats-section h6 {
  margin-bottom: 1rem;
  font-size: 1rem;
  font-weight: 500;
}

.trade-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
}

.chart-header {
  padding: 1rem;
  border-bottom: 1px solid #333;
}

.chart-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 500;
}

.chart-body {
  padding: 1rem;
  position: relative;
}

.chart-fallback {
  width: 100%;
  height: 250px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0,0,0,0.05);
  border-radius: 8px;
}

.chart-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #999;
}

.chart-loading i {
  font-size: 3rem;
  margin-bottom: 1rem;
}

/* Custom Tooltip */
.custom-tooltip {
  position: fixed;
  background-color: #333;
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-size: 0.85rem;
  z-index: 1000;
  pointer-events: none; /* Ensure tooltip doesn't interfere with mouse events */
  max-width: 250px;
  word-wrap: break-word;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
  border: 1px solid #555;
  transform: translate(-50%, -100%);
  margin-top: -10px;
  text-align: center;
}

.tooltip-arrow {
  position: absolute;
  width: 0;
  height: 0;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-top: 8px solid #333;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }
  
  .chart-container {
    height: 250px;
  }
}

/* Support for Bootstrap classes used in the template */
.mb-3 {
  margin-bottom: 1rem;
}

.me-1 {
  margin-right: 0.25rem;
}

.ms-2 {
  margin-left: 0.5rem;
}

.fw-bold {
  font-weight: bold;
}
</style> 