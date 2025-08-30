<script setup>
import { defineProps, defineEmits, ref, computed, onMounted, watch } from 'vue';
import axios from 'axios';

const props = defineProps({
  selectedStock: {
    type: String,
    default: ''
  },
  activeSection: {
    type: String,
    default: 'price-distribution'
  },
  analysisOptions: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['update:selectedStock', 'update:activeSection', 'update:dateRange']);
const searchQuery = ref('');
const filteredTickers = ref([]);
const showDropdown = ref(false);
const isLoading = ref(false);
const dateFrom = ref('');
const dateTo = ref('');
const searchTimeout = ref(null);
const tickerCount = ref(0);

// Format today's date as YYYY-MM-DD for max date
const today = new Date().toISOString().split('T')[0];

// Calculate default date range
const setDefaultDateRange = () => {
  // Get current date
  const currentDate = new Date();
  
  // Set end date to today
  const toDate = new Date(currentDate);
  
  // Set start date to 1 year ago
  const fromDate = new Date(currentDate);
  fromDate.setFullYear(currentDate.getFullYear() - 1);
  
  // Format dates as YYYY-MM-DD
  dateTo.value = toDate.toISOString().split('T')[0];
  dateFrom.value = fromDate.toISOString().split('T')[0];
  
  console.log(`Setting default date range: ${dateFrom.value} to ${dateTo.value}`);
  
  // Emit the initial date range
  updateDateRange();
};

// Quick date range selection options
const quickDateRanges = [
  { label: '1Y', years: 1 },
  { label: '2Y', years: 2 },
  { label: '3Y', years: 3 },
  { label: '5Y', years: 5 },
  { label: 'YTD', ytd: true },
  { label: 'MAX', max: true }
];

// Set date range based on quick selection
const setQuickDateRange = (range) => {
  // Get current date
  const currentDate = new Date();
  
  // Set end date to today
  const toDate = new Date(currentDate);
  
  // Set start date based on selection
  const fromDate = new Date(currentDate);
  
  if (range.years) {
    fromDate.setFullYear(currentDate.getFullYear() - range.years);
  } else if (range.months) {
    fromDate.setMonth(currentDate.getMonth() - range.months);
  } else if (range.ytd) {
    fromDate.setMonth(0);
    fromDate.setDate(1);
  } else if (range.max) {
    // For MAX option, use a far past date (10 years ago)
    fromDate.setFullYear(currentDate.getFullYear() - 100);
  }
  
  // Format dates as YYYY-MM-DD
  dateTo.value = toDate.toISOString().split('T')[0];
  dateFrom.value = fromDate.toISOString().split('T')[0];
  
  console.log(`Setting date range: ${dateFrom.value} to ${dateTo.value}`);
  
  // Check if the current section is hurst and ensure minimum date range
  if (props.activeSection === 'hurst') {
    ensureMinimumDateRangeForHurst();
  } else {
    updateDateRange();
  }
};

// Ensure minimum date range for Hurst exponent analysis
const ensureMinimumDateRangeForHurst = () => {
  const start = new Date(dateFrom.value);
  const end = new Date(dateTo.value);
  
  // Calculate difference in days
  const diffTime = Math.abs(end - start);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  // Minimum required days for Hurst (assuming window size of 126)
  const minRequiredDays = 126 * 1.5;
  
  if (diffDays < minRequiredDays) {
    console.log(`Date range too short for Hurst analysis (${diffDays} days), extending to at least ${minRequiredDays} days`);
    
    // Keep the end date the same, extend the start date
    const newStart = new Date(end);
    newStart.setDate(newStart.getDate() - Math.ceil(minRequiredDays));
    dateFrom.value = newStart.toISOString().split('T')[0];
    
    console.log(`Extended date range for Hurst: ${dateFrom.value} to ${dateTo.value}`);
  }
  
  updateDateRange();
};

// Watch for changes in activeSection to adjust date range if needed
watch(() => props.activeSection, (newSection) => {
  if (newSection === 'hurst') {
    ensureMinimumDateRangeForHurst();
  }
});

// Fetch total ticker count
const fetchTickerCount = async () => {
  try {
    const response = await axios.get('/api/stock-analysis/tickers', {
      params: { limit: 1, page: 1 }
    });
    tickerCount.value = response.data.total || 0;
  } catch (error) {
    console.error('Error fetching ticker count:', error);
  }
};

// Debounced search function
const debouncedSearch = async () => {
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value);
  }
  
  searchTimeout.value = setTimeout(async () => {
    if (!searchQuery.value || searchQuery.value.length < 1) {
      filteredTickers.value = [];
      showDropdown.value = false;
      return;
    }
    
    try {
      isLoading.value = true;
      showDropdown.value = true;
      
      // Use the search endpoint instead of filtering locally
      const response = await axios.get('/api/stock-analysis/tickers/search', {
        params: {
          query: searchQuery.value,
          limit: 50,
          exact_match: false
        }
      });
      
      filteredTickers.value = response.data.tickers || [];
      isLoading.value = false;
    } catch (error) {
      console.error('Error searching tickers:', error);
      filteredTickers.value = [];
      isLoading.value = false;
    }
  }, 300); // 300ms debounce
};

