<template>
  <div class="relevant-catalysts-container">
    <!-- Search box -->
    <div class="search-container">
      <a-input-search
        v-model:value="searchText"
        placeholder="Search catalysts..."
        class="dark-input"
        style="width: 100%"
      />
    </div>
    
    <!-- Recent catalysts section -->
    <div class="recent-catalysts-section">
      <h4 class="dark-text">Recent Market Catalysts:</h4>
      
      <!-- Show loading indicator when loading -->
      <div v-if="loading" class="loading-container">
        <a-spin />
      </div>
      
      <!-- Show catalysts when available -->
      <div v-else-if="displayCatalysts.length > 0">
        <div v-for="(catalyst, index) in displayCatalysts" :key="index" class="catalyst-item dark-card">
          <div class="catalyst-date dark-text-secondary">
            {{ formatDate(catalyst.date) }}
          </div>
          
          <div class="catalyst-content dark-text">
            {{ catalyst.keyFact }}
          </div>
          
          <div class="catalyst-tags">
            <a-tag :color="getExpectationColor(catalyst.actualVsExpectation)">
              {{ getExpectationText(catalyst.actualVsExpectation) }}
            </a-tag>
            
            <a-tag v-if="catalyst.currentMarketTheme" color="blue">
              {{ catalyst.currentMarketTheme }}
            </a-tag>
          </div>
        </div>
      </div>
      
      <!-- Show empty state when no catalysts -->
      <div v-else class="empty-state">
        <a-empty description="No catalysts found for this symbol" class="dark-empty" />
      </div>
    </div>
  </div>
</template>

<script>
import { defineComponent, ref, watch, computed, onMounted } from 'vue';
import { Input, Empty, Tag, Spin } from 'ant-design-vue';
import dayjs from 'dayjs';

export default defineComponent({
  name: 'RelevantCatalysts',
  components: {
    AInputSearch: Input.Search,
    AEmpty: Empty,
    ATag: Tag,
    ASpin: Spin
  },
  props: {
    symbol: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const catalysts = ref([]);
    const loading = ref(true);
    const searchText = ref('');
    
    // Filter catalysts based on search text and symbol
    const displayCatalysts = computed(() => {
      // First check if there are any catalysts specifically for this symbol
      const symbolSpecificCatalysts = catalysts.value.filter(c => 
        c.relatedSymbols?.includes(props.symbol) || 
        c.keyFact?.toLowerCase().includes(props.symbol.toLowerCase())
      );

      // If we have symbol-specific catalysts and no search, return them
      if (symbolSpecificCatalysts.length > 0 && !searchText.value) {
        return symbolSpecificCatalysts;
      }
      
      // If we're searching, filter based on search text
      if (searchText.value) {
        const searchLower = searchText.value.toLowerCase();
        return catalysts.value.filter(c => 
          (c.keyFact?.toLowerCase().includes(searchLower) || 
           c.currentMarketTheme?.toLowerCase().includes(searchLower))
        );
      }

      // If no symbol-specific catalysts and no search, return all catalysts
      // This ensures we always show something if available
      return catalysts.value;
    });
    
    // Format date for display
    const formatDate = (dateStr) => {
      if (!dateStr) return '';
      return dayjs(dateStr).format('MMM D, YYYY');
    };
    
    // Get color based on expectation
    const getExpectationColor = (expectation) => {
      if (expectation === 'exceeded') return 'green';
      if (expectation === 'missed') return 'red';
      return 'blue';
    };
    
    // Get text for expectation
    const getExpectationText = (expectation) => {
      if (expectation === 'exceeded') return 'Exceeded Expectations';
      if (expectation === 'missed') return 'Missed Expectations';
      return 'Recession Fear';
    };
    
    // Load catalysts from localStorage
    const loadCatalysts = () => {
      loading.value = true;
      console.log("Loading catalysts for symbol:", props.symbol);
      
      try {
        const storedCatalysts = localStorage.getItem('marketCatalysts');
        if (storedCatalysts) {
          // Parse and sort by date
          const allCatalysts = JSON.parse(storedCatalysts);
          console.log("Found catalysts in localStorage:", allCatalysts);
          
          catalysts.value = [...allCatalysts].sort((a, b) => {
            if (!a.date) return 1;
            if (!b.date) return -1;
            return new Date(b.date).getTime() - new Date(a.date).getTime();
          });
          
          console.log("Sorted catalysts:", catalysts.value);
          console.log("Display catalysts computed:", displayCatalysts.value);
        } else {
          // Create sample data if none exists
          const sampleData = [
            {
              date: new Date().toISOString(),
              keyFact: 'Trade Tensions and Tariff Uncertainty Weigh on Sentiment',
              actualVsExpectation: 'missed',
              currentMarketTheme: 'Recession Fear',
              relatedSymbols: ['SPY', 'AAPL', 'MSFT']
            },
            {
              date: new Date(Date.now() - 86400000).toISOString(),
              keyFact: 'Trump tariffs was illegal. Market thought tariff war is done.',
              actualVsExpectation: 'exceeded',
              currentMarketTheme: 'Tariff trade war',
              relatedSymbols: ['SPY', 'QQQ', 'AAPL']
            }
          ];
          
          catalysts.value = sampleData;
          localStorage.setItem('marketCatalysts', JSON.stringify(sampleData));
          console.log("Created sample catalysts:", sampleData);
        }
      } catch (error) {
        console.error('Error loading catalysts:', error);
        catalysts.value = [];
      } finally {
        loading.value = false;
      }
    };
    
    // Load catalysts on mount and when symbol changes
    onMounted(loadCatalysts);
    
    watch(() => props.symbol, () => {
      loadCatalysts();
    });
    
    return {
      catalysts,
      loading,
      searchText,
      displayCatalysts,
      formatDate,
      getExpectationColor,
      getExpectationText
    };
  }
});
</script>

<style scoped>
.relevant-catalysts-container {
  width: 100%;
}

.search-container {
  margin-bottom: 16px;
}

.recent-catalysts-section h4 {
  margin-bottom: 12px;
  font-size: 14px;
}

.catalyst-item {
  background-color: #262626 !important;
  border: 1px solid #303030;
  padding: 12px;
  margin-bottom: 12px;
  border-radius: 4px;
}

.catalyst-date {
  font-size: 12px;
  margin-bottom: 4px;
}

.catalyst-content {
  margin-bottom: 8px;
  font-size: 14px;
  line-height: 1.5;
}

.catalyst-tags {
  display: flex;
  gap: 8px;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 24px;
}

.empty-state {
  margin-top: 16px;
}

.dark-text {
  color: #e0e0e0 !important;
}

.dark-text-secondary {
  color: #a0a0a0 !important;
}

.dark-input {
  background-color: #262626 !important;
  border-color: #303030 !important;
}

.dark-input :deep(input) {
  background-color: #262626 !important;
  color: #e0e0e0 !important;
}

.dark-input :deep(.ant-input-search-button) {
  background-color: #303030 !important;
  border-color: #303030 !important;
  color: #e0e0e0 !important;
}

.dark-input :deep(::placeholder) {
  color: rgba(224, 224, 224, 0.5) !important;
}

.dark-empty :deep(.ant-empty-description) {
  color: #a0a0a0 !important;
}
</style> 