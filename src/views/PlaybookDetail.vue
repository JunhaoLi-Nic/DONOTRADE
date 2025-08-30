<script setup>
import { ref, reactive, onBeforeMount, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios';

import SpinnerLoadingPage from '../components/SpinnerLoadingPage.vue';
import PlaybookOverview from '../components/playbook/PlaybookOverview.vue';
import PlaybookRules from '../components/playbook/PlaybookRules.vue';
import PlaybookExecutedTrades from '../components/playbook/PlaybookExecutedTrades.vue';
import PlaybookMissedTrades from '../components/playbook/PlaybookMissedTrades.vue';
import PlaybookNotes from '../components/playbook/PlaybookNotes.vue';

import { spinnerLoadingPage, availableTags as globalAvailableTags, tags, playbooks } from '../stores/globals';
import { useFilterTags, useGetAvailableTags, useGetTagInfo, useGetTags } from '../utils/daily';
import AuthService from '../services/auth';
import TradeService from '../services/TradeService';
import PlaybookService from '../services/PlaybookService';

// Import the extractNameFromPlaybook function from playbooks.js
import { extractNameFromPlaybook } from '../utils/playbooks';

const route = useRoute();
const router = useRouter();
const currentTab = ref('overview');
const loadError = ref(false);
const errorMessage = ref('');

// Default mock data to avoid errors if API fails
const playbook = ref({
  name: 'Morning Top Reversal',
  playbook: '<p>This is a test playbook to verify the component loads correctly.</p>',
  stats: {
    netPnL: 87996.97,
    trades: 4,
    winRate: 50,
    profitFactor: 5.93,
    missedTrades: 2,
    expectancy: 21999.24,
    rulesFollowed: 100,
    averageWinner: 52915.59,
    averageLoser: -8917.10,
    largestProfit: 77471.72,
    largestLoss: -17122.44,
    totalRMultiple: 1.15
  }
});

// Tags management
const playbookTags = ref([]);
const showTagsDropdown = ref(false);
const availableTagsFlat = ref([]);
const filteredTrades = ref([]);
const allTrades = ref([]);

// Store the current playbook ID to use with localStorage
const currentPlaybookId = computed(() => route.params.id);

const tabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'rules', label: 'Playbook Rules' },
  { id: 'trades', label: 'Executed Trades' },
  { id: 'missed', label: 'Missed Trades' },
  { id: 'notes', label: 'Notes' }
];

// Path segments for breadcrumbs
const pathSegments = computed(() => {
  return [
    { name: playbook.value.name || 'Loading...', path: '#' },
    { name: getCurrentTabName(), path: '#' }
  ];
});

// Get current tab name for breadcrumb
function getCurrentTabName() {
  const tab = tabs.find(tab => tab.id === currentTab.value);
  return tab ? tab.label : '';
}

// Switch tabs
function switchTab(tabId) {
  console.log('Switching to tab:', tabId);
  currentTab.value = tabId;
  // Update URL without reloading (for bookmarking)
  const query = { ...route.query, tab: tabId };
  router.replace({ query });
}

// Go back to playbook list
function goBack() {
  router.push('/playbook');
}

// Share playbook
function sharePlaybook() {
  // Implement sharing functionality
  alert('Sharing feature will be implemented');
}

// Tags management functions
async function loadAvailableTags() {
  try {
    await useGetAvailableTags();
    //console.log('Available tags loaded');
    
    // Make availableTags accessible globally for components
    window.availableTags = globalAvailableTags;
    
    // Flatten tags for dropdown
    availableTagsFlat.value = [];
    
    // Safely handle globalAvailableTags
    if (globalAvailableTags.value && Array.isArray(globalAvailableTags.value)) {
      globalAvailableTags.value.forEach(group => {
        if (group && group.tags && Array.isArray(group.tags)) {
          group.tags.forEach(tag => {
            availableTagsFlat.value.push({
              ...tag,
              groupName: group.name || 'Ungrouped',
              groupColor: group.color || '#555'
            });
          });
        }
      });
      //console.log(`Flattened ${availableTagsFlat.value.length} tags for dropdown`);
    } else {
      console.warn('globalAvailableTags is undefined or not an array');
    }
  } catch (error) {
    console.error('Error loading available tags:', error);
    availableTagsFlat.value = []; // Ensure it's at least an empty array
  }
}

function toggleTagsDropdown() {
  showTagsDropdown.value = !showTagsDropdown.value;
}

