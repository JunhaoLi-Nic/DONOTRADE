<script setup>
import { ref, onMounted } from 'vue';
import AnalysisStockSidebar from './AnalysisStockSidebar.vue';
import PriceDistribution from './AnalysisCharts/PriceDistribution.vue';
import Volatility from './AnalysisCharts/Volatility.vue';
import HurstExponent from './AnalysisCharts/HurstExponent.vue';
import ConsecutiveMoves from './AnalysisCharts/ConsecutiveMoves.vue';
import NextDayStats from './AnalysisCharts/NextDayStats.vue';
import axios from 'axios';

const activeSection = ref('price-distribution');
const selectedStock = ref('');
const dateRange = ref({ from: '', to: '' });
const isLoading = ref(false);
const analysisData = ref(null);

// Handle analysis request
const fetchAnalysisData = async () => {
  if (!selectedStock.value) return;
  
  isLoading.value = true;
  analysisData.value = null;
  
  try {
    // For now, we're just setting a dummy value for analysisData
    // The actual data fetching will be handled by each chart component
    analysisData.value = { success: true };
    console.log(`Analysis section changed to: ${activeSection.value} for stock: ${selectedStock.value}`);
  } catch (error) {
    console.error(`Error setting up ${activeSection.value} data:`, error);
    analysisData.value = { error: `Failed to load ${activeSection.value} data` };
  } finally {
    isLoading.value = false;
  }
};

// Watch for changes in selected stock or analysis section
const handleStockChange = (stock) => {
  selectedStock.value = stock;
  if (stock) {
    fetchAnalysisData();
  }
};

const handleSectionChange = (section) => {
  activeSection.value = section;
  if (selectedStock.value) {
    fetchAnalysisData();
  }
};

const handleDateRangeChange = (range) => {
  dateRange.value = range;
  if (selectedStock.value) {
    fetchAnalysisData();
  }
};

// Match the section IDs with the backend API routes
const analysisOptions = [
    { id: 'price-distribution', label: 'Price Distribution', icon: 'uil-chart-line' },
    { id: 'volatility', label: 'Volatility Analysis', icon: 'uil-chart-growth' },
    { id: 'hurst', label: 'Hurst Exponent', icon: 'uil-chart-bar' },
    { id: 'consecutive', label: 'Consecutive Moves', icon: 'uil-chart-bar-alt' },
    { id: 'next-day-stats', label: 'Next Day Stats', icon: 'uil-analytics' }
];
</script>

<template>
    <div class="stock-analysis-container">
        <!-- Use the sidebar component -->
        <AnalysisStockSidebar
            :selectedStock="selectedStock"
            :activeSection="activeSection"
            :analysisOptions="analysisOptions"
            @update:selectedStock="handleStockChange"
            @update:activeSection="handleSectionChange"
            @update:dateRange="handleDateRangeChange"
        />

        <!-- Content -->
        <div class="content">
            <div v-if="!selectedStock" class="placeholder">
                <i class="uil uil-chart-pie"></i>
                <p>Select a stock to view analysis</p>
            </div>
            
            <div v-else>
                <div class="analysis-header">
                <h4>{{ selectedStock }} - {{ analysisOptions.find(opt => opt.id === activeSection)?.label }}</h4>
                    <div class="date-range-display" v-if="dateRange.from || dateRange.to">
                        <span v-if="dateRange.from">From: {{ dateRange.from }}</span>
                        <span v-if="dateRange.to">To: {{ dateRange.to }}</span>
                    </div>
                </div>
                
                <div class="analysis-content">
                    <div v-if="isLoading" class="loading">
                        <i class="uil uil-spinner-alt spin"></i>
                        <p>Loading analysis data...</p>
                    </div>
                    
                    <div v-else-if="analysisData && analysisData.error" class="error">
                        <i class="uil uil-exclamation-triangle"></i>
                        <p>{{ analysisData.error }}</p>
                    </div>
                    
                    <div v-else-if="analysisData" class="analysis-data">
                        <!-- Render the appropriate chart component based on activeSection -->
                        <PriceDistribution 
                            v-if="activeSection === 'price-distribution'"
                            :key="'price-' + selectedStock + '-' + (dateRange.from || '') + '-' + (dateRange.to || '')"
                            :ticker="selectedStock"
                            :startDate="dateRange.from"
                            :endDate="dateRange.to"
                        />
                        
                        <Volatility 
                            v-if="activeSection === 'volatility'"
                            :key="'volatility-' + selectedStock + '-' + (dateRange.from || '') + '-' + (dateRange.to || '')"
                            :ticker="selectedStock"
                            :startDate="dateRange.from"
                            :endDate="dateRange.to"
                        />
                        
                        <HurstExponent 
                            v-if="activeSection === 'hurst'"
                            :key="'hurst-' + selectedStock + '-' + (dateRange.from || '') + '-' + (dateRange.to || '')"
                            :ticker="selectedStock"
                            :startDate="dateRange.from"
                            :endDate="dateRange.to"
                        />
                        
                        <ConsecutiveMoves 
                            v-if="activeSection === 'consecutive'"
                            :key="'consecutive-' + selectedStock + '-' + (dateRange.from || '') + '-' + (dateRange.to || '')"
                            :ticker="selectedStock"
                            :startDate="dateRange.from"
                            :endDate="dateRange.to"
                        />
                        
                        <NextDayStats 
                            v-if="activeSection === 'next-day-stats'"
                            :key="'next-day-' + selectedStock + '-' + (dateRange.from || '') + '-' + (dateRange.to || '')"
                            :ticker="selectedStock"
                            :startDate="dateRange.from"
                            :endDate="dateRange.to"
                        />
                    </div>
                    
                    <div v-else class="placeholder">
                        <p>Select analysis parameters and click analyze</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.stock-analysis-container {
    display: flex;
    height: calc(100vh - 140px);
    margin-top: 15px;
    gap: 15px;
    overflow: hidden; /* Prevent container from creating scrollbars */
}

.content {
    flex-grow: 1;
    background-color: var(--black-bg-5);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 20px;
    overflow-y: auto; /* This is the only scrollbar we want */
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
}

.placeholder {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--white-60);
}

.placeholder i {
    font-size: 4rem;
    margin-bottom: 15px;
    opacity: 0.5;
}

.analysis-content {
    background-color: var(--black-bg-7);
    border-radius: 6px;
    padding: 20px;
    margin-top: 20px;
    color: var(--white-60);
    flex: 1;
    overflow: visible; /* Changed from hidden to visible */
    display: flex;
    flex-direction: column;
}

.analysis-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

h4 {
    color: var(--white-87);
    margin: 0;
}

.date-range-display {
    font-size: 0.85rem;
    color: var(--white-60);
    display: flex;
    gap: 15px;
}

.loading, .error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 200px;
}

.loading i, .error i {
    font-size: 3rem;
    margin-bottom: 15px;
}

.error i {
    color: var(--red-color, #ff5252);
}

.spin {
    animation: spin 1s linear infinite;
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.analysis-data {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: visible; /* Changed from hidden to visible */
}
</style>