// Handle search input with debounce
const handleSearchInput = () => {
  debouncedSearch();
};

const selectStock = (symbol) => {
  emit('update:selectedStock', symbol);
  searchQuery.value = symbol;
  showDropdown.value = false;
};

const selectSection = (sectionId) => {
  emit('update:activeSection', sectionId);
};

// Update date range based on quick selection
const updateDateRange = () => {
  // Validate dates before emitting
  validateDates();
  
  emit('update:dateRange', {
    from: dateFrom.value,
    to: dateTo.value
  });
};

// Validate dates to prevent future dates
const validateDates = () => {
  const today = new Date().toISOString().split('T')[0];
  
  // Check if dates are in the future
  if (dateFrom.value > today) {
    console.log(`Start date ${dateFrom.value} is in the future, using today instead`);
    dateFrom.value = today;
  }
  
  if (dateTo.value > today) {
    console.log(`End date ${dateTo.value} is in the future, using today instead`);
    dateTo.value = today;
  }
  
  // Check if dates are in wrong order
  if (dateFrom.value > dateTo.value) {
    console.log(`Start date ${dateFrom.value} is after end date ${dateTo.value}, swapping`);
    [dateFrom.value, dateTo.value] = [dateTo.value, dateFrom.value];
  }
};

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
  if (!event.target.closest('.stock-select')) {
    showDropdown.value = false;
  }
};

// Load ticker count on component mount
onMounted(() => {
  fetchTickerCount();
  document.addEventListener('click', handleClickOutside);
  
  // If a stock is already selected, set the search query
  if (props.selectedStock) {
    searchQuery.value = props.selectedStock;
  }
  
  // Set default date range (1 year)
  setDefaultDateRange();
  
  // If the active section is already 'hurst', ensure minimum date range
  if (props.activeSection === 'hurst') {
    ensureMinimumDateRangeForHurst();
  }
});

// Watch for changes in the search query
watch(searchQuery, (newValue, oldValue) => {
  if (newValue !== oldValue) {
    debouncedSearch();
  }
});
</script>

