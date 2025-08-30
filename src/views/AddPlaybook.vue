<script setup>
import { ref, reactive, onBeforeMount, computed } from 'vue';
import { useRouter } from 'vue-router';
import SpinnerLoadingPage from '../components/SpinnerLoadingPage.vue';
import { currentDate, itemToEditId, spinnerLoadingPage, playbookUpdate, playbookIdToEdit } from '../stores/globals';
import { useUploadPlaybook } from '../utils/playbooks';
import axios from 'axios';

/* MODULES */
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc.js';
dayjs.extend(utc);
import timezone from 'dayjs/plugin/timezone.js';
dayjs.extend(timezone);

const router = useRouter();

// Form data
const playbookData = reactive({
  name: '',
  description: '',
  icon: '📈',
  color: '#5e72e4',
  rules: {
    entry: [],
    exit: [],
    market: []
  }
});

// UI state
const currentStep = ref(1);
const totalSteps = 2;
const showRuleModal = ref(false);
const ruleModalType = ref('entry'); // 'entry', 'exit', or 'market'
const newRule = ref('');
const newRuleCondition = ref('always'); // 'always', 'winner', 'loser', 'breakeven'
const showGroupModal = ref(false);
const newGroupName = ref('');

// Icons for selection
const availableIcons = ['📈', '📉', '📊', '💹', '📋', '🔍', '⚡', '🔔', '📝', '🌅', '📖', '💰', '↩️', '🌠', '🚗', '❌', '🔄', '💼'];

// Colors for selection
const availableColors = [
  '#5e72e4', // Primary blue
  '#2dce89', // Success green
  '#f5365c', // Danger red
  '#fb6340', // Warning orange
  '#11cdef', // Info cyan
  '#8965e0', // Purple
  '#f3a4b5', // Pink
  '#45aaf2'  // Light blue
];

onBeforeMount(async () => {
  spinnerLoadingPage.value = true;
  
  // If we're editing an existing playbook, load its data
  if (itemToEditId.value) {
    await loadPlaybookToEdit(itemToEditId.value);
  }
  
  // Clear the edit ID from session storage
  sessionStorage.removeItem('editItemId');
  
  spinnerLoadingPage.value = false;
});

async function loadPlaybookToEdit(playbookId) {
  try {
    playbookIdToEdit.value = playbookId;
    console.log("Getting playbook to edit:", playbookId);
    
    const response = await axios.get(`/api/playbooks/${playbookId}`);
    if (response.data) {
      const playbook = response.data;
      
      // Populate form data
      playbookData.name = playbook.name || '';
      playbookData.description = playbook.description || '';
      playbookData.icon = playbook.icon || '📈';
      playbookData.color = playbook.color || '#5e72e4';
      
      // Parse rules if they exist
      if (playbook.rules) {
        playbookData.rules = {
          entry: playbook.rules.entry || [],
          exit: playbook.rules.exit || [],
          market: playbook.rules.market || []
        };
      }
    } else {
      console.error("No playbook found with that ID");
    }
  } catch (error) {
    console.error("Error fetching playbook:", error);
  }
}

function nextStep() {
  if (currentStep.value < totalSteps) {
    currentStep.value++;
  }
}

function previousStep() {
  if (currentStep.value > 1) {
    currentStep.value--;
  }
}

function selectIcon(icon) {
  playbookData.icon = icon;
}

function selectColor(color) {
  playbookData.color = color;
}

function openRuleModal(type) {
  ruleModalType.value = type;
  newRule.value = '';
  newRuleCondition.value = 'always';
  showRuleModal.value = true;
}

function closeRuleModal() {
  showRuleModal.value = false;
}

function addRule() {
  if (!newRule.value.trim()) return;
  
  const rule = {
    text: newRule.value.trim(),
    condition: newRuleCondition.value,
    id: Date.now().toString()
  };
  
  playbookData.rules[ruleModalType.value].push(rule);
  closeRuleModal();
}

function deleteRule(type, ruleId) {
  playbookData.rules[type] = playbookData.rules[type].filter(rule => rule.id !== ruleId);
}

function openGroupModal() {
  newGroupName.value = '';
  showGroupModal.value = true;
}

function closeGroupModal() {
  showGroupModal.value = false;
}

function addGroup() {
  if (!newGroupName.value.trim()) return;
  // In a real implementation, you would save the group to the database
  closeGroupModal();
}

