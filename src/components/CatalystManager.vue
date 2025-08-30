<template>
  <div class="catalyst-manager">
    <div class="card">
      <div class="card-header">
        <h4 class="card-title">Market Catalysts & Drivers</h4>
        <div v-if="error" class="error-tag">{{ error }}</div>
        <div class="header-actions">
          <button class="btn btn-secondary" @click="handleRefresh" :disabled="loading">
            <i class="fa fa-sync-alt"></i>
            Refresh
          </button>
          <button class="btn btn-primary" @click="showModal()">
            <i class="fa fa-plus"></i>
            Add Catalyst
          </button>
        </div>
      </div>

      <div v-if="loading && catalysts.length === 0" class="loading-container">
        <div class="spinner"></div>
        <p class="loading-text">Loading market catalysts...</p>
      </div>
      <div v-else class="card-body">
        <table v-if="catalysts.length > 0" class="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Key Information</th>
              <th>Market Theme</th>
              <th>Technical Position</th>
              <th>Related Symbols</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(catalyst, index) in catalysts" :key="`${catalyst.keyFact}-${index}`">
              <td>{{ formatDate(catalyst.date) }}</td>
              <td>
                <div class="key-fact">
                  <strong class="truncate">{{ catalyst.keyFact }}</strong>
                  <div class="tags-container">
                    <span class="tag" :class="`importance-${catalyst.importance}`">
                      {{ catalyst.importance.toUpperCase() }}
                    </span>
                    <span class="tag" :class="`expectation-${catalyst.actualVsExpectation}`">
                      {{ getExpectationText(catalyst.actualVsExpectation) }}
                    </span>
                  </div>
                </div>
              </td>
              <td class="truncate">{{ catalyst.currentMarketTheme }}</td>
              <td>
                <span class="tag" :class="`tech-${catalyst.technicalPosition}`">
                  {{ getPositionText(catalyst.technicalPosition) }}
                </span>
              </td>
              <td>
                <div class="symbols-container">
                  <span 
                    v-for="symbol in catalyst.relatedSymbols" 
                    :key="symbol" 
                    class="symbol-tag"
                  >
                    {{ symbol }}
                  </span>
                </div>
              </td>
              <td>
                <div class="actions-container">
                  <button class="btn-text" @click="showModal(catalyst, index)">
                    Edit
                  </button>
                  <button class="btn-text danger" @click="handleDelete(index)">
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-container">
          <p>No market catalysts added yet</p>
          <button class="btn btn-primary" @click="showModal()">
            Add Your First Catalyst
          </button>
        </div>
      </div>
    </div>

    <!-- Catalyst Checklist Modal -->
    <catalyst-checklist
      :open="isModalVisible"
      :initial-data="editingCatalyst.value"
      :on-save="handleSave"
      :on-close="handleCancel"
    />

    <!-- News Template Guide -->
    <div class="card news-template-guide">
      <div class="card-header">
        <i class="fa fa-info-circle"></i>
        <span>Market News Types and Typical Reactions</span>
      </div>
      <div class="card-body">
        <p>
          This guide shows common types of market news and their typical market reactions.
          Understanding these patterns can help when adding and interpreting market catalysts.
        </p>
        
        <div class="collapse-section">
          <div class="collapse-header" :class="{ 'active': !collapsedSections.news }" @click="toggleCollapse('news')">
            <strong>Part 1: Different News Types and Typical Market Reactions</strong>
            <i :class="collapsedSections.news ? 'uil uil-angle-down' : 'uil uil-angle-up'" class="collapse-icon"></i>
          </div>
          <div class="collapse-content" v-show="!collapsedSections.news">
            <!-- Header Row -->
            <div class="guide-row header">
              <div class="col-news-type">News Type</div>
              <div class="col-reaction">Initial Reaction</div>
              <div class="col-reaction">Main Market Reaction</div>
              <div class="col-reaction">Market Trend After News</div>
              <div class="col-notes">Notes</div>
            </div>
            
            <!-- Breaking News Row -->
            <div class="guide-row">
              <div class="col-news-type">
                <strong>Breaking News</strong><br/>
                <span class="text-secondary">(earnings, major partnerships)</span>
              </div>
              <div class="col-reaction">Rapid price movement</div>
              <div class="col-reaction">Volume spike, volatility increase</div>
              <div class="col-reaction">Leading indicator, often gap movement</div>
              <div class="col-notes"></div>
            </div>
            
            <!-- Economic Data Row -->
            <div class="guide-row">
              <div class="col-news-type">
                <strong>Economic Data Surprises</strong><br/>
                <span class="text-secondary">(better/worse than expected)</span>
              </div>
              <div class="col-reaction">Substantial volatility</div>
              <div class="col-reaction">Repositioning by major players</div>
              <div class="col-reaction">Potential trend reset</div>
              <div class="col-notes"></div>
            </div>
            
            <!-- Surprise Earnings Row -->
            <div class="guide-row">
              <div class="col-news-type">
                <strong>Surprise Earnings</strong><br/>
                <span class="text-secondary">(beats/misses)</span>
              </div>
              <div class="col-reaction">Rapid moves, emotional trading</div>
              <div class="col-reaction">Setup for continuation or reversal</div>
              <div class="col-reaction">Short-term volatility then trend</div>
              <div class="col-notes"></div>
            </div>
            
            <!-- Policy/Regulatory Row -->
            <div class="guide-row">
              <div class="col-news-type">
                <strong>Policy/Regulatory News</strong><br/>
                <span class="text-secondary">(gov't decisions, tax changes)</span>
              </div>
              <div class="col-reaction">Extended volatility</div>
              <div class="col-reaction">Sector-wide repricing</div>
              <div class="col-reaction">Can shift market thesis</div>
              <div class="col-notes"></div>
            </div>
            
            <!-- Macro Economic Row -->
            <div class="guide-row">
              <div class="col-news-type">
                <strong>Macro Economic Reports</strong><br/>
                <span class="text-secondary">(inflation, jobs)</span>
              </div>
              <div class="col-reaction">Cautious trading</div>
              <div class="col-reaction">Main indicators move lower</div>
              <div class="col-reaction">Leading companies react first</div>
              <div class="col-notes"></div>
            </div>
          </div>
        </div>
        
        <div class="collapse-section">
          <div class="collapse-header" :class="{ 'active': !collapsedSections.perception }" @click="toggleCollapse('perception')">
            <strong>Part 2: Why Your Market Understanding Differs from Others</strong>
            <i :class="collapsedSections.perception ? 'uil uil-angle-down' : 'uil uil-angle-up'" class="collapse-icon"></i>
          </div>
          <div class="collapse-content" v-show="!collapsedSections.perception">
            <!-- Header Row -->
            <div class="guide-row header">
              <div class="col-perception">Your Perception</div>
              <div class="col-perception">Market's Perception</div>
              <div class="col-discrepancy">Key Discrepancy</div>
            </div>
            
            <!-- Headline Focus Row -->
            <div class="guide-row">
              <div class="col-perception">
                <strong>News headline focus</strong>
              </div>
              <div class="col-perception">
                <strong>News follow-through structure</strong>
              </div>
              <div class="col-discrepancy">
                <span class="text-secondary">Your "breaking news" vs market's "expected move"</span>
              </div>
            </div>
            
            <!-- Profit Growth Row -->
            <div class="guide-row">
              <div class="col-perception">
                <strong>Profit growth focus</strong>
              </div>
              <div class="col-perception">
                <strong>Growth reliability patterns</strong>
              </div>
              <div class="col-discrepancy">
                <span class="text-secondary">You see current numbers, markets see future patterns</span>
              </div>
            </div>
            
            <!-- Partnership Row -->
            <div class="guide-row">
              <div class="col-perception">
                <strong>Partnership announcements</strong>
              </div>
              <div class="col-perception">
                <strong>Partnership details and impact</strong>
              </div>
              <div class="col-discrepancy">
                <span class="text-secondary">News exists but value is unclear</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="key-insight">
          <p class="italic">
            Key insight: Markets don't react to news; they react to the <strong>interpretation</strong> of news.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue';
import axios from 'axios';
import CatalystChecklist from './CatalystChecklist.vue';

export default {
  name: 'CatalystManager',
  components: {
    CatalystChecklist
  },
  props: {
    catalysts: {
      type: Array,
      default: () => []
    },
    onCatalystsChanged: {
      type: Function,
      default: null
    }
  },
  setup(props) {
    // State
    const catalysts = ref(props.catalysts || []);
    const isModalVisible = ref(false);
    const editingCatalyst = ref({
      date: new Date().toISOString().split('T')[0],
      keyFact: '',
      importance: 'medium',
      actualVsExpectation: 'met',
      currentMarketTheme: '',
      technicalPosition: 'neutral',
      relatedSymbols: [],
      marketPreAnnouncement: '',
      howCatalystAffects: '',
      keyLevels: '',
      notes: ''
    });
    const editingIndex = ref(-1);
    const loading = ref(false);
    const error = ref(null);
    const symbolsInput = ref('');
    
    // Change from a single value to a map of section IDs to boolean values
    const collapsedSections = reactive({
      news: false,      // false means expanded (visible)
      perception: true  // true means collapsed (hidden)
    });

    // Load catalysts from the API when component mounts
    onMounted(async () => {
      if (props.catalysts && props.catalysts.length > 0) {
        catalysts.value = props.catalysts;
      } else {
        await fetchCatalysts();
      }
    });
    
    const fetchCatalysts = async () => {
      loading.value = true;
      try {
        const response = await axios.get('/backend/api/catalysts');
        if (response.data && Array.isArray(response.data)) {
          catalysts.value = response.data;
          
          // Also save to localStorage as a backup
          try {
            localStorage.setItem('marketCatalysts', JSON.stringify(response.data));
          } catch (storageError) {
            console.error('Error saving catalysts to local storage:', storageError);
          }
        }
      } catch (apiError) {
        console.error('Error fetching catalysts from API:', apiError);
        error.value = 'Failed to load market catalysts. Using local data if available.';
        
        // Fallback to localStorage if API fails
        try {
          const storedCatalysts = localStorage.getItem('marketCatalysts');
          if (storedCatalysts) {
            catalysts.value = JSON.parse(storedCatalysts);
          }
        } catch (storageError) {
          console.error('Error loading catalysts from local storage:', storageError);
        }
      } finally {
        loading.value = false;
      }
    };

    // Watch for changes and notify parent
    const notifyParent = () => {
      if (props.onCatalystsChanged) {
        props.onCatalystsChanged(catalysts.value);
      }
      
      // Save to local storage as a backup
      try {
        localStorage.setItem('marketCatalysts', JSON.stringify(catalysts.value));
      } catch (error) {
        console.error('Error saving catalysts to local storage:', error);
      }
    };

    const showModal = (catalyst = null, index = -1) => {
      if (catalyst) {
        editingCatalyst.value = { ...catalyst };
        symbolsInput.value = catalyst.relatedSymbols ? catalyst.relatedSymbols.join(', ') : '';
        editingIndex.value = index;
      } else {
        editingCatalyst.value = {
          date: new Date().toISOString().split('T')[0],
          keyFact: '',
          importance: 'medium',
          actualVsExpectation: 'met',
          currentMarketTheme: '',
          technicalPosition: 'neutral',
          relatedSymbols: [],
          marketPreAnnouncement: '',
          howCatalystAffects: '',
          keyLevels: '',
          notes: ''
        };
        symbolsInput.value = '';
        editingIndex.value = -1;
      }
      isModalVisible.value = true;
    };

    const handleCancel = () => {
      isModalVisible.value = false;
    };

    const handleSave = async (formData) => {
      loading.value = true;
      try {
        if (editingIndex.value >= 0) {
          // Update existing catalyst via API
          await axios.put(`/backend/api/catalysts/${editingCatalyst.value._id || editingCatalyst.value.id}`, formData);
          const updatedList = [...catalysts.value];
          updatedList[editingIndex.value] = formData;
          catalysts.value = updatedList;
          console.log('Catalyst updated successfully');
        } else {
          // Add new catalyst via API
          const response = await axios.post('/backend/api/catalysts', formData);
          if (response.data) {
            catalysts.value = [...catalysts.value, response.data];
            console.log('New catalyst added');
          } else {
            catalysts.value = [...catalysts.value, formData];
          }
        }
      } catch (apiError) {
        console.error('Error saving catalyst:', apiError);
        error.value = 'Failed to save catalyst. Changes saved locally only.';
        
        // Fallback to local-only update
        const newCatalysts = [...catalysts.value];
        if (editingIndex.value >= 0) {
          newCatalysts[editingIndex.value] = formData;
        } else {
          newCatalysts.push(formData);
        }
        catalysts.value = newCatalysts;
      } finally {
        loading.value = false;
        isModalVisible.value = false;
        notifyParent();
      }
    };

    const handleDelete = async (index) => {
      if (!confirm('Are you sure you want to delete this catalyst? This action cannot be undone.')) {
        return;
      }
      
      loading.value = true;
      try {
        const catalyst = catalysts.value[index];
        const id = catalyst._id || catalyst.id;
        
        // Delete via API
        await axios.delete(`/backend/api/catalysts/${id}`);
        catalysts.value = catalysts.value.filter((_, i) => i !== index);
        console.log('Catalyst deleted');
      } catch (apiError) {
        console.error('Error deleting catalyst:', apiError);
        error.value = 'Failed to delete from server. Removed locally only.';
        
        // Fallback to local-only delete
        catalysts.value = catalysts.value.filter((_, i) => i !== index);
      } finally {
        loading.value = false;
        notifyParent();
      }
    };

    const handleRefresh = async () => {
      await fetchCatalysts();
      notifyParent();
    };

    const toggleCollapse = (section) => {
      // Toggle just the specified section
      collapsedSections[section] = !collapsedSections[section];
    };

    // Format utilities
    const formatDate = (dateString) => {
      if (!dateString) return 'N/A';
      const date = new Date(dateString);
      return new Intl.DateTimeFormat('en-US', { 
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      }).format(date);
    };
    
    const getExpectationText = (result) => {
      switch (result) {
        case 'exceeded':
          return 'Exceeded';
        case 'met':
          return 'Met';
        case 'missed':
          return 'Missed';
        default:
          return 'Unknown';
      }
    };
    
    const getPositionText = (position) => {
      const positionMap = {
        'overbought': 'Overbought',
        'neutral': 'Neutral',
        'oversold': 'Oversold',
        'keySupport': 'Key Support',
        'keyResistance': 'Key Resistance'
      };
      
      return positionMap[position] || position;
    };

    return {
      catalysts,
      isModalVisible,
      editingCatalyst,
      editingIndex,
      loading,
      error,
      symbolsInput,
      collapsedSections,
      showModal,
      handleCancel,
      handleSave,
      handleDelete,
      handleRefresh,
      formatDate,
      getExpectationText,
      getPositionText,
      toggleCollapse
    };
  }
};
</script>

<style scoped>
.catalyst-manager {
  display: flex;
  flex-direction: column;
  gap: 20px;
  color: #e0e0e0;
}

.card {
  background-color: #1e1e1e;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.card-header {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #3a3a3a;
  color: #ffffff;
}

.card-title {
  margin: 0;
  font-size: 18px;
  color: #ffffff;
}

.card-body {
  padding: 20px;
  color: #e0e0e0;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.error-tag {
  display: inline-block;
  background-color: rgba(244, 67, 54, 0.2);
  color: #f44336;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: none;
  transition: all 0.2s;
}

.btn i {
  font-size: 14px;
}

.btn-primary {
  background-color: #4a6cf7;
  color: white;
}

.btn-primary:hover {
  background-color: #3a5cd8;
}

.btn-secondary {
  background-color: #5c636a;
  color: white;
}

.btn-secondary:hover {
  background-color: #4d545a;
}

.btn-text {
  background: none;
  border: none;
  color: #4a6cf7;
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 3px;
  transition: all 0.2s;
}

.btn-text:hover {
  background-color: rgba(74, 108, 247, 0.1);
}

.btn-text.danger {
  color: #f44336;
}

.btn-text.danger:hover {
  background-color: rgba(244, 67, 54, 0.1);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  color: #e0e0e0;
}

.data-table th {
  text-align: left;
  padding: 12px 16px;
  background-color: #2a2a2a;
  border-bottom: 1px solid #3a3a3a;
  font-weight: 500;
}

.data-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #3a3a3a;
}

