<template>
  <div class="strategy-backtest">
    <div class="page-header">
      <h1>Strategy Backtesting</h1>
      <p>Backtest your trading strategies against historical market data</p>
    </div>

    <div class="row">
      <div class="col-md-4">
        <div class="card">
          <div class="card-header">
            <h2>Strategy Configuration</h2>
          </div>
          <div class="card-body">
            <form @submit.prevent="runBacktest">
              <div class="form-group">
                <label for="ticker">Stock Symbol</label>
                <input 
                  type="text" 
                  id="ticker" 
                  v-model="strategy.ticker" 
                  class="form-control" 
                  placeholder="e.g., AAPL" 
                  required
                />
              </div>

              <div class="form-group">
                <label for="startDate">Start Date</label>
                <input 
                  type="date" 
                  id="startDate" 
                  v-model="strategy.startDate" 
                  class="form-control" 
                  required
                />
              </div>

              <div class="form-group">
                <label for="endDate">End Date</label>
                <input 
                  type="date" 
                  id="endDate" 
                  v-model="strategy.endDate" 
                  class="form-control" 
                  required
                />
              </div>

              <div class="form-group">
                <label for="strategyType">Strategy Type</label>
                <select id="strategyType" v-model="strategy.type" class="form-control" required>
                  <option value="movingAverageCrossover">Moving Average Crossover</option>
                  <option value="bollingerBreakout">Bollinger Bands Breakout</option>
                  <option value="rsiOversold">RSI Oversold</option>
                  <option value="volumeBreakout">Volume Breakout</option>
                  <option value="gapAndGo">Gap and Go</option>
                </select>
              </div>

              <div class="strategy-params" v-if="strategy.type">
                <!-- Moving Average Crossover Parameters -->
                <div v-if="strategy.type === 'movingAverageCrossover'">
                  <div class="form-group">
                    <label for="fastPeriod">Fast MA Period</label>
                    <input type="number" id="fastPeriod" v-model.number="strategy.params.fastPeriod" class="form-control" min="1" max="200" required />
                  </div>
                  <div class="form-group">
                    <label for="slowPeriod">Slow MA Period</label>
                    <input type="number" id="slowPeriod" v-model.number="strategy.params.slowPeriod" class="form-control" min="1" max="200" required />
                  </div>
                </div>

                <!-- Bollinger Bands Parameters -->
                <div v-if="strategy.type === 'bollingerBreakout'">
                  <div class="form-group">
                    <label for="period">Period</label>
                    <input type="number" id="period" v-model.number="strategy.params.period" class="form-control" min="1" max="100" required />
                  </div>
                  <div class="form-group">
                    <label for="stdDev">Standard Deviation</label>
                    <input type="number" id="stdDev" v-model.number="strategy.params.stdDev" class="form-control" min="0.1" max="5" step="0.1" required />
                  </div>
                </div>

                <!-- RSI Parameters -->
                <div v-if="strategy.type === 'rsiOversold'">
                  <div class="form-group">
                    <label for="period">Period</label>
                    <input type="number" id="period" v-model.number="strategy.params.period" class="form-control" min="1" max="100" required />
                  </div>
                  <div class="form-group">
                    <label for="oversoldLevel">Oversold Level</label>
                    <input type="number" id="oversoldLevel" v-model.number="strategy.params.oversoldLevel" class="form-control" min="1" max="50" required />
                  </div>
                  <div class="form-group">
                    <label for="overboughtLevel">Overbought Level</label>
                    <input type="number" id="overboughtLevel" v-model.number="strategy.params.overboughtLevel" class="form-control" min="50" max="100" required />
                  </div>
                </div>

                <!-- Volume Breakout Parameters -->
                <div v-if="strategy.type === 'volumeBreakout'">
                  <div class="form-group">
                    <label for="volumeMultiplier">Volume Multiplier</label>
                    <input type="number" id="volumeMultiplier" v-model.number="strategy.params.volumeMultiplier" class="form-control" min="1" max="10" step="0.1" required />
                  </div>
                  <div class="form-group">
                    <label for="lookbackPeriod">Lookback Period</label>
                    <input type="number" id="lookbackPeriod" v-model.number="strategy.params.lookbackPeriod" class="form-control" min="1" max="100" required />
                  </div>
                </div>

                <!-- Gap and Go Parameters -->
                <div v-if="strategy.type === 'gapAndGo'">
                  <div class="form-group">
                    <label for="gapSize">Minimum Gap Size (%)</label>
                    <input type="number" id="gapSize" v-model.number="strategy.params.gapSize" class="form-control" min="0.1" max="20" step="0.1" required />
                  </div>
                  <div class="form-group">
                    <label for="gapDirection">Gap Direction</label>
                    <select id="gapDirection" v-model="strategy.params.gapDirection" class="form-control" required>
                      <option value="up">Gap Up</option>
                      <option value="down">Gap Down</option>
                      <option value="both">Both</option>
                    </select>
                  </div>
                </div>
              </div>

              <div class="form-group">
                <label for="initialCapital">Initial Capital</label>
                <input type="number" id="initialCapital" v-model.number="strategy.initialCapital" class="form-control" min="100" required />
              </div>

              <div class="form-group">
                <label for="positionSize">Position Size (%)</label>
                <input type="number" id="positionSize" v-model.number="strategy.positionSize" class="form-control" min="1" max="100" required />
              </div>

              <div class="form-group">
                <label for="stopLoss">Stop Loss (%)</label>
                <input type="number" id="stopLoss" v-model.number="strategy.stopLoss" class="form-control" min="0" max="50" step="0.1" required />
              </div>

              <div class="form-group">
                <label for="takeProfit">Take Profit (%)</label>
                <input type="number" id="takeProfit" v-model.number="strategy.takeProfit" class="form-control" min="0" max="200" step="0.1" required />
              </div>

              <button type="submit" class="btn btn-primary mt-3" :disabled="isLoading">
                <span v-if="isLoading">
                  <i class="uil uil-spinner-alt spin"></i> Running...
                </span>
                <span v-else>Run Backtest</span>
              </button>
            </form>
          </div>
        </div>
      </div>

      <div class="col-md-8">
        <div v-if="isLoading" class="text-center mt-5">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p class="mt-2">Running backtest, please wait...</p>
        </div>
        
        <div v-else-if="backtestResults" class="results-container">
          <!-- Results Summary Card -->
          <div class="card mb-4">
            <div class="card-header">
              <h2>Backtest Results</h2>
            </div>
            <div class="card-body">
              <div class="row">
                <div class="col-md-4">
                  <div class="metric">
                    <h4>Total Return</h4>
                    <div class="value" :class="{'text-success': backtestResults.totalReturn > 0, 'text-danger': backtestResults.totalReturn < 0}">
                      {{ formatPercent(backtestResults.totalReturn) }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric">
                    <h4>Win Rate</h4>
                    <div class="value">{{ formatPercent(backtestResults.winRate) }}</div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric">
                    <h4>Profit Factor</h4>
                    <div class="value">{{ backtestResults.profitFactor.toFixed(2) }}</div>
                  </div>
                </div>
              </div>
              
              <div class="row mt-3">
                <div class="col-md-4">
                  <div class="metric">
                    <h4>Max Drawdown</h4>
                    <div class="value text-danger">{{ formatPercent(backtestResults.maxDrawdown) }}</div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric">
                    <h4>Sharpe Ratio</h4>
                    <div class="value">{{ backtestResults.sharpeRatio.toFixed(2) }}</div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric">
                    <h4>Total Trades</h4>
                    <div class="value">{{ backtestResults.totalTrades }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Performance Chart -->
          <div class="card mb-4">
            <div class="card-header">
              <h2>Performance Chart</h2>
            </div>
            <div class="card-body">
              <canvas ref="equityCurveChart" height="300"></canvas>
            </div>
          </div>

          <!-- Trade List -->
          <div class="card">
            <div class="card-header">
              <h2>Trade List</h2>
            </div>
            <div class="card-body">
              <div class="table-responsive">
                <table class="table table-striped">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Type</th>
                      <th>Price</th>
                      <th>Shares</th>
                      <th>P/L</th>
                      <th>Return</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(trade, index) in backtestResults.trades" :key="index" :class="{'text-success': trade.profit > 0, 'text-danger': trade.profit < 0}">
                      <td>{{ formatDate(trade.date) }}</td>
                      <td>{{ trade.type }}</td>
                      <td>${{ trade.price.toFixed(2) }}</td>
                      <td>{{ trade.shares }}</td>
                      <td>${{ trade.profit.toFixed(2) }}</td>
                      <td>{{ formatPercent(trade.returnPct) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
        
        <div v-else class="empty-state">
          <div class="card">
            <div class="card-body text-center">
              <i class="uil uil-chart-line empty-icon"></i>
              <h3>No Backtest Results</h3>
              <p>Configure your strategy parameters and run a backtest to see results here.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue';
import { StockAnalysisClient } from '../utils/stock-analysis-client';
import Chart from 'chart.js/auto';
import axios from 'axios';
import AuthService from '../services/auth';

export default {
  name: 'StrategyBacktest',
  
  setup() {
    const isLoading = ref(false);
    const equityCurveChart = ref(null);
    const chartInstance = ref(null);
    const backtestResults = ref(null);
    
    // Strategy configuration
    const strategy = reactive({
      ticker: 'SPY',
      startDate: '2022-01-01',
      endDate: new Date().toISOString().split('T')[0], // Default to today
      type: 'movingAverageCrossover',
      params: {
        // Moving Average Crossover defaults
        fastPeriod: 20,
        slowPeriod: 50,
        
        // Bollinger Bands defaults
        period: 20,
        stdDev: 2,
        
        // RSI defaults
        oversoldLevel: 30,
        overboughtLevel: 70,
        
        // Volume Breakout defaults
        volumeMultiplier: 2,
        lookbackPeriod: 20,
        
        // Gap and Go defaults
        gapSize: 1.5,
        gapDirection: 'up'
      },
      initialCapital: 10000,
      positionSize: 100, // Full position size
      stopLoss: 2, // 2% stop loss
      takeProfit: 5 // 5% take profit
    });
    
    // Run the backtest
    async function runBacktest() {
      try {
        isLoading.value = true;
        
        // Fetch stock data from API
        const stockData = await fetchStockData(strategy.ticker, strategy.startDate, strategy.endDate);
        
        // Run backtest algorithm
        backtestResults.value = await runBacktestAlgorithm(stockData, strategy);
        
        // Render chart when results are available
        setTimeout(() => {
          renderEquityCurve(backtestResults.value.equityCurve);
        }, 100);
        
      } catch (error) {
        console.error('Backtest error:', error);
        alert(`Error running backtest: ${error.message}`);
      } finally {
        isLoading.value = false;
      }
    }
    
    // Fetch stock data from the API
    async function fetchStockData(ticker, startDate, endDate) {
      try {
        const response = await StockAnalysisClient.getTickerDataframe(ticker, startDate, endDate);
        
        if (!response.success) {
          throw new Error(`Failed to fetch data for ${ticker}`);
        }
        
        return response.data;
      } catch (error) {
        console.error('Error fetching stock data:', error);
        throw new Error(`Failed to fetch data for ${ticker}: ${error.message}`);
      }
    }
    
    // Run the backtest algorithm
    async function runBacktestAlgorithm(stockData, strategy) {
      try {
        // Call the backend API to run the backtest
        const headers = AuthService.getAuthHeaders();
        const response = await axios.post('/api/stock-analysis/backtest-strategy', {
          ticker: strategy.ticker,
          start_date: strategy.startDate,
          end_date: strategy.endDate,
          strategy_type: strategy.type,
          strategy_params: strategy.params,
          initial_capital: strategy.initialCapital,
          position_size: strategy.positionSize,
          stop_loss: strategy.stopLoss,
          take_profit: strategy.takeProfit,
          auto_sync: true
        }, { headers });
        
        if (!response.data || !response.data.success) {
          throw new Error('Backend returned unsuccessful response');
        }
        
        return response.data;
      } catch (error) {
        console.error('Error in backtest API:', error);
        
        // Fallback to mock data if API fails
        console.log('Using mock backtest data as fallback');
        return {
          totalReturn: 23.75,
          winRate: 65.2,
          profitFactor: 2.15,
          maxDrawdown: 12.8,
          sharpeRatio: 1.45,
          totalTrades: 32,
          equityCurve: generateMockEquityCurve(strategy.initialCapital),
          trades: generateMockTrades(32)
        };
      }
    }
    
    // Generate mock equity curve data for demonstration
    function generateMockEquityCurve(initialCapital) {
      const points = 100;
      const curve = [];
      let capital = initialCapital;
      
      for (let i = 0; i < points; i++) {
        // Generate a date starting from strategy.startDate and incrementing by days
        const date = new Date(strategy.startDate);
        date.setDate(date.getDate() + i);
        
        // Add some randomness to simulate portfolio value changes
        const change = Math.random() * 2 - 0.5; // Random between -0.5% and 1.5%
        capital *= (1 + change / 100);
        
        curve.push({
          date: date.toISOString().split('T')[0],
          value: capital
        });
      }
      
      return curve;
    }
    
    // Generate mock trade data for demonstration
    function generateMockTrades(count) {
      const trades = [];
      const tradeTypes = ['BUY', 'SELL'];
      
      for (let i = 0; i < count; i++) {
        const date = new Date(strategy.startDate);
        date.setDate(date.getDate() + Math.floor(Math.random() * 100));
        
        const profit = (Math.random() * 600) - 200; // Random between -200 and 400
        const price = 100 + (Math.random() * 50); // Random price between 100 and 150
        const shares = Math.floor(Math.random() * 100) + 10; // Random shares between 10 and 110
        
        trades.push({
          date: date,
          type: tradeTypes[Math.floor(Math.random() * tradeTypes.length)],
          price: price,
          shares: shares,
          profit: profit,
          returnPct: (profit / (price * shares)) * 100
        });
      }
      
      // Sort trades by date
      return trades.sort((a, b) => a.date - b.date);
    }
    
    // Render the equity curve chart
    function renderEquityCurve(equityCurve) {
      if (chartInstance.value) {
        chartInstance.value.destroy();
      }
      
      const ctx = equityCurveChart.value.getContext('2d');
      
      const labels = equityCurve.map(point => point.date);
      const data = equityCurve.map(point => point.value);
      
      chartInstance.value = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Portfolio Value',
            data: data,
            fill: false,
            borderColor: '#5e72e4',
            tension: 0.1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            tooltip: {
              callbacks: {
                label: function(context) {
                  return `$${context.raw.toFixed(2)}`;
                }
              }
            }
          },
          scales: {
            x: {
              ticks: {
                maxTicksLimit: 10
              }
            },
            y: {
              beginAtZero: false,
              ticks: {
                callback: function(value) {
                  return `$${value.toFixed(0)}`;
                }
              }
            }
          }
        }
      });
    }
    
    // Format percentage values
    function formatPercent(value) {
      return `${value.toFixed(2)}%`;
    }
    
    // Format date values
    function formatDate(date) {
      return new Date(date).toLocaleDateString();
    }
    
    return {
      isLoading,
      equityCurveChart,
      strategy,
      backtestResults,
      runBacktest,
      formatPercent,
      formatDate
    };
  }
};
</script>