async function savePlaybook() {
  try {
    spinnerLoadingPage.value = true;
    
    const playbookPayload = {
      name: playbookData.name,
      description: playbookData.description,
      icon: playbookData.icon,
      color: playbookData.color,
      rules: playbookData.rules,
      dateUnix: Math.floor(Date.now() / 1000),
      date: dayjs().format('YYYY-MM-DD'),
      playbook: `<h1>${playbookData.name}</h1><p>${playbookData.description}</p>`
    };
    
    if (playbookIdToEdit.value) {
      // Update existing playbook
      await axios.put(`/api/playbooks/${playbookIdToEdit.value}`, playbookPayload);
    } else {
      // Create new playbook
      await axios.post('/api/playbooks', playbookPayload);
    }
    
    router.push('/playbook');
  } catch (error) {
    console.error("Error saving playbook:", error);
    alert("Failed to save playbook: " + (error.response?.data?.detail || error.message));
  } finally {
    spinnerLoadingPage.value = false;
  }
}

function cancel() {
  router.push('/playbook');
}
</script>

<template>
  <SpinnerLoadingPage />
  <div class="playbook-create" v-show="!spinnerLoadingPage">
    <!-- Header -->
    <div class="playbook-header">
      <div class="breadcrumbs">
        <span>Playbook</span>
        <span class="separator">/</span>
        <span class="current">Create Playbook</span>
      </div>
    </div>
    
    <!-- Main Content -->
    <div class="playbook-content">
      <!-- Step 1: General Information -->
      <div v-show="currentStep === 1" class="playbook-step">
        <div class="section-container">
          <div class="section-header">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: '50%' }"></div>
            </div>
          </div>
          
          <div class="section-grid">
            <!-- Left Section: General Information -->
            <div class="section">
              <h2 class="section-title">General Information</h2>
              <p class="section-description">
                Upload an icon or an image and name your trading playbook and get going with tradezella.
              </p>
              
              <div class="form-group">
                <div class="icon-selector">
                  <button class="btn btn-icon">
                    <i class="uil uil-image-plus"></i>
                    Add Icon
                  </button>
                  
                  <button class="btn btn-color">
                    Choose a Color
                  </button>
                </div>
                
                <p class="helper-text">Add Icon or choose a colour that represents your Playbook.</p>
                
                <div class="icon-grid">
                  <div 
                    v-for="icon in availableIcons" 
                    :key="icon" 
                    class="icon-item" 
                    :class="{ active: playbookData.icon === icon }"
                    @click="selectIcon(icon)"
                  >
                    {{ icon }}
                  </div>
                </div>
                
                <div class="color-grid">
                  <div 
                    v-for="color in availableColors" 
                    :key="color" 
                    class="color-item" 
                    :style="{ backgroundColor: color }"
                    :class="{ active: playbookData.color === color }"
                    @click="selectColor(color)"
                  >
                  </div>
                </div>
              </div>
              
              <div class="form-group">
                <label for="playbook-name">Playbook Name</label>
                <input 
                  type="text" 
                  id="playbook-name" 
                  v-model="playbookData.name"
                  placeholder="Name your trading playbook"
                  class="form-control"
                />
              </div>
              
              <div class="form-group">
                <label for="playbook-description">Description</label>
                <textarea 
                  id="playbook-description" 
                  v-model="playbookData.description"
                  placeholder="Add description to your trading playbook"
                  class="form-control"
                  rows="3"
                ></textarea>
              </div>
            </div>
            
            <!-- Right Section: Trading Playbook Rules -->
            <div class="section">
              <h2 class="section-title">Trading Playbook Rules</h2>
              <p class="section-description">
                List your rules, track and optimize your playbook.
              </p>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Step 2: Trading Rules -->
      <div v-show="currentStep === 2" class="playbook-step">
        <div class="section-container">
          <div class="section-header">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: '100%' }"></div>
            </div>
          </div>
          
          <div class="section">
            <div class="d-flex justify-content-between align-items-center mb-4">
              <div>
                <h2 class="section-title">Trading Playbook Rules</h2>
                <p class="section-description">
                  List your rules, track and optimize your playbook.
                </p>
              </div>
              <button class="btn btn-primary" @click="openGroupModal">
                <i class="uil uil-plus"></i> Create New Group
              </button>
            </div>
            
            <div class="rules-container">
              <div class="rules-section">
                <div class="rules-header">
                  <div class="rules-title">
                    <i class="uil uil-arrow-down"></i>
                    <h3>Entry Criteria</h3>
                  </div>
                  <div class="rules-actions">
                    <button class="btn btn-text" @click="openRuleModal('entry')">
                      <i class="uil uil-plus"></i> Create new rule
                    </button>
                  </div>
                </div>
                
                <div class="rules-list">
                  <div v-for="rule in playbookData.rules.entry" :key="rule.id" class="rule-item">
                    <div class="rule-handle">
                      <i class="uil uil-draggabledots"></i>
                    </div>
                    <div class="rule-text">{{ rule.text }}</div>
                    <button class="btn btn-delete" @click="deleteRule('entry', rule.id)">
                      <i class="uil uil-trash-alt"></i> Delete
                    </button>
                  </div>
                  
                  <div v-if="playbookData.rules.entry.length === 0" class="rule-empty">
                    No entry criteria defined yet. Click "Create new rule" to add one.
                  </div>
                </div>
              </div>
              
              <div class="rules-section">
                <div class="rules-header">
                  <div class="rules-title">
                    <i class="uil uil-arrow-up"></i>
                    <h3>Exit Criteria</h3>
                  </div>
                  <div class="rules-actions">
                    <button class="btn btn-text" @click="openRuleModal('exit')">
                      <i class="uil uil-plus"></i> Create new rule
                    </button>
                  </div>
                </div>
                
                <div class="rules-list">
                  <div v-for="rule in playbookData.rules.exit" :key="rule.id" class="rule-item">
                    <div class="rule-handle">
                      <i class="uil uil-draggabledots"></i>
                    </div>
                    <div class="rule-text">{{ rule.text }}</div>
                    <button class="btn btn-delete" @click="deleteRule('exit', rule.id)">
                      <i class="uil uil-trash-alt"></i> Delete
                    </button>
                  </div>
                  
                  <div v-if="playbookData.rules.exit.length === 0" class="rule-empty">
                    No exit criteria defined yet. Click "Create new rule" to add one.
                  </div>
                </div>
              </div>
              
              <div class="rules-section">
                <div class="rules-header">
                  <div class="rules-title">
                    <i class="uil uil-chart-line"></i>
                    <h3>Market Conditions</h3>
                  </div>
                  <div class="rules-actions">
                    <button class="btn btn-text" @click="openRuleModal('market')">
                      <i class="uil uil-plus"></i> Create new rule
                    </button>
                  </div>
                </div>
                
                <div class="rules-list">
                  <div v-for="rule in playbookData.rules.market" :key="rule.id" class="rule-item">
                    <div class="rule-handle">
                      <i class="uil uil-draggabledots"></i>
                    </div>
                    <div class="rule-text">{{ rule.text }}</div>
                    <button class="btn btn-delete" @click="deleteRule('market', rule.id)">
                      <i class="uil uil-trash-alt"></i> Delete
                    </button>
                  </div>
                  
                  <div v-if="playbookData.rules.market.length === 0" class="rule-empty">
                    No market conditions defined yet. Click "Create new rule" to add one.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Navigation Buttons -->
      <div class="playbook-footer">
        <button class="btn btn-outline" @click="cancel">Cancel</button>
        
        <div class="navigation-buttons">
          <button v-if="currentStep > 1" class="btn btn-outline" @click="previousStep">
            <i class="uil uil-arrow-left"></i> Previous
          </button>
          
          <button v-if="currentStep < totalSteps" class="btn btn-primary" @click="nextStep">
            Next <i class="uil uil-arrow-right"></i>
          </button>
          
          <button v-else class="btn btn-primary" @click="savePlaybook">
            Create Playbook
          </button>
        </div>
      </div>
    </div>
    
    <!-- Rule Modal -->
    <div class="modal-overlay" v-if="showRuleModal">
      <div class="modal-container">
        <div class="modal-header">
          <h3>Create new {{ ruleModalType === 'entry' ? 'Entry' : ruleModalType === 'exit' ? 'Exit' : 'Market' }} Criteria rule</h3>
          <button class="btn btn-close" @click="closeRuleModal">
            <i class="uil uil-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <input 
              type="text" 
              v-model="newRule" 
              class="form-control"
              placeholder="Enter rule description"
            />
          </div>
          
          <div class="form-group">
            <p class="form-label">Show rule only when:</p>
            
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="newRuleCondition" value="always" />
                <span class="radio-text">Always</span>
              </label>
              
              <label class="radio-label">
                <input type="radio" v-model="newRuleCondition" value="winner" />
                <span class="radio-text">When trade is a winner</span>
              </label>
              
              <label class="radio-label">
                <input type="radio" v-model="newRuleCondition" value="loser" />
                <span class="radio-text">When trade is a loser</span>
              </label>
              
              <label class="radio-label">
                <input type="radio" v-model="newRuleCondition" value="breakeven" />
                <span class="radio-text">When trade is break even</span>
              </label>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-outline" @click="closeRuleModal">Cancel</button>
          <button class="btn btn-primary" @click="addRule">Create</button>
        </div>
      </div>
    </div>
    
    <!-- Group Modal -->
    <div class="modal-overlay" v-if="showGroupModal">
      <div class="modal-container">
        <div class="modal-header">
          <h3>Create New Group</h3>
          <button class="btn btn-close" @click="closeGroupModal">
            <i class="uil uil-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label for="group-name">Group Name</label>
            <input 
              type="text" 
              id="group-name"
              v-model="newGroupName" 
              class="form-control"
              placeholder="Enter group name"
            />
          </div>
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-outline" @click="closeGroupModal">Cancel</button>
          <button class="btn btn-primary" @click="addGroup">Create</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.playbook-create {
  min-height: 100vh;
  background-color: #121212;
  color: #fff;
  display: flex;
  flex-direction: column;
}

