<script setup>
import { ref, onMounted } from 'vue'
import { spinnerLoadingPage } from '../stores/globals';

// Data from the CSV file
const marketData = ref({
  date: '7/22/2025',
  categories: {
    broad: [],
    equalWeightedSectors: [],
    factors: [],
    growth: [],
    thematic: [],
    ark: []
  }
});

const loading = ref(true);

// Mock data structure based on the CSV file
onMounted(() => {
  // In a real implementation, this would load from an API
  // For now, we're using mock data based on the CSV structure
  
  // Broad market ETFs
  marketData.value.categories.broad = [
    { ticker: 'VTI', name: 'Vanguard Total Stock Market Index Fund ETF', price: 309.80, change1D: 0.12, ytdChange: 6.90, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'XLG', name: 'Invesco S&P 500 Top 50 ETF', price: 53.07, change1D: -0.49, ytdChange: 6.22, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'OEF', name: 'iShares S&P 100 ETF', price: 309.94, change1D: -0.26, ytdChange: 7.30, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'SPY', name: 'SPDR S&P 500 ETF Trust', price: 628.86, change1D: 0.01, ytdChange: 7.30, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'DIA', name: 'SPDR Dow Jones Industrial Average ETF Trust', price: 444.96, change1D: 0.34, ytdChange: 4.57, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'RSP', name: 'Invesco S&P 500 Eql Wght ETF', price: 185.89, change1D: 1.27, ytdChange: 6.08, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'MAGS', name: 'Roundhill Magnificent Seven ETF', price: 57.39, change1D: -0.38, ytdChange: 5.46, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'QQQ', name: 'Invesco QQQ Trust, Series 1', price: 561.25, change1D: -0.52, ytdChange: 9.78, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'QTEC', name: 'First Trust NASDAQ-100-Technology Sector Index Fd', price: 217.06, change1D: -0.40, ytdChange: 15.29, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'IWB', name: 'iShares Russell 1000 ETF', price: 345.66, change1D: 0.06, ytdChange: 7.29, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'IWM', name: 'iShares Russell 2000 ETF', price: 223.27, change1D: 0.83, ytdChange: 1.05, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'MDY', name: 'SPDR S&P MidCap 400 ETF Trust', price: 583.26, change1D: 1.29, ytdChange: 2.40, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'IWC', name: 'iShares Micro-Cap ETF', price: 134.82, change1D: -0.44, ytdChange: 3.41, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
  ];
  
  // Equal Weighted Sectors
  marketData.value.categories.equalWeightedSectors = [
    { ticker: 'RSPC', name: 'Invesco S&P 500 Equal Weight Communication Svc ETF', price: 38.11, change1D: 1.00, ytdChange: 11.40, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'RSPD', name: 'Invesco S&P 500 Eql Wght Con DiscrtN ETF', price: 56.27, change1D: 2.20, ytdChange: 5.32, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'RSPS', name: 'Invesco S&P 500 Eql Wght Con Staples ETF', price: 30.74, change1D: 1.97, ytdChange: 2.13, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    // Add more equal-weighted sectors here
  ];
  
  // Factors
  marketData.value.categories.factors = [
    { ticker: 'SPMO', name: 'Invesco S&P 500 Momentum ETF', price: 112.86, change1D: -1.03, ytdChange: 18.79, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'SPHB', name: 'Invesco S&P 500 High Beta ETF', price: 102.17, change1D: 0.02, ytdChange: 15.25, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'SPHQ', name: 'Invesco S&P 500 Quality ETF', price: 71.70, change1D: 0.36, ytdChange: 6.97, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    // Add more factors here
  ];
  
  // Growth
  marketData.value.categories.growth = [
    { ticker: 'IWY', name: 'iShares Russell Top 200 Growth Index Fund', price: 251.11, change1D: -0.63, ytdChange: 6.73, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'IVW', name: 'iShares S&P 500 Growth ETF', price: 111.98, change1D: -0.59, ytdChange: 10.29, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    // Add more growth ETFs here
  ];
  
  // Thematic
  marketData.value.categories.thematic = [
    { ticker: 'AIQ', name: 'Global X Artificial Intelligence & Technology ETF', price: 44.18, change1D: -0.79, ytdChange: 14.34, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'BOTZ', name: 'Global X Robotics and Artificial Intelligence ETF', price: 32.88, change1D: -0.39, ytdChange: 2.91, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    // Add more thematic ETFs here
  ];
  
  // ARK ETFs
  marketData.value.categories.ark = [
    { ticker: 'ARKK', name: 'ARK Innovation UCITS ETF USD Acc ETF', price: 7.87, change1D: -3.37, ytdChange: 32.94, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    { ticker: 'ARKQ', name: 'ARK Autonomous Technology & Robotics ETF', price: 96.79, change1D: -1.42, ytdChange: 25.29, ema20: 'Loading...', ema60: 'Loading...', ema120: 'Loading...', cs: 'Loading...', sm: 'Loading...', ml: 'Loading...', sl: 'Loading...' },
    // Add more ARK ETFs here
  ];
  
  loading.value = false;
});

// Format percentage with + sign for positive values
const formatPercentage = (value) => {
  if (value === undefined || value === null) return 'N/A';
  return value >= 0 ? `+${value.toFixed(2)}%` : `${value.toFixed(2)}%`;
};

// Format price as currency
const formatPrice = (value) => {
  if (value === undefined || value === null) return 'N/A';
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
};
</script>

<template>
  <spinnerLoadingPage/>
  <header class="section-name">
    Market Watchlist / {{ marketData.date }}
  </header>
  
  <div class="market-watchlist">
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <p>Loading market data...</p>
    </div>
    
    <div v-else class="watchlist-container">
      <!-- Broad Market ETFs -->
      <div class="category-section">
        <h2>Broad Market ETFs</h2>
        <div class="table-container">
          <table class="market-table">
            <thead>
              <tr>
                <th class="text-left">Ticker</th>
                <th class="text-left">Name</th>
                <th class="text-right">Price</th>
                <th class="text-right">1D%</th>
                <th class="text-right">YTD%</th>
                <th class="text-right">EMA20</th>
                <th class="text-right">EMA60</th>
                <th class="text-right">EMA120</th>
                <th class="text-right">C/S</th>
                <th class="text-right">S/M</th>
                <th class="text-right">M/L</th>
                <th class="text-right">S/L</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in marketData.categories.broad" :key="`broad-${index}`">
                <td class="text-left ticker-cell">{{ item.ticker }}</td>
                <td class="text-left name-cell">{{ item.name }}</td>
                <td class="text-right">{{ formatPrice(item.price) }}</td>
                <td class="text-right" :class="{ 'positive': item.change1D > 0, 'negative': item.change1D < 0 }">
                  {{ formatPercentage(item.change1D) }}
                </td>
                <td class="text-right" :class="{ 'positive': item.ytdChange > 0, 'negative': item.ytdChange < 0 }">
                  {{ formatPercentage(item.ytdChange) }}
                </td>
                <td class="text-right">{{ item.ema20 }}</td>
                <td class="text-right">{{ item.ema60 }}</td>
                <td class="text-right">{{ item.ema120 }}</td>
                <td class="text-right">{{ item.cs }}</td>
                <td class="text-right">{{ item.sm }}</td>
                <td class="text-right">{{ item.ml }}</td>
                <td class="text-right">{{ item.sl }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- Equal Weighted Sectors -->
      <div class="category-section">
        <h2>Equal Weighted Sectors</h2>
        <div class="table-container">
          <table class="market-table">
            <thead>
              <tr>
                <th class="text-left">Ticker</th>
                <th class="text-left">Name</th>
                <th class="text-right">Price</th>
                <th class="text-right">1D%</th>
                <th class="text-right">YTD%</th>
                <th class="text-right">EMA20</th>
                <th class="text-right">EMA60</th>
                <th class="text-right">EMA120</th>
                <th class="text-right">C/S</th>
                <th class="text-right">S/M</th>
                <th class="text-right">M/L</th>
                <th class="text-right">S/L</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in marketData.categories.equalWeightedSectors" :key="`equal-${index}`">
                <td class="text-left ticker-cell">{{ item.ticker }}</td>
                <td class="text-left name-cell">{{ item.name }}</td>
                <td class="text-right">{{ formatPrice(item.price) }}</td>
                <td class="text-right" :class="{ 'positive': item.change1D > 0, 'negative': item.change1D < 0 }">
                  {{ formatPercentage(item.change1D) }}
                </td>
                <td class="text-right" :class="{ 'positive': item.ytdChange > 0, 'negative': item.ytdChange < 0 }">
                  {{ formatPercentage(item.ytdChange) }}
                </td>
                <td class="text-right">{{ item.ema20 }}</td>
                <td class="text-right">{{ item.ema60 }}</td>
                <td class="text-right">{{ item.ema120 }}</td>
                <td class="text-right">{{ item.cs }}</td>
                <td class="text-right">{{ item.sm }}</td>
                <td class="text-right">{{ item.ml }}</td>
                <td class="text-right">{{ item.sl }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- Factors -->
      <div class="category-section">
        <h2>Factors</h2>
        <div class="table-container">
          <table class="market-table">
            <thead>
              <tr>
                <th class="text-left">Ticker</th>
                <th class="text-left">Name</th>
                <th class="text-right">Price</th>
                <th class="text-right">1D%</th>
                <th class="text-right">YTD%</th>
                <th class="text-right">EMA20</th>
                <th class="text-right">EMA60</th>
                <th class="text-right">EMA120</th>
                <th class="text-right">C/S</th>
                <th class="text-right">S/M</th>
                <th class="text-right">M/L</th>
                <th class="text-right">S/L</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in marketData.categories.factors" :key="`factor-${index}`">
                <td class="text-left ticker-cell">{{ item.ticker }}</td>
                <td class="text-left name-cell">{{ item.name }}</td>
                <td class="text-right">{{ formatPrice(item.price) }}</td>
                <td class="text-right" :class="{ 'positive': item.change1D > 0, 'negative': item.change1D < 0 }">
                  {{ formatPercentage(item.change1D) }}
                </td>
                <td class="text-right" :class="{ 'positive': item.ytdChange > 0, 'negative': item.ytdChange < 0 }">
                  {{ formatPercentage(item.ytdChange) }}
                </td>
                <td class="text-right">{{ item.ema20 }}</td>
                <td class="text-right">{{ item.ema60 }}</td>
                <td class="text-right">{{ item.ema120 }}</td>
                <td class="text-right">{{ item.cs }}</td>
                <td class="text-right">{{ item.sm }}</td>
                <td class="text-right">{{ item.ml }}</td>
                <td class="text-right">{{ item.sl }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- Growth ETFs -->
      <div class="category-section">
        <h2>Growth ETFs</h2>
        <div class="table-container">
          <table class="market-table">
            <thead>
              <tr>
                <th class="text-left">Ticker</th>
                <th class="text-left">Name</th>
                <th class="text-right">Price</th>
                <th class="text-right">1D%</th>
                <th class="text-right">YTD%</th>
                <th class="text-right">EMA20</th>
                <th class="text-right">EMA60</th>
                <th class="text-right">EMA120</th>
                <th class="text-right">C/S</th>
                <th class="text-right">S/M</th>
                <th class="text-right">M/L</th>
                <th class="text-right">S/L</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in marketData.categories.growth" :key="`growth-${index}`">
                <td class="text-left ticker-cell">{{ item.ticker }}</td>
                <td class="text-left name-cell">{{ item.name }}</td>
                <td class="text-right">{{ formatPrice(item.price) }}</td>
                <td class="text-right" :class="{ 'positive': item.change1D > 0, 'negative': item.change1D < 0 }">
                  {{ formatPercentage(item.change1D) }}
                </td>
                <td class="text-right" :class="{ 'positive': item.ytdChange > 0, 'negative': item.ytdChange < 0 }">
                  {{ formatPercentage(item.ytdChange) }}
                </td>
                <td class="text-right">{{ item.ema20 }}</td>
                <td class="text-right">{{ item.ema60 }}</td>
                <td class="text-right">{{ item.ema120 }}</td>
                <td class="text-right">{{ item.cs }}</td>
                <td class="text-right">{{ item.sm }}</td>
                <td class="text-right">{{ item.ml }}</td>
                <td class="text-right">{{ item.sl }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- Thematic ETFs -->
      <div class="category-section">
        <h2>Thematic ETFs</h2>
        <div class="table-container">
          <table class="market-table">
            <thead>
              <tr>
                <th class="text-left">Ticker</th>
                <th class="text-left">Name</th>
                <th class="text-right">Price</th>
                <th class="text-right">1D%</th>
                <th class="text-right">YTD%</th>
                <th class="text-right">EMA20</th>
                <th class="text-right">EMA60</th>
                <th class="text-right">EMA120</th>
                <th class="text-right">C/S</th>
                <th class="text-right">S/M</th>
                <th class="text-right">M/L</th>
                <th class="text-right">S/L</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in marketData.categories.thematic" :key="`thematic-${index}`">
                <td class="text-left ticker-cell">{{ item.ticker }}</td>
                <td class="text-left name-cell">{{ item.name }}</td>
                <td class="text-right">{{ formatPrice(item.price) }}</td>
                <td class="text-right" :class="{ 'positive': item.change1D > 0, 'negative': item.change1D < 0 }">
                  {{ formatPercentage(item.change1D) }}
                </td>
                <td class="text-right" :class="{ 'positive': item.ytdChange > 0, 'negative': item.ytdChange < 0 }">
                  {{ formatPercentage(item.ytdChange) }}
                </td>
                <td class="text-right">{{ item.ema20 }}</td>
                <td class="text-right">{{ item.ema60 }}</td>
                <td class="text-right">{{ item.ema120 }}</td>
                <td class="text-right">{{ item.cs }}</td>
                <td class="text-right">{{ item.sm }}</td>
                <td class="text-right">{{ item.ml }}</td>
                <td class="text-right">{{ item.sl }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- ARK ETFs -->
      <div class="category-section">
        <h2>ARK ETFs</h2>
        <div class="table-container">
          <table class="market-table">
            <thead>
              <tr>
                <th class="text-left">Ticker</th>
                <th class="text-left">Name</th>
                <th class="text-right">Price</th>
                <th class="text-right">1D%</th>
                <th class="text-right">YTD%</th>
                <th class="text-right">EMA20</th>
                <th class="text-right">EMA60</th>
                <th class="text-right">EMA120</th>
                <th class="text-right">C/S</th>
                <th class="text-right">S/M</th>
                <th class="text-right">M/L</th>
                <th class="text-right">S/L</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in marketData.categories.ark" :key="`ark-${index}`">
                <td class="text-left ticker-cell">{{ item.ticker }}</td>
                <td class="text-left name-cell">{{ item.name }}</td>
                <td class="text-right">{{ formatPrice(item.price) }}</td>
                <td class="text-right" :class="{ 'positive': item.change1D > 0, 'negative': item.change1D < 0 }">
                  {{ formatPercentage(item.change1D) }}
                </td>
                <td class="text-right" :class="{ 'positive': item.ytdChange > 0, 'negative': item.ytdChange < 0 }">
                  {{ formatPercentage(item.ytdChange) }}
                </td>
                <td class="text-right">{{ item.ema20 }}</td>
                <td class="text-right">{{ item.ema60 }}</td>
                <td class="text-right">{{ item.ema120 }}</td>
                <td class="text-right">{{ item.cs }}</td>
                <td class="text-right">{{ item.sm }}</td>
                <td class="text-right">{{ item.ml }}</td>
                <td class="text-right">{{ item.sl }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <div class="disclaimer">
        <p>* This content is for educational purposes only and you should not construe any such information as legal, tax, investment, financial, or other advice.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.section-name {
  font-size: small;
  padding: 0% 0% 0% 0%;
  color: #b5abab;
}

.market-watchlist {
  padding: 20px 0;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
}

.loading-spinner {
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  border-top: 4px solid #4a6cf7;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.watchlist-container {
  width: 100%;
}

.category-section {
  margin-bottom: 30px;
  background-color: #1c1c1c;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.category-section h2 {
  font-size: 18px;
  padding: 16px;
  margin: 0;
  color: #e0e0e0;
  border-bottom: 1px solid #2a2a2a;
  background-color: #232323;
}

.table-container {
  width: 100%;
  overflow-x: auto;
}

.market-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.market-table th, 
.market-table td {
  padding: 10px;
  border-bottom: 1px solid #2a2a2a;
  white-space: nowrap;
}

.market-table thead th {
  background-color: #232323;
  color: #a0a0a0;
  font-weight: 500;
  text-align: left;
  position: sticky;
  top: 0;
  z-index: 10;
}

.market-table tbody tr:hover {
  background-color: #2a2a2a;
}

.text-left {
  text-align: left;
}

.text-right {
  text-align: right;
}

.ticker-cell {
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
}

.name-cell {
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.positive {
  color: #4caf50;
}

.negative {
  color: #f44336;
}

.disclaimer {
  margin-top: 20px;
  padding: 10px;
  font-size: 12px;
  color: #999;
  text-align: center;
  border-top: 1px solid #333;
}

/* Responsive styling */
@media (max-width: 768px) {
  .watchlist-container {
    padding: 0;
  }
  
  .market-table {
    font-size: 12px;
  }
  
  .market-table th, 
  .market-table td {
    padding: 8px 4px;
  }
  
  .category-section h2 {
    font-size: 16px;
  }
}
</style> 