function handleTagSelection(tag) {
  // Check if tag is already selected
  const existingIndex = playbookTags.value.findIndex(t => t.id === tag.id);
  
  if (existingIndex === -1) {
    // Add tag
    playbookTags.value.push(tag);
    savePlaybookTags();
  }
  
  // Close dropdown
  showTagsDropdown.value = false;
  
  // Filter trades based on new tag selection
  filterTradesByTags();
}

function removeTag(index) {
  console.log('Removing tag at index:', index);
  if (index >= 0 && index < playbookTags.value.length) {
    // Store the tag being removed for logging
    const removedTag = playbookTags.value[index];
    
    // Remove the tag
    playbookTags.value.splice(index, 1);
    
    // Update state
    savePlaybookTags();
    
    // Set tagFilterActive explicitly when no tags are left
    if (playbookTags.value.length === 0) {
      playbook.value.tagFilterActive = false;
    }
    
    // Update filtered trades
    filterTradesByTags();
  
    // Force the UI to update by creating a new array reference
    playbookTags.value = [...playbookTags.value];
  } 
  else {
    
  }
}

// Save playbook tags to API and localStorage
async function savePlaybookTags() {
  try {
    const playbookId = currentPlaybookId.value;
    
    // If no tags, clear localStorage
    if (playbookTags.value.length === 0) {
      localStorage.removeItem(`playbook_tags_${playbookId}`);
      
      // Use PlaybookService to save empty tags
      const response = await PlaybookService.savePlaybookTags(playbookId, []);
      console.log('Empty tags saved:', response);
      return response;
    }
    
    // Use PlaybookService to save tags
    const response = await PlaybookService.savePlaybookTags(playbookId, playbookTags.value);
    
    // Also save to localStorage for persistence
    localStorage.setItem(`playbook_tags_${playbookId}`, JSON.stringify(playbookTags.value));
    
    console.log('Playbook tags saved:', response);
    return response;
  } catch (error) {
    console.error('Error saving playbook tags:', error);
  }
}

// Load playbook tags from API or localStorage if available
async function loadPlaybookTags() {
  try {
    const playbookId = currentPlaybookId.value;
    
    // First try to load from localStorage for immediate display
    const localTags = localStorage.getItem(`playbook_tags_${playbookId}`);
    
    if (localTags) {
      try {
        const parsedTags = JSON.parse(localTags);
        if (Array.isArray(parsedTags)) {
          playbookTags.value = parsedTags;
          
          // Make playbookTags accessible globally for components
          window.playbookTags = playbookTags.value;
          console.log('Playbook tags loaded from localStorage:', playbookTags.value);
        }
      } catch (parseError) {
        console.error('Error parsing stored tags:', parseError);
      }
    }
    
    // Then try to load from API to get most up-to-date data
    try {
      // Use PlaybookService to get playbook tags
      const apiTags = await PlaybookService.getPlaybookTags(playbookId, globalAvailableTags.value);
      
      if (apiTags && apiTags.length > 0) {
        playbookTags.value = apiTags;
        
        // Store in localStorage for persistence
        localStorage.setItem(`playbook_tags_${playbookId}`, JSON.stringify(playbookTags.value));
      }
      
      // Make playbookTags accessible globally for components
      window.playbookTags = playbookTags.value;
      console.log('Playbook tags loaded from API and shared globally:', playbookTags.value);
    } catch (apiError) {
      console.error('Error fetching playbook tags:', apiError);
    }
  } catch (error) {
    console.error('Error loading playbook tags:', error);
  }
}

// Load trades and filter by tags
async function loadTrades() {
  try {
    spinnerLoadingPage.value = true;
    const playbookId = route.params.id;
    
    // Get auth headers
    const headers = AuthService.getAuthHeaders();
    
    try {
      // First, fetch all available tags to ensure we have them loaded
      await useGetTags();
      console.log("Loaded tags:", tags);
      
      // Log information about the expected format of tags to help debugging
      if (tags.length > 0) {
        console.log("Sample tag object:", tags[0]);
        console.log("Tag IDs we're looking for:", playbookTags.value.map(tag => tag.id));
      } else {
        console.log("No tags found in the system");
      }
      
      // Fetch trades from the API
      const response = await axios.get(`/api/trades`, { 
        params: { 
          limit: 1000, // Increased limit to get more trades
          // We don't filter by date in the API to ensure we get all trades
        },
        headers 
      });
      
      if (response.data && Array.isArray(response.data) && response.data.length > 0) {
        // First process the trades using TradeService
        let processedTrades = TradeService.processTradeData(response.data);
        
        // Then match the tags from the global tags store
        let taggedTrades = TradeService.matchTradeTagsFromGlobal(processedTrades, tags);
        
        // Filter out trades with EVEN status
        allTrades.value = taggedTrades.filter(trade => trade.status !== 'EVEN');
        
      } else {
        // Fallback to mock data
        console.warn('API did not return expected data format, using mock data');
        mockTradeData();
      }
    } catch (apiError) {
      console.error('Error fetching trades:', apiError);
      // Use mock data as fallback
      mockTradeData();
    } finally {
      spinnerLoadingPage.value = false;
    }
    
    
    // Initialize filtered trades with all trades or filtered by tags
    filterTradesByTags();
    
  } catch (error) {
    console.error('Error loading trades:', error);
    spinnerLoadingPage.value = false;
  }
}


