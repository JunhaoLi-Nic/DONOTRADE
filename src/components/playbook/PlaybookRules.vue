<script setup>
import { ref, watch, onMounted } from 'vue';
import axios from 'axios';
import AuthService from '../../services/auth';

const props = defineProps({
  playbook: {
    type: Object,
    required: true
  }
});

// Rules data
const entryRules = ref([
  { id: 1, text: 'Gap Up', condition: 'always' },
  { id: 2, text: 'RVOL above 1.5', condition: 'always' },
  { id: 3, text: 'Hitting Support Level', condition: 'always' }
]);

const exitRules = ref([
  { id: 4, text: 'Up 20%', condition: 'winner' },
  { id: 5, text: 'Seeing stock hit my stop loss', condition: 'loser' }
]);

const marketRules = ref([
  { id: 6, text: 'SPY above VWAP', condition: 'always' }
]);

// UI state
const showAddRuleModal = ref(false);
const ruleType = ref('entry'); // 'entry', 'exit', or 'market'
const newRuleText = ref('');
const newRuleCondition = ref('always');
const saveStatus = ref('');

// Load rules when component mounts
onMounted(async () => {
  console.log('PlaybookRules component mounted with playbook:', props.playbook);
  console.log('Playbook ID:', props.playbook._id || props.playbook.id);
  await loadRulesFromPlaybook();
});

// Save rules when they change
watch([entryRules, exitRules, marketRules], () => {
  saveRulesToPlaybook();
}, { deep: true });

// Load rules from the playbook
async function loadRulesFromPlaybook() {
  try {
    console.log('Playbook prop:', props.playbook);
    
    // Get the playbook ID, checking both _id and id properties
    const playbookId = props.playbook._id || props.playbook.id;
    
    if (playbookId) {
      console.log('Loading rules for playbook ID:', playbookId);
      const headers = AuthService.getAuthHeaders();
      const response = await axios.get(`/api/playbooks/${playbookId}`, { headers });
      
      console.log('Playbook API response:', response.data);
      
      if (response.data && response.data.rules) {
        // Use rules from the backend if available
        entryRules.value = response.data.rules.entry || entryRules.value;
        exitRules.value = response.data.rules.exit || exitRules.value;
        marketRules.value = response.data.rules.market || marketRules.value;
        console.log('Loaded rules from playbook:', response.data.rules);
      } else {
        // If no rules exist on the server yet, save the default ones
        console.log('No rules found in response, saving default rules');
        saveRulesToPlaybook();
      }
    } else {
      console.warn('No playbook ID available, cannot load rules');
    }
  } catch (error) {
    console.error('Error loading rules:', error);
  }
}

// Save rules to the playbook
async function saveRulesToPlaybook() {
  try {
    // Get the playbook ID, checking both _id and id properties
    const playbookId = props.playbook._id || props.playbook.id;
    
    if (playbookId) {
      console.log('Saving rules for playbook ID:', playbookId);
      saveStatus.value = 'Saving...';
      
      const headers = AuthService.getAuthHeaders();
      const rules = {
        entry: entryRules.value,
        exit: exitRules.value,
        market: marketRules.value
      };
      
      console.log('Saving rules:', rules);
      
      await axios.put(`/api/playbooks/${playbookId}`, {
        playbook: props.playbook.playbook,
        rules: rules
      }, { headers });
      
      console.log('Rules saved successfully');
      saveStatus.value = 'Saved';
      setTimeout(() => { saveStatus.value = ''; }, 2000);
    } else {
      console.warn('No playbook ID available, cannot save rules');
      saveStatus.value = 'Error: No playbook ID';
      setTimeout(() => { saveStatus.value = ''; }, 2000);
    }
  } catch (error) {
    console.error('Error saving rules:', error);
    saveStatus.value = 'Error saving';
    setTimeout(() => { saveStatus.value = ''; }, 2000);
  }
}

function openAddRuleModal(type) {
  ruleType.value = type;
  newRuleText.value = '';
  newRuleCondition.value = 'always';
  showAddRuleModal.value = true;
}

function closeAddRuleModal() {
  showAddRuleModal.value = false;
}

function addRule() {
  if (!newRuleText.value.trim()) return;
  
  const rule = {
    id: Date.now(),
    text: newRuleText.value.trim(),
    condition: newRuleCondition.value
  };
  
  if (ruleType.value === 'entry') {
    entryRules.value.push(rule);
  } else if (ruleType.value === 'exit') {
    exitRules.value.push(rule);
  } else if (ruleType.value === 'market') {
    marketRules.value.push(rule);
  }
  
  closeAddRuleModal();
}

function deleteRule(type, ruleId) {
  if (type === 'entry') {
    entryRules.value = entryRules.value.filter(rule => rule.id !== ruleId);
  } else if (type === 'exit') {
    exitRules.value = exitRules.value.filter(rule => rule.id !== ruleId);
  } else if (type === 'market') {
    marketRules.value = marketRules.value.filter(rule => rule.id !== ruleId);
  }
}

function getConditionLabel(condition) {
  switch (condition) {
    case 'always': return 'Always';
    case 'winner': return 'When trade is a winner';
    case 'loser': return 'When trade is a loser';
    case 'breakeven': return 'When trade is break even';
    default: return 'Always';
  }
}
</script>