.data-table tr:hover {
  background-color: #2a2a2a;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #5c636a;
  border-top-color: #4a6cf7;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  color: #a0a0a0;
}

.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  color: #a0a0a0;
}

.empty-image {
  width: 64px;
  height: 64px;
  background-color: #2a2a2a;
  border-radius: 50%;
  margin-bottom: 16px;
}

.key-fact {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tags-container {
  display: flex;
  gap: 6px;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.importance-high {
  background-color: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.importance-medium {
  background-color: rgba(255, 152, 0, 0.2);
  color: #ff9800;
}

.importance-low {
  background-color: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.expectation-exceeded {
  background-color: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.expectation-met {
  background-color: rgba(33, 150, 243, 0.2);
  color: #2196f3;
}

.expectation-missed {
  background-color: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.tech-overbought {
  background-color: rgba(255, 152, 0, 0.2);
  color: #ff9800;
}

.tech-neutral {
  background-color: rgba(158, 158, 158, 0.2);
  color: #9e9e9e;
}

.tech-oversold {
  background-color: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.tech-keySupport {
  background-color: rgba(33, 150, 243, 0.2);
  color: #2196f3;
}

.tech-keyResistance {
  background-color: rgba(156, 39, 176, 0.2);
  color: #9c27b0;
}

.truncate {
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

.symbols-container {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.symbol-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  background-color: rgba(158, 158, 158, 0.2);
  color: #e0e0e0;
}

.actions-container {
  display: flex;
  gap: 10px;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-container {
  background-color: #1e1e1e;
  border-radius: 4px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.modal-header {
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #3a3a3a;
}

.modal-header h3 {
  margin: 0;
  color: #e0e0e0;
}

.close-btn {
  background: none;
  border: none;
  color: #a0a0a0;
  font-size: 24px;
  cursor: pointer;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  padding: 16px 20px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid #3a3a3a;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #ffffff;
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #3a3a3a;
  border-radius: 4px;
  background-color: #2a2a2a;
  color: #ffffff;
  font-size: 14px;
}

textarea.form-control {
  resize: vertical;
}

/* News Template Guide Styles */
.news-template-guide {
  margin-top: 20px;
}

.collapse-section {
  margin-bottom: 16px;
  border: 1px solid #3a3a3a;
  border-radius: 4px;
  overflow: hidden;
}

.collapse-header {
  padding: 12px 16px;
  background-color: #2a2a2a;
  cursor: pointer;
  user-select: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.collapse-header.active {
  border-bottom: 1px solid #3a3a3a;
}

.collapse-icon {
  font-size: 18px;
  color: #a0a0a0;
  transition: transform 0.2s;
}

.collapse-header.active .collapse-icon {
  color: #4a6cf7;
}

.collapse-content {
  padding: 16px;
}

.guide-row {
  display: flex;
  padding: 12px 8px;
  border-bottom: 1px solid #3a3a3a;
}

.guide-row.header {
  font-weight: bold;
  background-color: #2a2a2a;
  border-radius: 2px;
  margin-bottom: 10px;
}

.col-news-type {
  width: 25%;
}

.col-reaction {
  width: 25%;
}

.col-notes {
  width: 25%;
}

.col-perception {
  width: 30%;
}

.col-discrepancy {
  width: 40%;
}

.text-secondary {
  color: #b0b0b0;
  font-size: 0.9em;
}

.key-insight {
  margin-top: 16px;
  padding: 12px 16px;
  border-left: 4px solid #3a3a3a;
  background-color: #2a2a2a;
}

.italic {
  font-style: italic;
  text-align: center;
  margin: 0;
}

@media (max-width: 768px) {
  .guide-row {
    flex-direction: column;
    gap: 8px;
  }
  
  .guide-row.header {
    display: none;
  }
  
  .col-news-type,
  .col-reaction,
  .col-notes,
  .col-perception,
  .col-discrepancy {
    width: 100%;
  }
}
</style>