// Mock data function for fallback
function mockTradeData() {
  // Mock data with no EVEN status trades
  const mockTrades = [
    {
      id: 1,
      openDate: '12/19/2022',
      symbol: 'SPY',
      status: 'WIN',
      closeDate: '12/19/2022',
      entryPrice: 391.12,
      exitPrice: 391.74,
      netPnL: 28359.45,
      netROI: 50.64,
      setups: 'morning top reversal',
      accountName: 'Umar2022 UAT',
      tags: ['tag_1', 'tag_3'] // Example tag IDs
    },
    {
      id: 2,
      openDate: '12/01/2022',
      symbol: 'SPY',
      status: 'WIN',
      closeDate: '12/01/2022',
      entryPrice: 391.07,
      exitPrice: 392.77,
      netPnL: 77471.72,
      netROI: 109.16,
      setups: 'morning top reversal',
      accountName: 'Umar2022 UAT',
      tags: ['tag_2', 'tag_4'] // Example tag IDs
    },
    {
      id: 3,
      openDate: '12/01/2022',
      symbol: 'SPY',
      status: 'LOSS',
      closeDate: '12/01/2022',
      entryPrice: 391.26,
      exitPrice: 390.84,
      netPnL: -17122.44,
      netROI: -33.89,
      setups: 'morning top reversal',
      accountName: 'Umar2022 UAT',
      tags: ['tag_1', 'tag_5'] // Example tag IDs
    },
    {
      id: 4,
      openDate: '11/14/2022',
      symbol: 'SPY',
      status: 'LOSS',
      closeDate: '11/14/2022',
      entryPrice: 391.33,
      exitPrice: 391.10,
      netPnL: -711.76,
      netROI: -17.84,
      setups: 'high of the day',
      accountName: 'Umar2022 UAT',
      tags: ['tag_3', 'tag_6'] // Example tag IDs
    },
    {
      id: 5,
      openDate: '06/13/2023',
      symbol: 'AAPL',
      status: 'LOSS',
      closeDate: '06/13/2023',
      entryPrice: 180.50,
      exitPrice: 179.25,
      netPnL: -79.13,
      netROI: -0.7,
      setups: 'gap fill',
      accountName: 'Demo Account',
      tags: ['random-test'] // This is the tag shown in the screenshot
    }
  ];
  
  // Assign the mock trades to allTrades
  allTrades.value = mockTrades;
  console.log(`Loaded ${allTrades.value.length} mock trades (no EVEN status trades included)`);
}

function filterTradesByTags() {
  // First, filter out trades with "EVEN" status from allTrades
  const tradesWithoutEven = allTrades.value.filter(trade => 
    trade.status !== 'EVEN'
  );
  
  // Load tags from localStorage or window as a fallback
  const playbookId = currentPlaybookId.value;
  let currentTags = playbookTags.value;
  
  // If playbookTags is empty, try to get from localStorage
  if (currentTags.length === 0) {
    // Clear localStorage if we're intentionally removing the last tag
    const localTags = localStorage.getItem(`playbook_tags_${playbookId}`);
    if (localTags) {
      try {
        const parsedTags = JSON.parse(localTags);
        if (Array.isArray(parsedTags) && parsedTags.length > 0) {
          // Only restore from localStorage if we actually want tags
          // If the playbookTags.value is intentionally empty, respect that
          if (playbookTags.value !== null) {
            currentTags = parsedTags;
            playbookTags.value = parsedTags; // Update the reactive ref
          } else {
            // Clear localStorage to match the intentional empty state
            localStorage.removeItem(`playbook_tags_${playbookId}`);
          }
        }
      } catch (parseError) {
        console.error('Error parsing stored tags during filtering:', parseError);
      }
    }
  }
  
  if (currentTags.length === 0) {
    // If no tags selected, show all trades (except EVEN ones)
    filteredTrades.value = [...tradesWithoutEven];
    playbook.value.tagFilterActive = false;
    console.log('No tags selected, showing all non-EVEN trades:', filteredTrades.value.length);
    
    // Ensure localStorage is cleared when no tags are selected
    localStorage.removeItem(`playbook_tags_${playbookId}`);
  } else {
    // Filter trades using PlaybookService
    filteredTrades.value = PlaybookService.filterTradesByTags(tradesWithoutEven, currentTags);
    
    // Set the tag filter active status
    playbook.value.tagFilterActive = true;
    
    console.log(`Filtered trades by tags: ${filteredTrades.value.length} matches found with tags: ${currentTags.map(tag => tag.id).join(', ')}`);
  }
  
  // Update playbook stats based on filtered trades
  updatePlaybookStats();
}