<template>
  <div class="rules-container">
    <!-- Save status indicator -->
    <div v-if="saveStatus" class="save-status">
      {{ saveStatus }}
    </div>
    
    <!-- Entry Rules -->
    <div class="rules-section">
      <div class="rules-header">
        <h3 class="rules-title">
          <i class="uil uil-arrow-down"></i> Entry Criteria
        </h3>
        <button class="btn-add-rule" @click="openAddRuleModal('entry')">
          <i class="uil uil-plus"></i> Add Rule
        </button>
      </div>
      <div class="rules-list">
        <div v-for="rule in entryRules" :key="rule.id" class="rule-item">
          <div class="rule-content">
            <div class="rule-text">{{ rule.text }}</div>
            <div class="rule-condition">{{ getConditionLabel(rule.condition) }}</div>
          </div>
          <div class="rule-actions">
            <button class="btn-delete" @click="deleteRule('entry', rule.id)">
              <i class="uil uil-trash-alt"></i>
            </button>
          </div>
        </div>
        <div v-if="entryRules.length === 0" class="no-rules">
          No entry rules defined. Click "Add Rule" to create one.
        </div>
      </div>
    </div>
    
    <!-- Exit Rules -->
    <div class="rules-section">
      <div class="rules-header">
        <h3 class="rules-title">
          <i class="uil uil-arrow-up"></i> Exit Criteria
        </h3>
        <button class="btn-add-rule" @click="openAddRuleModal('exit')">
          <i class="uil uil-plus"></i> Add Rule
        </button>
      </div>
      <div class="rules-list">
        <div v-for="rule in exitRules" :key="rule.id" class="rule-item">
          <div class="rule-content">
            <div class="rule-text">{{ rule.text }}</div>
            <div class="rule-condition">{{ getConditionLabel(rule.condition) }}</div>
          </div>
          <div class="rule-actions">
            <button class="btn-delete" @click="deleteRule('exit', rule.id)">
              <i class="uil uil-trash-alt"></i>
            </button>
          </div>
        </div>
        <div v-if="exitRules.length === 0" class="no-rules">
          No exit rules defined. Click "Add Rule" to create one.
        </div>
      </div>
    </div>
    
    <!-- Market Conditions -->
    <div class="rules-section">
      <div class="rules-header">
        <h3 class="rules-title">
          <i class="uil uil-chart-line"></i> Market Conditions
        </h3>
        <button class="btn-add-rule" @click="openAddRuleModal('market')">
          <i class="uil uil-plus"></i> Add Rule
        </button>
      </div>
      <div class="rules-list">
        <div v-for="rule in marketRules" :key="rule.id" class="rule-item">
          <div class="rule-content">
            <div class="rule-text">{{ rule.text }}</div>
            <div class="rule-condition">{{ getConditionLabel(rule.condition) }}</div>
          </div>
          <div class="rule-actions">
            <button class="btn-delete" @click="deleteRule('market', rule.id)">
              <i class="uil uil-trash-alt"></i>
            </button>
          </div>
        </div>
        <div v-if="marketRules.length === 0" class="no-rules">
          No market conditions defined. Click "Add Rule" to create one.
        </div>
      </div>
    </div>
    
    <!-- Add Rule Modal -->
    <div v-if="showAddRuleModal" class="modal-overlay">
      <div class="modal-container">
        <div class="modal-header">
          <h3>Add {{ ruleType === 'entry' ? 'Entry' : ruleType === 'exit' ? 'Exit' : 'Market' }} Rule</h3>
          <button class="btn-close" @click="closeAddRuleModal">
            <i class="uil uil-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label for="rule-text">Rule Description</label>
            <input 
              type="text" 
              id="rule-text" 
              v-model="newRuleText" 
              placeholder="Enter rule description"
              class="form-control"
            />
          </div>
          
          <div class="form-group">
            <label>Show rule only when:</label>
            <div class="radio-group">
              <label class="radio-option">
                <input type="radio" v-model="newRuleCondition" value="always" />
                <span>Always</span>
              </label>
              <label class="radio-option">
                <input type="radio" v-model="newRuleCondition" value="winner" />
                <span>When trade is a winner</span>
              </label>
              <label class="radio-option">
                <input type="radio" v-model="newRuleCondition" value="loser" />
                <span>When trade is a loser</span>
              </label>
              <label class="radio-option">
                <input type="radio" v-model="newRuleCondition" value="breakeven" />
                <span>When trade is break even</span>
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="closeAddRuleModal">Cancel</button>
          <button class="btn-primary" @click="addRule">Add Rule</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rules-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  position: relative;
}

.save-status {
  position: absolute;
  top: -30px;
  right: 0;
  padding: 0.25rem 0.5rem;
  font-size: 0.8rem;
  background-color: rgba(0, 0, 0, 0.5);
  color: #fff;
  border-radius: 4px;
  transition: opacity 0.3s;
}

.rules-section {
  background-color: #252525;
  border-radius: 0.5rem;
  overflow: hidden;
}

.rules-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #1e1e1e;
  border-bottom: 1px solid #333;
}

.rules-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: 1rem;
  font-weight: 500;
}

.btn-add-rule {
  background: none;
  border: none;
  color: #5e72e4;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  transition: background-color 0.2s;
}

.btn-add-rule:hover {
  background-color: rgba(94, 114, 228, 0.1);
}

.rules-list {
  padding: 1rem;
}

.rule-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background-color: #1e1e1e;
  border-radius: 0.375rem;
  margin-bottom: 0.75rem;
}

.rule-content {
  flex: 1;
}

.rule-text {
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.rule-condition {
  font-size: 0.8rem;
  color: #999;
}

.rule-actions {
  display: flex;
  gap: 0.5rem;
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

.no-rules {
  color: #666;
  font-style: italic;
  padding: 1rem 0;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-container {
  background-color: #1e1e1e;
  border-radius: 0.5rem;
  width: 500px;
  max-width: 90%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #333;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
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

.modal-body {
  padding: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  background-color: #252525;
  border: 1px solid #333;
  border-radius: 0.375rem;
  color: #fff;
  font-size: 1rem;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.radio-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem;
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
</style> 