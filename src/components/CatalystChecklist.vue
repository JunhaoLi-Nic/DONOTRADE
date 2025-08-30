<template>
  <div class="catalyst-checklist">
    <!-- Modal overlay -->
    <div v-if="isOpen" class="modal-overlay" @click="handleModalOutsideClick">
      <div class="modal-container" @click.stop>
        <div class="modal-header">
          <h2 class="modal-title">Market Catalyst Analysis</h2>
          <button class="close-btn" @click="onClose">&times;</button>
        </div>
        
        <div class="modal-body">
          <form @submit.prevent="handleSubmit">
            <div class="form-header">
              <div class="form-header-title">
                <h3>Catalyst Information</h3>
              </div>
              <div class="form-header-date">
                <div class="form-group">
                  <label>Date</label>
                  <input 
                    type="date" 
                    v-model="formData.date" 
                    class="form-control"
                  />
                </div>
              </div>
            </div>

            <!-- 1. Key Information -->
            <div class="form-card">
              <div class="form-card-header">
                <h4>1. Key Information</h4>
              </div>
              <div class="form-card-body">
                <div class="form-group">
                  <label>Key Information/News <span class="required">*</span></label>
                  <textarea 
                    v-model="formData.keyFact" 
                    class="form-control" 
                    rows="2" 
                    placeholder="What is the key fact or news?"
                    required
                  ></textarea>
                </div>
                
                <div class="form-group">
                  <label>Pre-announcement Market Expectation <span class="required">*</span></label>
                  <textarea 
                    v-model="formData.marketPreAnnouncement" 
                    class="form-control" 
                    rows="2" 
                    placeholder="What was the market expecting before this news? (Research required)"
                    required
                  ></textarea>
                </div>
                
                <div class="form-group">
                  <label>Actual vs Expectation <span class="required">*</span></label>
                  <div class="radio-group">
                    <label class="radio-label">
                      <input type="radio" v-model="formData.actualVsExpectation" value="exceeded">
                      Exceeded Expectations
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="formData.actualVsExpectation" value="met">
                      Met Expectations
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="formData.actualVsExpectation" value="missed">
                      Missed Expectations
                    </label>
                  </div>
                </div>
                
                <div class="form-group">
                  <label>Importance Level</label>
                  <div class="radio-group">
                    <label class="radio-label">
                      <input type="radio" v-model="formData.importance" value="low">
                      Low
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="formData.importance" value="medium">
                      Medium
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="formData.importance" value="high">
                      High
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <!-- 2. Market Theme Analysis -->
            <div class="form-card">
              <div class="form-card-header">
                <h4>2. Market Theme Analysis</h4>
              </div>
              <div class="form-card-body">
                <div class="form-group">
                  <label>Current Leading Market Theme <span class="required">*</span></label>
                  <input 
                    type="text" 
                    v-model="formData.currentMarketTheme" 
                    class="form-control" 
                    placeholder="e.g., Rate Hikes, AI Revolution, Recession Fears"
                    required
                  />
                </div>
                
                <div class="form-group">
                  <label>How this information affects the theme <span class="required">*</span></label>
                  <textarea 
                    v-model="formData.howCatalystAffects" 
                    class="form-control" 
                    rows="3" 
                    placeholder="Example: Strong economic data → Reinforces bull case → Higher rate hike probability → Market volatility"
                    required
                  ></textarea>
                </div>
              </div>
            </div>

            <!-- 3. Technical Position -->
            <div class="form-card">
              <div class="form-card-header">
                <h4>3. Technical Position</h4>
              </div>
              <div class="form-card-body">
                <div class="form-group">
                  <label>Current Technical Position</label>
                  <div class="radio-group">
                    <label class="radio-label">
                      <input type="radio" v-model="formData.technicalPosition" value="overbought">
                      Overbought (Extended Rally)
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="formData.technicalPosition" value="neutral">
                      Neutral
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="formData.technicalPosition" value="oversold">
                      Oversold (Extended Decline)
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="formData.technicalPosition" value="keySupport">
                      At Key Support
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="formData.technicalPosition" value="keyResistance">
                      At Key Resistance
                    </label>
                  </div>
                </div>
                
                <div class="form-group">
                  <label>Key Price Levels to Watch</label>
                  <textarea 
                    v-model="formData.keyLevels" 
                    class="form-control" 
                    rows="2" 
                    placeholder="Important support/resistance levels, moving averages, etc."
                  ></textarea>
                </div>
              </div>
            </div>

            <!-- 4. Additional Information -->
            <div class="form-card">
              <div class="form-card-header">
                <h4>4. Additional Information</h4>
              </div>
              <div class="form-card-body">
                <div class="form-group">
                  <label>Related Symbols/ETFs</label>
                  <div class="tags-input-container">
                    <div class="tags-container">
                      <span 
                        v-for="(symbol, index) in formData.relatedSymbols" 
                        :key="index" 
                        class="tag"
                      >
                        {{ symbol }}
                        <span class="tag-remove" @click="removeSymbol(index)">&times;</span>
                      </span>
                    </div>
                    <input 
                      type="text" 
                      v-model="symbolInput" 
                      class="form-control tag-input" 
                      placeholder="Add symbols (press Enter or comma to add)"
                      @keydown="handleSymbolInputKeydown"
                      @blur="addSymbolFromInput"
                    />
                  </div>
                  <div class="symbols-suggestions">
                    <button 
                      type="button" 
                      class="symbol-suggestion" 
                      v-for="suggestion in symbolSuggestions" 
                      :key="suggestion.value"
                      @click="addSymbol(suggestion.value)"
                    >
                      {{ suggestion.label }}
                    </button>
                  </div>
                </div>
                
                <div class="form-group">
                  <label>Additional Notes</label>
                  <textarea 
                    v-model="formData.notes" 
                    class="form-control" 
                    rows="3" 
                    placeholder="Any other relevant information or observations (Has market verify the news yet? Have they priced in already? How is the volume? Do insitutions know about it earilier? )"
                  ></textarea>
                </div>
              </div>
            </div>
            
            <!-- Form Footer Buttons -->
            <div class="form-footer">
              <button type="button" class="btn btn-secondary" @click="onClose">Cancel</button>
              <button type="submit" class="btn btn-primary" :disabled="submitting">
                {{ submitting ? 'Saving...' : 'Save' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, watch, computed } from 'vue';

export default {
  name: 'CatalystChecklist',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    open: {
      type: Boolean,
      default: false
    },
    initialData: {
      type: Object,
      default: () => ({})
    },
    onSave: {
      type: Function,
      required: true
    },
    onClose: {
      type: Function,
      required: true
    }
  },
  setup(props) {
    console.log('CatalystChecklist props:', props);
    
    // Computed property to handle both visible and open props
    const isOpen = computed(() => {
      if (props.visible && !props.open) {
        console.warn('[ant-design-vue: Modal] `visible` will be removed in next major version, please use `open` instead.');
      }
      return props.open || props.visible;
    });
    
    // Form data state
    const formData = reactive({
      keyFact: '',
      marketPreAnnouncement: '',
      marketExpectation: '',
      actualVsExpectation: 'met',
      currentMarketTheme: '',
      howCatalystAffects: '',
      technicalPosition: 'neutral',
      keyLevels: '',
      date: new Date().toISOString().split('T')[0],
      relatedSymbols: [],
      notes: '',
      importance: 'medium'
    });
    
    const submitting = ref(false);
    const symbolInput = ref('');
    
    // Symbol suggestions
    const symbolSuggestions = [
      { value: 'SPY', label: 'SPY (S&P 500)' },
      { value: 'QQQ', label: 'QQQ (Nasdaq)' },
      { value: 'IWM', label: 'IWM (Russell 2000)' },
      { value: 'DIA', label: 'DIA (Dow Jones)' },
      { value: 'XLK', label: 'XLK (Technology)' },
      { value: 'XLF', label: 'XLF (Financials)' },
      { value: 'XLE', label: 'XLE (Energy)' },
      { value: 'XLY', label: 'XLY (Consumer Discretionary)' },
      { value: 'XLP', label: 'XLP (Consumer Staples)' },
      { value: 'XLV', label: 'XLV (Health Care)' },
      { value: 'XLI', label: 'XLI (Industrials)' },
      { value: 'XLB', label: 'XLB (Materials)' },
      { value: 'XLRE', label: 'XLRE (Real Estate)' },
      { value: 'XLU', label: 'XLU (Utilities)' },
      { value: 'XLC', label: 'XLC (Communication Services)' }
    ];
    
    // Reset form when modal becomes visible or gets new initial data
    watch(() => props.visible, (newVisible) => {
      console.log('Visibility changed:', newVisible);
      if (newVisible) {
        resetForm();
      }
    });
    
    watch(() => props.initialData, (newData) => {
      console.log('Initial data changed:', newData);
      if (newData && props.visible) {
        populateForm(newData);
      }
    }, { deep: true });
    
    // Initialize form with initial data if available
    onMounted(() => {
      if (props.initialData && props.visible) {
        populateForm(props.initialData);
      }
    });
    
    const resetForm = () => {
      if (props.initialData) {
        populateForm(props.initialData);
      } else {
        // Reset to defaults
        Object.assign(formData, {
          keyFact: '',
          marketPreAnnouncement: '',
          marketExpectation: '',
          actualVsExpectation: 'met',
          currentMarketTheme: '',
          howCatalystAffects: '',
          technicalPosition: 'neutral',
          keyLevels: '',
          date: new Date().toISOString().split('T')[0],
          relatedSymbols: [],
          notes: '',
          importance: 'medium'
        });
        symbolInput.value = '';
      }
    };
    
    const populateForm = (data) => {
      // Populate form with provided data
      Object.keys(formData).forEach(key => {
        if (data[key] !== undefined) {
          formData[key] = data[key];
        }
      });
      
      // Handle special case for date
      if (data.date) {
        formData.date = data.date;
      }
      
      // Handle array for related symbols
      if (data.relatedSymbols) {
        formData.relatedSymbols = [...data.relatedSymbols];
      }
    };
    
    const handleSubmit = () => {
      submitting.value = true;
      try {
        // Create a copy of the form data
        const formattedData = { ...formData };
        
        // Ensure date is formatted correctly
        if (formattedData.date) {
          // Make sure it's in YYYY-MM-DD format
          const date = new Date(formattedData.date);
          formattedData.date = date.toISOString().split('T')[0];
        } else {
          formattedData.date = new Date().toISOString().split('T')[0];
        }
        
        // Call the save handler
        props.onSave(formattedData);
      } catch (error) {
        console.error('Form submission error:', error);
      } finally {
        submitting.value = false;
      }
    };
    
    // Prevent modal close when clicking inside
    const handleModalOutsideClick = (event) => {
      // Close modal only if clicking on the overlay
      if (event.target === event.currentTarget) {
        props.onClose();
      }
    };
    
    // Symbol tag input handling
    const addSymbol = (symbol) => {
      if (symbol && !formData.relatedSymbols.includes(symbol)) {
        formData.relatedSymbols.push(symbol);
      }
    };
    
    const removeSymbol = (index) => {
      formData.relatedSymbols.splice(index, 1);
    };
    
    const handleSymbolInputKeydown = (event) => {
      // Add on Enter or comma
      if (event.key === 'Enter' || event.key === ',') {
        event.preventDefault();
        addSymbolFromInput();
      }
    };
    
    const addSymbolFromInput = () => {
      const symbols = symbolInput.value.split(',');
      
      symbols.forEach(symbol => {
        const trimmed = symbol.trim();
        if (trimmed && !formData.relatedSymbols.includes(trimmed)) {
          formData.relatedSymbols.push(trimmed);
        }
      });
      
      symbolInput.value = '';
    };
    
    return {
      isOpen,
      formData,
      submitting,
      symbolInput,
      symbolSuggestions,
      handleSubmit,
      handleModalOutsideClick,
      addSymbol,
      removeSymbol,
      handleSymbolInputKeydown,
      addSymbolFromInput
    };
  }
};
</script>

