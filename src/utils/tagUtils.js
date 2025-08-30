import axios from 'axios';
import AuthService from '../services/auth';
import { availableTags as globalAvailableTags, tags } from '../stores/globals';

/**
 * Load all available tags from the API
 * @returns {Promise<Array<Object>>} Array of available tag groups
 */
export async function loadAvailableTags() {
  try {
    // Get auth headers
    const headers = AuthService.getAuthHeaders();
    
    const response = await axios.get('/api/availableTags', { headers });
    
    // Process the response
    if (response.data && Array.isArray(response.data)) {
      return response.data;
    }
    
    // Return default structure if no tags exist
    return [{
      id: "group_0",
      name: "Ungrouped",
      color: "#6c757d",
      tags: []
    }];
  } catch (error) {
    console.error("Error loading available tags:", error);
    // Return a default tag group if we can't load from server
    return [{
      id: "group_0",
      name: "Ungrouped",
      color: "#6c757d",
      tags: []
    }];
  }
}

/**
 * Flatten the nested tag structure for dropdown display
 * @param {Array<Object>} tagGroups - Tag groups from globalAvailableTags
 * @returns {Array<Object>} - Flattened tags array with group info
 */
export function flattenTagsForDropdown(tagGroups) {
  if (!tagGroups || !Array.isArray(tagGroups)) {
    return [];
  }
  
  const flattened = [];
  
  tagGroups.forEach(group => {
    if (group && group.tags && Array.isArray(group.tags)) {
      group.tags.forEach(tag => {
        flattened.push({
          ...tag,
          groupName: group.name || 'Ungrouped',
          groupColor: group.color || '#555'
        });
      });
    }
  });
  
  return flattened;
}

/**
 * Convert tag IDs to full tag objects with group information
 * @param {Array<string>} tagIds - Array of tag IDs
 * @param {Array<Object>} availableTags - Available tag groups
 * @returns {Array<Object>} - Full tag objects with group info
 */
export function mapTagIdsToFullTags(tagIds, availableTags) {
  if (!tagIds || !Array.isArray(tagIds) || !availableTags || !Array.isArray(availableTags)) {
    return [];
  }
  
  return tagIds.map(tagId => {
    let foundTag = null;
    
    // Search available tags for the tag with this ID
    for (const group of availableTags) {
      if (group && group.tags && Array.isArray(group.tags)) {
        const tag = group.tags.find(t => t.id === tagId);
        if (tag) {
          foundTag = {
            ...tag,
            groupName: group.name || 'Ungrouped',
            groupColor: group.color || '#555'
          };
          break;
        }
      }
    }
    
    // If not found, create a placeholder
    if (!foundTag) {
      foundTag = { 
        id: tagId, 
        name: tagId.includes('tag_') ? tagId.replace('tag_', 'Tag ') : tagId,
        groupColor: '#555'
      };
    }
    
    return foundTag;
  });
}

/**
 * Filter trades based on selected tags
 * @param {Array<Object>} trades - Array of trade objects
 * @param {Array<Object>} selectedTags - Array of selected tag objects
 * @returns {Array<Object>} - Filtered trades
 */
export function filterTradesByTags(trades, selectedTags) {
  if (!selectedTags || !Array.isArray(selectedTags) || selectedTags.length === 0) {
    // If no tags selected, return all trades
    return trades;
  }
  
  // Get the IDs of the selected tags
  const selectedTagIds = selectedTags.map(tag => tag.id);
  
  // Filter trades that have AT LEAST ONE of the selected tags
  return trades.filter(trade => {
    // If the trade has no tags array or it's empty, it can't match
    if (!trade.tags || !Array.isArray(trade.tags) || trade.tags.length === 0) {
      return false;
    }
    
    // Check if any of the trade's tags match the selected tags
    return trade.tags.some(tagId => selectedTagIds.includes(tagId));
  });
}

/**
 * Get tag information for a specific tag ID
 * @param {string} tagId - Tag ID to look up
 * @returns {Object} - Tag information including group details
 */
export function getTagInfo(tagId, availableTagGroups = globalAvailableTags.value) {
  let info = {
    groupColor: "#6c757d",  // Default color
    tagName: '',
    tagGroupId: "group_0",
    tagGroupName: "Ungrouped"
  };
  
  // Check if tag id exists then return info
  for (let group of availableTagGroups) {
    for (let tag of group.tags || []) {
      if (tag.id === tagId) {
        info.tagGroupId = group.id;
        info.tagGroupName = group.name;
        info.groupColor = group.color;
        info.tagName = tag.name;
        return info;
      }
    }
  }
  
  // Set default color if we have ungrouped
  if (availableTagGroups.length > 0) {
    const ungrouped = availableTagGroups.find(g => g.id === "group_0");
    if (ungrouped) {
      info.groupColor = ungrouped.color;
    }
  }
  
  return info;
}

/**
 * Add tags to trades based on trade IDs from global tags
 * @param {Array<Object>} trades - Trade objects
 * @returns {Array<Object>} - Trades with tags added
 */
export function addTagsToTrades(trades) {
  if (!Array.isArray(trades) || !Array.isArray(tags)) {
    return trades;
  }
  
  return trades.map(trade => {
    // Start with existing tags or empty array
    let tradeTags = trade.tags || [];
    
    // Trade IDs can be in multiple formats, try all possible ones
    const tradeIdPossibilities = [
      trade._id,                   // MongoDB ObjectId
      trade.id,                    // String ID
      trade.dateUnix?.toString(),  // Unix timestamp as string
      trade.openDate               // Date string
    ];
    
    // Find tags for this trade by checking all possible ID formats
    for (const possibleId of tradeIdPossibilities) {
      if (!possibleId) continue;
      
      const tagEntry = tags.find(tag => tag.tradeId === possibleId);
      if (tagEntry && Array.isArray(tagEntry.tags)) {
        tradeTags = tagEntry.tags;
        break; // Stop once we find a match
      }
    }
    
    // Return trade with updated tags
    return {
      ...trade,
      tags: tradeTags
    };
  });
} 