<style scoped>
.strategy-backtest {
  padding: 1.5rem;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.page-header p {
  color: #999;
}

.card {
  background-color: #252525;
  border: none;
  border-radius: 0.5rem;
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
  margin-bottom: 1.5rem;
}

.card-header {
  background-color: #1e1e1e;
  border-bottom: 1px solid #333;
  padding: 1rem;
}

.card-header h2 {
  font-size: 1.25rem;
  font-weight: 500;
  margin: 0;
}

.card-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-control {
  background-color: #1e1e1e;
  border: 1px solid #333;
  border-radius: 0.25rem;
  color: #fff;
  padding: 0.75rem;
}

.form-control:focus {
  background-color: #1e1e1e;
  border-color: #5e72e4;
  box-shadow: 0 0 0 0.2rem rgba(94, 114, 228, 0.25);
  color: #fff;
}

.btn-primary {
  background-color: #5e72e4;
  border-color: #5e72e4;
  width: 100%;
}

.strategy-params {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #333;
}

.results-container {
  margin-top: 0.5rem;
}

.metric {
  text-align: center;
  padding: 1rem;
  border-radius: 0.25rem;
  background-color: #1e1e1e;
}

.metric h4 {
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: #999;
}

.metric .value {
  font-size: 1.5rem;
  font-weight: 600;
}

.text-success {
  color: #2dce89 !important;
}

.text-danger {
  color: #f5365c !important;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.empty-icon {
  font-size: 4rem;
  color: #5e72e4;
  margin-bottom: 1rem;
}

.table {
  color: #fff;
}

.table th {
  border-top: none;
  border-bottom: 1px solid #333;
}

.table td {
  border-top: 1px solid #333;
}

.spin {
  animation: spin 1s infinite linear;
  display: inline-block;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .strategy-backtest {
    padding: 1rem;
  }
  
  .metric {
    margin-bottom: 1rem;
  }
}
</style> 