<style scoped>
.catalyst-checklist {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

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
  max-width: 800px;
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

.modal-title {
  margin: 0;
  color: #e0e0e0;
  font-size: 18px;
  font-weight: 500;
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

.form-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}

.form-header-title {
  flex: 3;
}

.form-header-date {
  flex: 1;
}

.form-header h3 {
  margin: 0;
  color: #e0e0e0;
  font-size: 16px;
  font-weight: 500;
}

.form-card {
  margin-bottom: 16px;
  border: 1px solid #3a3a3a;
  border-radius: 4px;
  overflow: hidden;
}

.form-card-header {
  padding: 12px 16px;
  background-color: #2a2a2a;
}

.form-card-header h4 {
  margin: 0;
  color: #e0e0e0;
  font-size: 14px;
  font-weight: 500;
}

.form-card-body {
  padding: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #e0e0e0;
  font-size: 14px;
}

.required {
  color: #f44336;
}

.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #3a3a3a;
  border-radius: 4px;
  background-color: #2a2a2a;
  color: #e0e0e0;
  font-size: 14px;
  box-sizing: border-box;
}

textarea.form-control {
  resize: vertical;
}

.radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.radio-label {
  display: flex;
  align-items: center;
  color: #e0e0e0;
  font-size: 14px;
  cursor: pointer;
}

.radio-label input {
  margin-right: 6px;
}

.tags-input-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 32px;
  padding: 4px;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  background-color: rgba(74, 108, 247, 0.2);
  color: #4a6cf7;
  border-radius: 16px;
  font-size: 12px;
}

.tag-remove {
  margin-left: 6px;
  cursor: pointer;
  font-weight: bold;
}

.tag-input {
  padding: 6px 8px;
  font-size: 14px;
}

.symbols-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.symbol-suggestion {
  background: none;
  border: 1px solid #4a6cf7;
  color: #4a6cf7;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.symbol-suggestion:hover {
  background-color: rgba(74, 108, 247, 0.1);
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background-color: #4a6cf7;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #3a5cd8;
}

.btn-primary:disabled {
  background-color: #3a5cd8;
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: #5c636a;
  color: white;
}

.btn-secondary:hover {
  background-color: #4d545a;
}

@media (max-width: 768px) {
  .form-header {
    flex-direction: column;
    gap: 16px;
  }
  
  .radio-group {
    flex-direction: column;
    gap: 8px;
  }
}
</style> 