.playbook-header {
  padding: 1rem 2rem;
  border-bottom: 1px solid #2c2c2c;
}

.breadcrumbs {
  display: flex;
  align-items: center;
  font-size: 0.9rem;
}

.breadcrumbs .separator {
  margin: 0 0.5rem;
  color: #666;
}

.breadcrumbs .current {
  font-weight: 500;
}

.playbook-content {
  flex: 1;
  padding: 0 2rem;
  display: flex;
  flex-direction: column;
}

.playbook-step {
  flex: 1;
}

.section-container {
  background-color: #1a1a1a;
  border-radius: 0.5rem;
  margin: 1.5rem 0;
}

.section-header {
  padding: 0;
}

.progress-bar {
  height: 4px;
  background-color: #2c2c2c;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: #2dce89;
}

.section-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  padding: 1.5rem;
}

.section {
  padding: 1.5rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.section-description {
  color: #999;
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-control {
  width: 100%;
  padding: 0.75rem 1rem;
  background-color: #1e1e1e;
  border: 1px solid #333;
  border-radius: 0.375rem;
  color: #fff;
  font-size: 1rem;
}

.form-control:focus {
  border-color: #5e72e4;
  outline: none;
}

.form-control::placeholder {
  color: #666;
}

label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.icon-selector {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-size: 0.9rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  border: none;
}

.btn-icon {
  background-color: #1e1e1e;
  color: #fff;
  border: 1px solid #333;
}

.btn-color {
  background-color: #1e1e1e;
  color: #fff;
  border: 1px solid #333;
}

.helper-text {
  color: #999;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.icon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(40px, 1fr));
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.icon-item {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #1e1e1e;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 1.25rem;
  border: 1px solid #333;
}

.icon-item.active {
  border-color: #5e72e4;
  background-color: rgba(94, 114, 228, 0.1);
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(40px, 1fr));
  gap: 0.5rem;
}

.color-item {
  width: 40px;
  height: 40px;
  border-radius: 0.375rem;
  cursor: pointer;
  border: 2px solid transparent;
}

.color-item.active {
  border-color: #fff;
}

.rules-container {
  background-color: #1e1e1e;
  border-radius: 0.5rem;
  overflow: hidden;
}

.rules-section {
  margin-bottom: 1.5rem;
}

.rules-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background-color: #252525;
}

.rules-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.rules-title h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 500;
}

