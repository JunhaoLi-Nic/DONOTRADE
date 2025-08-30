<script setup>
import { ref, computed } from 'vue';
import { useGetTagInfo } from '../../utils/daily';
import { useCreatedDateFormat } from '../../utils/utils';

const props = defineProps({
  playbook: {
    type: Object,
    required: true
  },
  trades: {
    type: Array,
    default: () => []
  }
});

// Sorting and filtering
const sortBy = ref('date');
const sortDir = ref('desc');
const searchQuery = ref('');

// Get selected tag IDs from playbook
const selectedTagIds = computed(() => {
  if (!props.playbook || !props.playbook.tags) {
    // If no playbook tags, try to get them from the playbookTags array if it exists
    if (typeof window !== 'undefined' && window.playbookTags) {
      return window.playbookTags.map(tag => tag.id);
    }
    
    // If window.playbookTags is empty, try to get from localStorage
    const playbookId = props.playbook?.id || document.location.pathname.split('/').pop();
    if (playbookId) {
      try {
        const localTags = localStorage.getItem(`playbook_tags_${playbookId}`);
        if (localTags) {
          const parsedTags = JSON.parse(localTags);
          if (Array.isArray(parsedTags) && parsedTags.length > 0) {
            return parsedTags.map(tag => tag.id);
          }
        }
      } catch (error) {
        console.error("Error loading tags from localStorage:", error);
      }
    }
    
    return [];
  }
  return props.playbook.tags.map(tag => tag.id);
});

// Check if a tag is in the highlighted/selected tags
const isHighlightedTag = (tagId) => {
  // First try props.playbook tags
  if (props.playbook && 
      props.playbook.tagFilterActive && 
      selectedTagIds.value.includes(tagId)) {
    return true;
  }
  
  // If not found, check localStorage directly
  const playbookId = props.playbook?.id || document.location.pathname.split('/').pop();
  if (playbookId) {
    try {
      const localTags = localStorage.getItem(`playbook_tags_${playbookId}`);
      if (localTags) {
        const parsedTags = JSON.parse(localTags);
        if (Array.isArray(parsedTags) && parsedTags.length > 0) {
          return parsedTags.some(tag => tag.id === tagId);
        }
      }
    } catch (error) {
      console.error("Error checking tags in localStorage:", error);
    }
  }
  
  return false;
};

// Computed filtered and sorted trades
const filteredTrades = computed(() => {
  let result = [...props.trades];
  
  // Debug logging for trade tags
  if (result.length > 0) {
    console.log('Trades received in PlaybookExecutedTrades:', result);
    console.log('Sample trade tags:', result[0]?.tags);
  } else {
    console.log('No trades received in PlaybookExecutedTrades');
  }
  
  // Apply search filter
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(trade => {
      return (
        trade.symbol.toLowerCase().includes(query) ||
        trade.accountName?.toLowerCase().includes(query) ||
        (trade.setups && trade.setups.toLowerCase().includes(query))
      );
    });
  }
  
  // Apply sorting
  result.sort((a, b) => {
    let aValue, bValue;
    
    // Extract the values to compare based on sortBy
    switch (sortBy.value) {
      case 'date':
        aValue = new Date(a.openDate);
        bValue = new Date(b.openDate);
        break;
      case 'symbol':
        aValue = a.symbol;
        bValue = b.symbol;
        break;
      case 'netPnL':
        aValue = a.netPnL;
        bValue = b.netPnL;
        break;
      case 'netROI':
        aValue = a.netROI;
        bValue = b.netROI;
        break;
      default:
        aValue = a[sortBy.value];
        bValue = b[sortBy.value];
    }
    
    // Perform the comparison
    if (sortDir.value === 'asc') {
      return aValue > bValue ? 1 : -1;
    } else {
      return aValue < bValue ? 1 : -1;
    }
  });
  
  return result;
});