// Calculate statistics based on filtered trades
function updatePlaybookStats() {
  if (!filteredTrades.value || filteredTrades.value.length === 0) {
    // Set default stats if no trades match the filter
    playbook.value.stats = {
      netPnL: 0,
      winRate: 0,
      tradesCount: 0,
      profitFactor: 0,
      totalWins: 0,
      totalLosses: 0,
      avgWin: 0,
      avgLoss: 0,
      biggestWin: 0,
      biggestLoss: 0
    };
    return;
  }
  
  // Use PlaybookService to calculate stats
  playbook.value.stats = PlaybookService.calculatePlaybookStats(
    filteredTrades.value, 
    TradeService.calculateTradeProfit
  );
  
  console.log('Updated playbook stats based on filtered trades:', playbook.value.stats);
}

// Load playbook data
async function loadPlaybook() {
  spinnerLoadingPage.value = true;
  loadError.value = false;
  errorMessage.value = '';
  
  console.log('Loading playbook data...');
  
  try {
    const playbookId = route.params.id;
    console.log(`Loading playbook with ID: ${playbookId}`);
    
    if (!playbookId) {
      throw new Error('No playbook ID provided');
    }
    
    try {
      // Use PlaybookService to get playbook
      playbook.value = await PlaybookService.getPlaybook(playbookId);
      console.log('Playbook loaded:', playbook.value);
    } catch (apiError) {
      console.log('API error, using mock data instead:', apiError);
      // Keep using the default mock data
      loadError.value = true;
      errorMessage.value = `Failed to load playbook: ${apiError.response?.status || ''} ${apiError.message}. Using mock data instead.`;
    }
    
    // Check for tab in URL query param
    if (route.query.tab && tabs.some(tab => tab.id === route.query.tab)) {
      currentTab.value = route.query.tab;
    }
    
    // Load required data regardless of API errors
    await Promise.allSettled([
      loadAvailableTags(),
      loadPlaybookTags(),
      loadTrades()
    ]);
    
  } catch (error) {
    console.error('Error loading playbook:', error);
    loadError.value = true;
    errorMessage.value = `Failed to load playbook: ${error.message}`;
  } finally {
    spinnerLoadingPage.value = false;
  }
}

// Watch for changes in playbook tags to update filtered trades and global window object
watch(playbookTags, (newTags) => {
  // Update filtered trades
  filterTradesByTags();
  
  // Make playbookTags accessible globally for components
  window.playbookTags = newTags;
  
  // Also save to localStorage for persistence
  const playbookId = currentPlaybookId.value;
  localStorage.setItem(`playbook_tags_${playbookId}`, JSON.stringify(newTags));
  
  console.log('Playbook tags updated and shared globally:', newTags);
}, { deep: true });

// Initial load
onBeforeMount(() => {
  loadPlaybook();
});

// Debug: Log when currentTab changes
watch(currentTab, (newTab) => {
  console.log('Current tab changed to:', newTab);
});

// Fix dropdown navigation issue by using router.push instead of direct href
function navigateTo(route) {
  router.push(route);
}
</script>