.rules-actions {
  display: flex;
  align-items: center;
}

.btn-text {
  background: none;
  color: #5e72e4;
  padding: 0.25rem 0.5rem;
}

.btn-text i {
  margin-right: 0.25rem;
}

.rules-list {
  padding: 1rem;
}

.rule-item {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  background-color: #252525;
  border-radius: 0.375rem;
  margin-bottom: 0.5rem;
}

.rule-handle {
  margin-right: 0.75rem;
  color: #666;
  cursor: grab;
}

.rule-text {
  flex: 1;
}

.btn-delete {
  background: none;
  color: #f5365c;
  padding: 0.25rem 0.5rem;
}

.rule-empty {
  color: #666;
  padding: 1rem 0;
  font-style: italic;
}

.playbook-footer {
  display: flex;
  justify-content: space-between;
  padding: 1.5rem 0;
  border-top: 1px solid #2c2c2c;
  margin-top: auto;
}

.navigation-buttons {
  display: flex;
  gap: 1rem;
}

.btn-outline {
  background: none;
  border: 1px solid #333;
  color: #fff;
}

.btn-outline:hover {
  background-color: #252525;
}

.btn-primary {
  background-color: #5e72e4;
  color: #fff;
}

.btn-primary:hover {
  background-color: #4c61d0;
}

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
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #2c2c2c;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.btn-close {
  background: none;
  color: #999;
  font-size: 1.25rem;
  padding: 0;
}

.modal-body {
  padding: 1.5rem;
}

.form-label {
  font-weight: 500;
  margin-bottom: 1rem;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.radio-label {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.radio-label input {
  margin-right: 0.75rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.5rem;
  border-top: 1px solid #2c2c2c;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .section-grid {
    grid-template-columns: 1fr;
  }
}
</style>