function formatPrice(price) {
  if (price === undefined || price === null) return '';
  return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatCurrency(value) {
  if (value === undefined || value === null) return '';
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatPercent(value) {
  if (value === undefined || value === null) return '';
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '%';
}

// Calculate ROI for a trade
function calculateROI(trade) {
  if (!trade) return 0;
  
  // First try to use the existing netROI if it's valid and not zero
  if (trade.netROI !== undefined && trade.netROI !== null && trade.netROI !== 0) {
    try {
      // Convert to number if it's a string
      const roiValue = typeof trade.netROI === 'string' 
        ? parseFloat(trade.netROI.replace('%', '')) 
        : parseFloat(trade.netROI);
      
      if (!isNaN(roiValue) && roiValue !== 0) {
        return roiValue;
      }
    } catch (e) {
      console.error(`Error processing ROI for trade:`, e);
    }
  }
  
  // If netROI is 0 or invalid, calculate it from scratch
  if (trade.netPnL && trade.entryPrice && trade.quantity) {
    const investment = trade.entryPrice * trade.quantity;
    if (investment !== 0) {
      const calculatedROI = (trade.netPnL / investment) * 100;
      console.log(`Calculated ROI for ${trade.symbol}: ${calculatedROI}% from P&L: ${trade.netPnL}, investment: ${investment}`);
      return calculatedROI;
    }
  }
  
  return 0;
}

function getStatusClass(status) {
  if (!status) return '';
  const statusLower = status.toLowerCase();
  if (statusLower === 'win') return 'status-win';
  if (statusLower === 'loss') return 'status-loss';
  return 'status-even';
}

function getDisplayTags(trade) {
  if (!trade) {
    console.log('Trade object is undefined');
    return [];
  }

  
  if (!trade.tags) {
    console.log(`No tags found for trade ${trade.symbol}`);
    return [];
  }
  
  if (!Array.isArray(trade.tags)) {
    console.warn(`Tags for trade ${trade.symbol} is not an array:`, trade.tags);
    // Try to convert to array if it's something else
    try {
      if (typeof trade.tags === 'string') {
        // If it's a comma-separated string
        return trade.tags.split(',').map(t => t.trim()).slice(0, 2);
      }
      return [];
    } catch (e) {
      console.error('Error processing tags:', e);
      return [];
    }
  }
  
  return trade.tags.slice(0, 2); // Show max 2 tags
}

function hasMoreTags(trade) {
  return trade.tags && trade.tags.length > 2;
}

function additionalTagsCount(trade) {
  return trade.tags ? trade.tags.length - 2 : 0;
}

function getTagInfo(tagId) {
  console.log(`Getting tag info for tagId: ${tagId}`);
  
  // Access the global availableTags store
  const globalAvailableTags = window.availableTags?.value || [];
  
  if (!globalAvailableTags || !Array.isArray(globalAvailableTags)) {
    console.log('Available tags not loaded in global store');
    // Return a default tag with the ID as name
    return {
      tagName: tagId.includes('tag_') ? tagId.replace('tag_', 'Tag ') : tagId,
      groupColor: '#555'
    };
  }
  
  // Search through all tag groups to find the matching tag ID
  for (const group of globalAvailableTags) {
    if (group && group.tags && Array.isArray(group.tags)) {
      const foundTag = group.tags.find(tag => tag.id === tagId);
      if (foundTag) {
        console.log(`Found tag in group ${group.name}:`, foundTag);
        return {
          tagName: foundTag.name,
          groupColor: group.color || '#555'
        };
      }
    }
  }
  
  // If tag not found in the availableTags, try useGetTagInfo as fallback
  const tagInfo = useGetTagInfo(tagId);
  
  if (tagInfo && tagInfo.tagName) {
    return tagInfo;
  }
  
  // If all else fails, return a default
  console.log(`No tag info found for ID: ${tagId}`);
  return {
    tagName: tagId.includes('tag_') ? tagId.replace('tag_', 'Tag ') : tagId,
    groupColor: '#555'
  };
}

function setSortBy(field) {
  if (sortBy.value === field) {
    toggleSortDirection();
  } else {
    sortBy.value = field;
    sortDir.value = 'asc';
  }
}

function toggleSortDirection() {
  sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc';
}
</script>

<template>
  <div class="executed-trades-container">
    <!-- Filters bar -->
    <div class="filters-bar">
      <div class="search-box">
        <i class="uil uil-search search-icon"></i>
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="Search trades..." 
          class="search-input"
        >
      </div>
      
      <div class="filter-stats">
        <span v-if="searchQuery" class="search-active">
          <i class="uil uil-filter"></i>
          {{ filteredTrades.length }} results
        </span>
        
        <div class="sorting">
          <span>Sort by:</span>
          <select v-model="sortBy" class="sort-select">
            <option value="date">Date</option>
            <option value="symbol">Symbol</option>
            <option value="netPnL">P&L</option>
            <option value="netROI">ROI</option>
          </select>
          <button @click="toggleSortDirection" class="sort-dir-btn">
            <i :class="sortDir === 'asc' ? 'uil uil-arrow-up' : 'uil uil-arrow-down'"></i>
          </button>
        </div>
      </div>
    </div>
    
    <!-- Tag filter notice -->
    <div v-if="props.playbook && props.playbook.tagFilterActive" class="tag-filter-notice">
      <i class="uil uil-filter me-1"></i>
      Showing trades with selected tags
    </div>
    
    <!-- Trades table -->
    <div class="trades-table-wrapper">
      <table class="trades-table">
        <thead>
          <tr>
            <th @click="setSortBy('date')" class="sortable">
              Date {{ sortBy === 'date' ? (sortDir === 'asc' ? '↑' : '↓') : '' }}
            </th>
            <th @click="setSortBy('symbol')" class="sortable">
              Symbol {{ sortBy === 'symbol' ? (sortDir === 'asc' ? '↑' : '↓') : '' }}
            </th>
            <th>Status</th>
            <th>Entry</th>
            <th>Exit</th>
            <th @click="setSortBy('netPnL')" class="sortable">
              P&L {{ sortBy === 'netPnL' ? (sortDir === 'asc' ? '↑' : '↓') : '' }}
            </th>
            <th @click="setSortBy('netROI')" class="sortable">
              ROI {{ sortBy === 'netROI' ? (sortDir === 'asc' ? '↑' : '↓') : '' }}
            </th>
            <th>Tags</th>
            <th>Account</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="trade in filteredTrades" :key="trade.id">
            <td>{{ trade.closeDate !== 0 ? useCreatedDateFormat(trade.closeDate) : useCreatedDateFormat(trade.openDate) }}</td>
            <td>{{ trade.symbol }}</td>
            <td>
              <span class="status-badge" :class="getStatusClass(trade.status)">
                {{ trade.status }}
              </span>
            </td>
            <td>{{ formatPrice(trade.entryPrice) }}</td>
            <td>{{ formatPrice(trade.exitPrice) }}</td>
            <td :class="trade.netPnL >= 0 ? 'text-success' : 'text-danger'">
              {{ formatCurrency(trade.netPnL) }}
            </td>
            <td :class="calculateROI(trade) >= 0 ? 'text-success' : 'text-danger'">
              {{ formatPercent(calculateROI(trade)) }}
            </td>
            <td>
              <div class="tags-wrapper">
                <span v-for="tagId in getDisplayTags(trade)" :key="tagId" 
                      class="tag tag-small"
                      :class="isHighlightedTag(tagId) ? 'tag-highlighted' : ''"
                      :style="{ 'background-color': getTagInfo(tagId).groupColor || '#555' }">
                  {{ getTagInfo(tagId).tagName || tagId }}
                </span>
                <span v-if="hasMoreTags(trade)" class="tag-more tag-small">
                  +{{ additionalTagsCount(trade) }}
                </span>
                <span v-if="!trade.tags || trade.tags.length === 0" class="no-tags">
                  —
                </span>
              </div>
            </td>
            <td>{{ trade.accountName }}</td>
          </tr>
          <tr v-if="filteredTrades.length === 0">
            <td colspan="9" class="empty-table">
              <div class="empty-message">
                <i class="uil uil-chart"></i>
                <p v-if="props.playbook && props.playbook.tagFilterActive">
                  No trades match the selected tags.
                </p>
                <p v-else-if="searchQuery">
                  No trades match your search criteria.
                </p>
                <p v-else>
                  No trades found for this playbook.
                </p>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.executed-trades-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.filters-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.search-box {
  position: relative;
  width: 300px;
}

.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: #999;
}

.search-input {
  width: 100%;
  padding: 0.5rem 0.5rem 0.5rem 2rem;
  background-color: #252525;
  border: 1px solid #333;
  border-radius: 0.375rem;
  color: #fff;
  font-size: 0.9rem;
}

.search-input:focus {
  outline: none;
  border-color: #5e72e4;
}

.filter-stats {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: #999;
  font-size: 0.85rem;
}

.search-active {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background-color: rgba(94, 114, 228, 0.1);
  border-radius: 0.25rem;
  color: #5e72e4;
}

.sorting {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sort-select {
  background-color: #252525;
  color: #fff;
  border: 1px solid #333;
  border-radius: 0.25rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.85rem;
}

.sort-dir-btn {
  background-color: #252525;
  color: #999;
  border: 1px solid #333;
  border-radius: 0.25rem;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
}

.sort-dir-btn:hover {
  color: #fff;
}

.tag-filter-notice {
  padding: 0.5rem 1rem;
  background-color: rgba(94, 114, 228, 0.1);
  border-radius: 0.375rem;
  color: #5e72e4;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

.trades-table-wrapper {
  overflow-x: auto;
}

.trades-table {
  width: 100%;
  border-collapse: collapse;
}

.trades-table th,
.trades-table td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid #333;
}

.trades-table th {
  background-color: #1e1e1e;
  font-weight: 500;
  color: #999;
  white-space: nowrap;
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable:hover {
  color: #fff;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-win {
  background-color: rgba(45, 206, 137, 0.15);
  color: #2dce89;
}

.status-loss {
  background-color: rgba(245, 54, 92, 0.15);
  color: #f5365c;
}

.status-even {
  background-color: rgba(251, 188, 5, 0.15);
  color: #fbbc05;
}

.text-success {
  color: #2dce89;
}

.text-danger {
  color: #f5365c;
}

.tags-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  background-color: #555;
  color: white;
}

.tag-small {
  font-size: 0.7rem;
  padding: 1px 6px;
}

.tag-highlighted {
  border: 1px solid white;
  box-shadow: 0 0 3px rgba(255, 255, 255, 0.5);
}

.tag-more {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
  background-color: #333;
  color: #999;
}

.no-tags {
  color: #666;
  font-size: 0.9rem;
}

.empty-table {
  height: 200px;
}

.empty-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: #666;
}

.empty-message i {
  font-size: 2rem;
  margin-bottom: 1rem;
}

.empty-message p {
  margin: 0;
}

.me-1 {
  margin-right: 0.25rem;
}
</style> 