<template>
  <SpinnerLoadingPage />
  <div v-show="!spinnerLoadingPage" class="playbook-detail">
    <!-- Error Alert -->
    <div v-if="loadError" class="alert alert-warning">
      {{ errorMessage }}
    </div>
    
    <!-- Breadcrumbs -->
    <div class="breadcrumbs d-flex mb-4">
      <div v-for="(segment, index) in pathSegments" :key="index" class="d-flex align-items-center">
        <a :href="segment.path" class="text-decoration-none">{{ segment.name }}</a>
        <span v-if="index < pathSegments.length - 1" class="mx-2">/</span>
      </div>
    </div>
    
    <!-- Page Header -->
    <div class="page-header d-flex justify-content-between align-items-center mb-4">
      <div>
        <h1 class="page-title">{{ playbook.name }}</h1>
        <div class="playbook-id text-muted">ID: {{ route.params.id }}</div>
        
        <!-- Tags Component -->
        <div class="playbook-tags mt-2">
          <div class="tag-container d-flex align-items-center flex-wrap">
            <span v-for="(tag, index) in playbookTags" :key="tag.id" 
                  class="tag txt-small me-1 mb-1"
                  :style="{ 'background-color': tag.groupColor || '#555' }">
              <span class="tag-name">{{ tag.name }}</span>
              <span 
                class="remove-tag" 
                @click.stop.prevent="removeTag(index)"
                @mousedown.prevent 
                tabindex="0"
              >×</span>
            </span>
            
            <!-- Tag Dropdown -->
            <div class="dropdown tag-dropdown">
              <button class="btn btn-sm btn-outline-light dropdown-toggle" 
                      @click="toggleTagsDropdown">
                Add Tag
              </button>
              
              <div class="dropdown-menu tag-dropdown-menu" 
                   :class="{ show: showTagsDropdown }">
                <div class="dropdown-header">Select a tag</div>
                <div class="dropdown-divider"></div>
                
                <div class="tag-groups">
                  <div v-for="group in globalAvailableTags" :key="group.name" class="tag-group">
                    <div class="group-header" v-if="group.name">{{ group.name }}</div>
                    <div class="group-tags">
                      <div v-for="tag in group.tags" :key="tag.id" 
                           class="dropdown-item tag-item"
                           @click="handleTagSelection({...tag, groupColor: group.color, groupName: group.name})">
                        <span class="tag-color" :style="{ 'background-color': group.color }"></span>
                        {{ tag.name }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Tag filter info -->
            <div class="tag-filter-info ms-3" v-if="playbookTags.length > 0">
              <span class="badge bg-info">
                <i class="uil uil-filter me-1"></i>
                Filtering trades by {{ playbookTags.length }} tag{{ playbookTags.length > 1 ? 's' : '' }}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="d-flex">
        <button @click="sharePlaybook" class="btn btn-outline-light btn-sm me-2">
          <i class="uil uil-share-alt me-1"></i> Share
        </button>
        <button @click="navigateTo('/playbook')" class="btn btn-primary">
          Back to Playbooks
        </button>
      </div>
    </div>
    
    <!-- Tabs -->
    <div class="nav-tabs-wrapper mb-4">
      <ul class="nav nav-tabs">
        <li class="nav-item" v-for="tab in tabs" :key="tab.id">
          <button class="nav-link" :class="{ active: currentTab === tab.id }" @click="switchTab(tab.id)">
            {{ tab.label }}
          </button>
        </li>
      </ul>
    </div>
    
    <!-- Tab Content -->
    <div class="tab-content">
      <!-- Overview Tab -->
      <div v-if="currentTab === 'overview'" class="tab-pane active">
        <PlaybookOverview :playbook="playbook" :trades="filteredTrades" />
      </div>
      
      <!-- Rules Tab -->
      <div v-if="currentTab === 'rules'" class="tab-pane active">
        <PlaybookRules :playbook="playbook" />
      </div>
      
      <!-- Executed Trades Tab -->
      <div v-if="currentTab === 'trades'" class="tab-pane active">
        <PlaybookExecutedTrades :playbook="playbook" :trades="filteredTrades" />
      </div>
      
      <!-- Missed Trades Tab -->
      <div v-if="currentTab === 'missed'" class="tab-pane active">
        <PlaybookMissedTrades :playbook="playbook" />
      </div>
      
      <!-- Notes Tab -->
      <div v-if="currentTab === 'notes'" class="tab-pane active">
        <PlaybookNotes :playbook="playbook" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.playbook-detail {
  padding: 1rem 2rem;
  min-height: calc(100vh - 64px);
  background-color: #121212;
  color: #fff;
}

.alert {
  padding: 0.75rem 1.25rem;
  border-radius: 0.375rem;
  margin-bottom: 1rem;
}

.alert-warning {
  background-color: rgba(251, 99, 64, 0.1);
  color: #fb6340;
  border: 1px solid rgba(251, 99, 64, 0.2);
}

.breadcrumbs {
  font-size: 0.9rem;
  color: #999;
}

.breadcrumbs a {
  color: #999;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.playbook-id {
  font-size: 0.9rem;
  color: #999;
}

.tab-content {
  min-height: 400px;
  background-color: #1e1e1e;
  border-radius: 0.5rem;
  padding: 1.5rem;
}

.nav-tabs {
  border-bottom: 1px solid #333;
  display: flex;
}

.nav-item {
  list-style: none;
}

.nav-link {
  border: none;
  border-bottom: 2px solid transparent;
  color: #999;
  padding: 0.75rem 1.25rem;
  transition: all 0.3s ease;
  background: none;
  cursor: pointer;
}

.nav-link.active {
  border-bottom: 2px solid #5e72e4;
  color: #fff;
  font-weight: 500;
  background-color: transparent;
}

.nav-link:hover:not(.active) {
  border-bottom: 2px solid #444;
  color: #fff;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 0.375rem;
  font-size: 0.9rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  transition: all 0.2s ease;
}

.btn-primary {
  background-color: #5e72e4;
  border-color: #5e72e4;
  color: #fff;
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.85rem;
}

.btn-outline-light {
  border: 1px solid #444;
  color: #fff;
  background: none;
}

.btn-outline-light:hover {
  background-color: #333;
  color: #fff;
  border-color: #555;
}

/* Tag styling */
.playbook-tags {
  display: flex;
  align-items: center;
}

.tag-container {
  max-width: 100%;
  min-height: 32px;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  background-color: #555;
  color: white;
  margin-right: 4px;
  margin-bottom: 4px;
  position: relative;
}

.tag-name {
  margin-right: 2px;
}

.remove-tag {
  margin-left: 4px;
  font-weight: bold;
  cursor: pointer;
  padding: 0 4px;
  z-index: 10;
  pointer-events: all;
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  min-height: 16px;
}

.remove-tag:hover {
  opacity: 0.7;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.txt-small {
  font-size: 0.8rem;
}

/* Tag dropdown styling */
.tag-dropdown {
  position: relative;
  margin-bottom: 4px;
}

.tag-dropdown-menu {
  width: 280px;
  max-height: 350px;
  overflow-y: auto;
  padding: 0.5rem 0;
  margin: 0;
  background-color: #1e1e1e;
  border: 1px solid #333;
  border-radius: 4px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 1000;
  display: none;
}

.tag-dropdown-menu.show {
  display: block;
}

.dropdown-header {
  padding: 0.5rem 1rem;
  font-size: 0.8rem;
  color: #999;
  font-weight: 500;
}

.dropdown-divider {
  height: 1px;
  background-color: #333;
  margin: 0.5rem 0;
}

.tag-groups {
  padding: 0 0.5rem;
}

.tag-group {
  margin-bottom: 0.75rem;
}

.group-header {
  font-size: 0.75rem;
  color: #999;
  padding: 0.25rem 0.5rem;
  font-weight: 500;
}

.tag-item {
  display: flex;
  align-items: center;
  padding: 0.5rem;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.15s ease;
}

.tag-item:hover {
  background-color: #2a2a2a;
}

.tag-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  margin-right: 8px;
  display: inline-block;
}

.tag-filter-info {
  font-size: 0.8rem;
}

.badge {
  padding: 0.35em 0.65em;
  font-weight: normal;
}

.bg-info {
  background-color: rgba(23, 162, 184, 0.2) !important;
  color: #5bc0de;
  border: 1px solid rgba(23, 162, 184, 0.3);
}

.d-flex {
  display: flex;
}

.justify-content-between {
  justify-content: space-between;
}

.align-items-center {
  align-items: center;
}

.mb-4 {
  margin-bottom: 1.5rem;
}

.mt-2 {
  margin-top: 0.5rem;
}

.me-1 {
  margin-right: 0.25rem;
}

.me-2 {
  margin-right: 0.5rem;
}

.mb-1 {
  margin-bottom: 0.25rem;
}

.ms-3 {
  margin-left: 1rem;
}

.mx-2 {
  margin-left: 0.5rem;
  margin-right: 0.5rem;
}

.text-decoration-none {
  text-decoration: none;
}

.text-muted {
  color: #999;
}

.flex-wrap {
  flex-wrap: wrap;
}
</style> 