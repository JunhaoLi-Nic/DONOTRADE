<script setup>
import { ref } from 'vue';

const props = defineProps({
  playbook: {
    type: Object,
    required: true
  }
});

// Mock missed trades data
const missedTrades = ref([
  {
    id: 1,
    date: '01/05/2023',
    symbol: 'AAPL',
    setup: 'Morning Top Reversal',
    reason: 'Missed entry due to hesitation',
    potentialPnL: 1250.75
  },
  {
    id: 2,
    date: '01/12/2023',
    symbol: 'TSLA',
    setup: 'Morning Top Reversal',
    reason: 'Missed due to meeting',
    potentialPnL: 3450.25
  }
]);

// Form for adding new missed trades
const showAddForm = ref(false);
const newMissedTrade = ref({
  symbol: '',
  date: new Date().toLocaleDateString('en-US'),
  setup: '',
  reason: '',
  potentialPnL: null
});

function toggleAddForm() {
  showAddForm.value = !showAddForm.value;
  
  // Reset form when opening
  if (showAddForm.value) {
    newMissedTrade.value = {
      symbol: '',
      date: new Date().toLocaleDateString('en-US'),
      setup: '',
      reason: '',
      potentialPnL: null
    };
  }
}

function addMissedTrade() {
  if (!newMissedTrade.value.symbol || !newMissedTrade.value.reason) {
    return;
  }
  
  missedTrades.value.push({
    id: Date.now(),
    ...newMissedTrade.value
  });
  
  toggleAddForm();
}

function deleteMissedTrade(id) {
  missedTrades.value = missedTrades.value.filter(trade => trade.id !== id);
}

// Format currency
function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(value);
}
</script>

<template>
  <div class="missed-trades-container">
    <!-- Header with add button -->
    <div class="section-header">
      <h3 class="section-title">Missed Trading Opportunities</h3>
      <button class="btn-add" @click="toggleAddForm">
        <i class="uil uil-plus"></i> Add Missed Trade
      </button>
    </div>
    
    <!-- Add form -->
    <div v-if="showAddForm" class="add-form">
      <div class="form-header">
        <h4>Add Missed Trade</h4>
        <button class="btn-close" @click="toggleAddForm">
          <i class="uil uil-times"></i>
        </button>
      </div>
      
      <div class="form-body">
        <div class="form-row">
          <div class="form-group">
            <label for="symbol">Symbol</label>
            <input 
              type="text" 
              id="symbol" 
              v-model="newMissedTrade.symbol" 
              placeholder="e.g. AAPL"
              class="form-control"
            />
          </div>
          
          <div class="form-group">
            <label for="date">Date</label>
            <input 
              type="text" 
              id="date" 
              v-model="newMissedTrade.date" 
              placeholder="MM/DD/YYYY"
              class="form-control"
            />
          </div>
        </div>
        
        <div class="form-group">
          <label for="setup">Setup</label>
          <input 
            type="text" 
            id="setup" 
            v-model="newMissedTrade.setup" 
            placeholder="e.g. Morning Top Reversal"
            class="form-control"
          />
        </div>
        
        <div class="form-group">
          <label for="reason">Reason Missed</label>
          <textarea 
            id="reason" 
            v-model="newMissedTrade.reason" 
            placeholder="Why did you miss this trade?"
            class="form-control"
            rows="3"
          ></textarea>
        </div>
        
        <div class="form-group">
          <label for="potentialPnL">Potential P&L ($)</label>
          <input 
            type="number" 
            id="potentialPnL" 
            v-model="newMissedTrade.potentialPnL" 
            placeholder="0.00"
            class="form-control"
          />
        </div>
      </div>
      
      <div class="form-footer">
        <button class="btn-cancel" @click="toggleAddForm">Cancel</button>
        <button 
          class="btn-primary" 
          @click="addMissedTrade"
          :disabled="!newMissedTrade.symbol || !newMissedTrade.reason"
        >
          Save
        </button>
      </div>
    </div>
    
    <!-- Missed trades list -->
    <div class="trades-list">
      <div v-for="trade in missedTrades" :key="trade.id" class="trade-card">
        <div class="trade-header">
          <div class="trade-symbol">{{ trade.symbol }}</div>
          <div class="trade-date">{{ trade.date }}</div>
        </div>
        
        <div class="trade-body">
          <div class="trade-setup">{{ trade.setup }}</div>
          <div class="trade-reason">{{ trade.reason }}</div>
          <div class="trade-potential">
            Potential P&L: <span class="text-success">{{ formatCurrency(trade.potentialPnL) }}</span>
          </div>
        </div>
        
        <div class="trade-actions">
          <button class="btn-delete" @click="deleteMissedTrade(trade.id)">
            <i class="uil uil-trash-alt"></i>
          </button>
        </div>
      </div>
      
      <div v-if="missedTrades.length === 0" class="no-trades">
        <i class="uil uil-chart"></i>
        <p>No missed trades recorded for this playbook.</p>
        <p class="small">Click "Add Missed Trade" to record opportunities you missed.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.missed-trades-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 500;
  margin: 0;
}

.btn-add {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background-color: #5e72e4;
  color: white;
  border: none;
  border-radius: 0.375rem;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.btn-add:hover {
  background-color: #4a5cd0;
}

.add-form {
  background-color: #252525;
  border-radius: 0.5rem;
  margin-bottom: 1.5rem;
  overflow: hidden;
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #1e1e1e;
  border-bottom: 1px solid #333;
}

.form-header h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 500;
}

.btn-close {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 1.25rem;
  padding: 0;
}

.form-body {
  padding: 1rem;
}

.form-row {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.form-row .form-group {
  flex: 1;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  font-size: 0.9rem;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  background-color: #1e1e1e;
  border: 1px solid #333;
  border-radius: 0.375rem;
  color: #fff;
  font-size: 1rem;
}

.form-control:focus {
  outline: none;
  border-color: #5e72e4;
}

textarea.form-control {
  resize: vertical;
  min-height: 80px;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem;
  background-color: #1e1e1e;
  border-top: 1px solid #333;
}

.btn-cancel {
  background: none;
  border: 1px solid #333;
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  cursor: pointer;
}

.btn-primary {
  background-color: #5e72e4;
  border: none;
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  cursor: pointer;
}

.btn-primary:disabled {
  background-color: #3a4485;
  cursor: not-allowed;
  opacity: 0.7;
}

.trades-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.trade-card {
  background-color: #252525;
  border-radius: 0.5rem;
  overflow: hidden;
  position: relative;
}

.trade-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #1e1e1e;
}

.trade-symbol {
  font-size: 1.25rem;
  font-weight: 600;
}

.trade-date {
  font-size: 0.85rem;
  color: #999;
}

.trade-body {
  padding: 1rem;
}

.trade-setup {
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.trade-reason {
  color: #999;
  margin-bottom: 1rem;
}

.trade-potential {
  font-size: 0.9rem;
}

.text-success {
  color: #2dce89;
  font-weight: 600;
}

.trade-actions {
  position: absolute;
  top: 1rem;
  right: 1rem;
}

.btn-delete {
  background: none;
  border: none;
  color: #f5365c;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.25rem;
  transition: background-color 0.2s;
}

.btn-delete:hover {
  background-color: rgba(245, 54, 92, 0.1);
}

.no-trades {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  background-color: #252525;
  border-radius: 0.5rem;
  color: #666;
  text-align: center;
}

.no-trades i {
  font-size: 2rem;
  margin-bottom: 1rem;
}

.no-trades p {
  margin: 0;
}

.no-trades .small {
  font-size: 0.8rem;
  margin-top: 0.5rem;
}
</style> 