<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h5>Stock Analysis</h5>
    </div>
    
    <!-- Stock Search/Select -->
    <div class="stock-select">
      <label for="stockSearch">
        Select Stock: 
        <span class="ticker-count" v-if="tickerCount">({{ tickerCount }} tickers available)</span>
      </label>
      <div class="search-wrapper">
        <input 
          id="stockSearch"
          type="text"
          v-model="searchQuery"
          @input="handleSearchInput"
          placeholder="Search for a ticker..."
          class="form-control"
          autocomplete="off"
          @focus="() => { if (!searchQuery) searchQuery = 'TSLA'; }"
        />
        <i class="uil uil-search search-icon" v-if="!isLoading"></i>
        <i class="uil uil-spinner-alt spin search-icon" v-else></i>
      </div>
      
      <!-- Dropdown for search results -->
      <div 
        v-if="showDropdown && filteredTickers.length > 0" 
        class="dropdown-list"
      >
        <div class="dropdown-header" v-if="filteredTickers.length > 0">
          {{ filteredTickers.length }} result{{ filteredTickers.length !== 1 ? 's' : '' }}
        </div>
        <div 
          v-for="ticker in filteredTickers" 
          :key="ticker"
          class="dropdown-item"
          :class="{ 'active': selectedStock === ticker }"
          @click="selectStock(ticker)"
        >
          <span class="symbol">{{ ticker }}</span>
        </div>
      </div>
      
      <div v-if="searchQuery && showDropdown && filteredTickers.length === 0" class="no-results">
        <span v-if="isLoading">Searching...</span>
        <span v-else>No tickers found</span>
      </div>
    </div>
    
    <!-- Date Range Inputs -->
    <div class="date-range">
      <label>Date Range:</label>
      
      <!-- Quick Date Range Selectors -->
      <div class="quick-ranges">
        <button 
          v-for="range in quickDateRanges" 
          :key="range.label"
          @click="setQuickDateRange(range)"
          class="quick-range-btn"
        >
          {{ range.label }}
        </button>
      </div>
      
      <div class="date-inputs">
        <div class="date-input-group">
          <span class="date-label">From:</span>
          <input 
            type="date" 
            id="dateFrom" 
            v-model="dateFrom" 
            class="form-control date-input"
            :max="today"
            @change="updateDateRange"
          />
        </div>
        <div class="date-input-group">
          <span class="date-label">To:</span>
          <input 
            type="date" 
            id="dateTo" 
            v-model="dateTo" 
            class="form-control date-input"
            :max="today"
            @change="updateDateRange"
          />
        </div>
      </div>
    </div>

    <!-- Analysis Options -->
    <div class="options-list">
      <div 
        v-for="option in analysisOptions" 
        :key="option.id"
        class="option-item"
        :class="{ 'active': activeSection === option.id }"
        @click="selectSection(option.id)"
      >
        <i :class="'uil ' + option.icon"></i>
        <span>{{ option.label }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sidebar {
  width: 250px;
  background-color: var(--black-bg-5);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  height: 100%;
}

.sidebar-header h5 {
  margin: 0;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--white-87);
}

.stock-select {
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
}

.stock-select label {
  display: block;
  margin-bottom: 0;
  color: var(--white-60);
  font-size: var(--font-size-secondary);
}

.ticker-count {
  font-size: 0.8rem;
  opacity: 0.7;
  margin-left: 4px;
}

.search-wrapper {
  position: relative;
}

.search-icon {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--white-60);
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: translateY(-50%) rotate(0deg); }
  to { transform: translateY(-50%) rotate(360deg); }
}

.form-control {
  width: 100%;
  padding: 8px;
  background-color: var(--black-bg-7);
  color: var(--white-87);
  border: 1px solid var(--white-38);
  border-radius: 4px;
  font-size: 0.9rem;
}

.dropdown-list {
  position: absolute;
  top: 100%;
  left: 0;
  width: 100%;
  max-height: 200px;
  overflow-y: auto;
  background-color: var(--black-bg-7);
  border: 1px solid var(--white-38);
  border-radius: 4px;
  z-index: 10;
  margin-top: 2px;
}

.dropdown-header {
  padding: 6px 10px;
  font-size: 0.8rem;
  color: var(--white-60);
  background-color: rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.dropdown-item {
  padding: 8px 10px;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.dropdown-item.active {
  background-color: var(--blue-color);
  color: white;
}

.symbol {
  font-weight: bold;
  font-size: 0.9rem;
}

.loading-more {
  padding: 8px 10px;
  text-align: center;
  font-size: 0.8rem;
  color: var(--white-60);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.no-results {
  padding: 15px 10px;
  text-align: center;
  color: var(--white-60);
  font-style: italic;
  font-size: 0.9rem;
}

.date-range {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.date-range label {
  display: block;
  margin-bottom: 0;
  color: var(--white-60);
  font-size: var(--font-size-secondary);
}

.quick-ranges {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 8px;
}

.quick-range-btn {
  padding: 4px 8px;
  background-color: var(--black-bg-7);
  color: var(--white-87);
  border: 1px solid var(--white-38);
  border-radius: 4px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-range-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.quick-range-btn:active {
  background-color: var(--blue-color);
  color: white;
}

.date-inputs {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.date-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-label {
  width: 45px;
  font-size: 0.85rem;
  color: var(--white-60);
}

.date-input {
  flex: 1;
  padding: 6px 8px;
  font-size: 0.85rem;
}

.options-list {
  display: flex;
  flex-direction: column;
  margin-top: 10px;
}

.option-item {
  display: flex;
  align-items: center;
  padding: 10px;
  cursor: pointer;
  border-radius: 4px;
  color: var(--white-87);
  margin-bottom: 5px;
}

.option-item i {
  margin-right: 10px;
  width: 20px;
  text-align: center;
}

.option-item:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.option-item.active {
  background-color: var(--blue-color);
  color: #fff;
}
</style>
