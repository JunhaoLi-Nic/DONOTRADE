<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, defineProps, defineEmits, Teleport } from 'vue';
import { useCreatedDateFormat, useTwoDecCurrencyFormat, useTimeFormat, useTimeDuration, useCheckVisibleScreen, useDecimalsArithmetic, useInitTooltip, useDateCalFormat, useSwingDuration } from '../utils/utils';
import Screenshot from './Screenshot.vue';
import { useSetupImageUpload, useSaveScreenshot } from '../utils/screenshots';
import { useGetExcursions, useGetTags, useGetAvailableTags, useUpdateAvailableTags, useUpdateTags, useFindHighestIdNumber, useFindHighestIdNumberTradeTags, useUpdateNote, useGetNotes, useGetTagInfo, useCreateAvailableTagsArray, useFilterSuggestions, useTradeTagsChange, useFilterTags, useToggleTagsDropdown, useResetTags, useDailySatisfactionChange } from '../utils/daily';
import { useCandlestickChart } from '../utils/charts';
import { useCreateOHLCV } from '../utils/addTrades';
import axios from 'axios';
import dayjs from 'dayjs';
// Import bootstrap for modal functionality
import * as bootstrap from 'bootstrap';

// Import global state
import { timeZoneTrade, tradeNote, tradeTags, tradeNoteChanged, tradeExcursionChanged, tradeScreenshotChanged, tradeTagsChanged, showTagsList, selectedTagIndex, excursion, saveButton, tagInput, notes, tags, availableTags, screenshot, apis, excursions, markerAreaOpen, spinnerSetups, screenshots, tradeTagsId, tradeTagsDateUnix } from '../stores/globals';

const props = defineProps({
  isOpen: Boolean,
  trade: Object,
  tradeIndex: Number,
  dateUnix: Number
});

const emit = defineEmits(['close', 'save']);

// Local state
const loading = ref(false);
const error = ref(null);
const apiIndex = ref(-1);
const apiKey = ref(null);
const apiSource = ref(null);
const candlestickChartFailureMessage = ref(null);
const ohlcArray = [];
// Add missing refs for trade excursion
const tradeExcursionId = ref(null);
const tradeExcursionDateUnix = ref(null);
// Local state for tag dropdown
const localShowTagsList = ref(false);
let modal = null;

// Add a cache control function before the defineProps
const tagDataCache = ref({});

// Cache tag data for specific trade ID
function cacheTagData(tradeId, data) {
  if (!tradeId) return;
  tagDataCache.value[tradeId] = {
    data: data,
    timestamp: Date.now()
  };
}

// Get cached tag data if valid (less than 1 minute old)
function getCachedTagData(tradeId) {
  if (!tradeId || !tagDataCache.value[tradeId]) return null;
  
  const cache = tagDataCache.value[tradeId];
  const now = Date.now();
  
  // Cache valid for 1 minute
  if (now - cache.timestamp < 60000) {
    return cache.data;
  }
  
  return null;
}

// Update the loadTagData function to use cache without replacing the original function
async function loadTagData() {
  if (!props.trade || !props.trade.id) return;
  
  const tradeId = props.trade.id;
  
  // Check cache first
  const cachedData = getCachedTagData(tradeId);
  if (cachedData) {
    console.log(`Using cached tag data for trade ${tradeId}`);
    // Use cached data
    return cachedData;
  }
  
  // No valid cache, fetch new data
  try {
    console.log(`Loading tag data for trade ${tradeId}`);
    await useGetTags();
    // Cache the result after fetching
    if (tags.value) {
      cacheTagData(tradeId, tags.value);
    }
    return tags.value;
  } catch (error) {
    console.error("Error loading tag data:", error);
    return null;
  }
}

onMounted(() => {
  // Create Bootstrap modal instance
  setTimeout(() => {
    const modalElement = document.getElementById('standaloneTradeModal');
    if (modalElement && bootstrap.Modal) {
      try {
        // First remove any existing modal-backdrop elements
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
          backdrop.parentNode.removeChild(backdrop);
        });
        
        // Create new modal instance
        modal = new bootstrap.Modal(modalElement, {
          backdrop: true,
          keyboard: true
        });
        
        // Handle modal hidden event
        modalElement.addEventListener('hidden.bs.modal', () => {
          emit('close');
        });
        
        // Show modal if it should be open
        if (props.isOpen) {
          // Make sure body has proper classes
          document.body.classList.add('modal-open');
          
          // Create backdrop manually if needed
          if (document.querySelectorAll('.modal-backdrop').length === 0) {
            const backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop fade show';
            document.body.appendChild(backdrop);
          }
          
          modal.show();
          loadTradeData();
        }
        
        // Setup tag dropdown click outside handler
        setupTagDropdownClickOutside();
      } catch (error) {
        console.error('Error initializing modal:', error);
      }
    } else {
      console.error('Bootstrap Modal not available or modal element not found');
    }
  }, 200);
});

onUnmounted(() => {
  // Clean up any resources
  const modalElement = document.getElementById('standaloneTradeModal');
  if (modalElement) {
    modalElement.removeEventListener('hidden.bs.modal', () => {});
  }
  
  // Clean up tag dropdown click outside handler
  cleanupTagDropdownClickOutside();
});

// Watch for isOpen changes
watch(() => props.isOpen, (newValue) => {
  if (newValue) {
    // Force modal to show when isOpen becomes true
    setTimeout(() => {
      const modalElement = document.getElementById('standaloneTradeModal');
      if (modalElement) {
        if (!modal && bootstrap.Modal) {
          // Create modal if it doesn't exist
          modal = new bootstrap.Modal(modalElement, {
            backdrop: true,
            keyboard: true
          });
          
          // Handle modal hidden event
          modalElement.addEventListener('hidden.bs.modal', () => {
  emit('close');
          });
        }
        
        // Apply direct styles to ensure visibility
        modalElement.style.display = 'block';
        modalElement.classList.add('show');
        modalElement.setAttribute('aria-modal', 'true');
        modalElement.removeAttribute('aria-hidden');
        
        // Add backdrop if needed
        if (document.querySelectorAll('.modal-backdrop').length === 0) {
          const backdrop = document.createElement('div');
          backdrop.className = 'modal-backdrop fade show';
          document.body.appendChild(backdrop);
        }
        
        // Add modal-open class to body
        document.body.classList.add('modal-open');
        document.body.style.overflow = 'hidden';
        document.body.style.paddingRight = '17px'; // Scrollbar width
        
        if (modal) {
          try {
            modal.show();
            loadTradeData();
          } catch (error) {
            console.error('Error showing modal:', error);
            // Still load data even if modal show fails
            loadTradeData();
          }
        } else {
          // Fallback - try using jQuery if available
          try {
            if (window.jQuery) {
              window.jQuery(modalElement).modal('show');
            }
          } catch (error) {
            console.error('Error with jQuery fallback:', error);
          }
          
          // Still load data even if modal show fails
          loadTradeData();
        }
      }
    }, 100);
  } else {
    // Hide modal when isOpen becomes false
    const modalElement = document.getElementById('standaloneTradeModal');
    if (modalElement) {
      // Direct DOM manipulation to hide
      modalElement.style.display = 'none';
      modalElement.classList.remove('show');
      modalElement.setAttribute('aria-hidden', 'true');
      modalElement.removeAttribute('aria-modal');
      
      // Remove backdrop
      document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.parentNode.removeChild(backdrop);
      });
      
      // Remove modal-open class from body
      document.body.classList.remove('modal-open');
      document.body.style.overflow = '';
      document.body.style.paddingRight = '';
    }
    
    if (modal) {
      try {
        modal.hide();
      } catch (error) {
        console.error('Error hiding modal:', error);
      }
    }
  }
});

// Watch for trade changes to ensure tag IDs are always current
watch(() => props.trade, (newTrade) => {
  if (newTrade && newTrade.id && props.dateUnix) {
    tradeTagsId.value = newTrade.id;
    tradeTagsDateUnix.value = props.dateUnix;
    console.log("Updated tag IDs from watch:", tradeTagsId.value, tradeTagsDateUnix.value);
  }
}, { immediate: true });

// Load trade data asynchronously
async function loadTradeData() {
  if (!props.trade) return;
  
  loading.value = true;
  error.value = null;
  
  try {
    // Reset state first
    resetExcursion();
    await useResetTags();
    tradeNoteChanged.value = false;
    tradeExcursionChanged.value = false;
    tradeScreenshotChanged.value = false;
    tradeTagsChanged.value = false;
    showTagsList.value = false;
    
    // Load API providers
    apiIndex.value = -1;
    let databentoIndex = apis.findIndex(obj => obj.provider === "databento");
    let polygonIndex = apis.findIndex(obj => obj.provider === "polygon");

    if (databentoIndex > -1 && apis[databentoIndex].key !== "") {
      apiIndex.value = databentoIndex;
      apiSource.value = "databento";
    } else if (polygonIndex > -1 && apis[polygonIndex].key !== "") {
      apiIndex.value = polygonIndex;
      apiSource.value = "polygon";
    }
    
    // Process data
    await processTradeData();
    
    // Initialize tooltips and other UI elements
    await nextTick();
    
  } catch (err) {
    console.error('Error loading trade data:', err);
    error.value = 'Failed to load trade data';
  } finally {
    loading.value = false;
  }
}

// Process the current trade data
async function processTradeData() {
  if (!props.trade) return;
  
  const tradeId = props.trade.id;
  console.log("Processing trade data for trade ID:", tradeId);
  console.log("Trade date:", props.dateUnix);
  
  // Set trade ID and date for both excursion and tags updates right away
  if (props.trade && props.trade.id && props.dateUnix) {
    // For excursion
    tradeExcursionId.value = props.trade.id;
    tradeExcursionDateUnix.value = props.dateUnix;
    console.log("Set excursion ID:", tradeExcursionId.value);
    console.log("Set excursion date:", tradeExcursionDateUnix.value);
    
    // For tags - IMPORTANT: These values are needed for tag updates
    tradeTagsId.value = props.trade.id;
    tradeTagsDateUnix.value = props.dateUnix;
    console.log("Set tags ID:", tradeTagsId.value);
    console.log("Set tags date:", tradeTagsDateUnix.value);
  }
  
  // Look up screenshot
  let findScreenshot = null;
  if (screenshots && screenshots.length > 0) {
    findScreenshot = screenshots.find(s => s.name === tradeId);
  }
  
  for (let key in screenshot) delete screenshot[key];
  candlestickChartFailureMessage.value = null;

  if (findScreenshot) {
    // Use existing screenshot
    Object.assign(screenshot, findScreenshot);
  } else {
    // No screenshot - set defaults and try to load chart data
    screenshot.side = null;
    screenshot.type = null;
    
    // Load chart data in the background
    setTimeout(() => {
      loadChartData(props.trade);
    }, 100);
  }
  
  // Process trade tags
  console.log("Processing trade tags...");
  const findTags = tags.find(obj => obj.tradeId === tradeId);
  console.log("Found tags for this trade:", findTags);
  tradeTags.length = 0;
  if (findTags) {
    console.log("Tag IDs to process:", findTags.tags);
    findTags.tags.forEach(element => {
      for (let obj of availableTags) {
        for (let tag of obj.tags) {
          if (tag.id === element) {
            tradeTags.push({ id: tag.id, name: tag.name });
            console.log("Added tag to tradeTags:", tag.name);
          }
        }
      }
    });
  }
  console.log("Final tradeTags:", JSON.stringify(tradeTags));
  
  // Process notes
  const noteIndex = notes.findIndex(obj => obj.tradeId === tradeId);
  tradeNote.value = noteIndex !== -1 ? notes[noteIndex].note : null;
  
  // Process excursion data
  const findExcursion = excursions.filter(obj => obj.tradeId === tradeId);
  if (findExcursion.length) {
    if (findExcursion[0].stopLoss != null) excursion.stopLoss = findExcursion[0].stopLoss;
    if (findExcursion[0].maePrice != null) excursion.maePrice = findExcursion[0].maePrice;
    if (findExcursion[0].mfePrice != null) excursion.mfePrice = findExcursion[0].mfePrice;
  }
  
  // Reset UI state
  tagInput.value = '';
  saveButton.value = false;
  
  // Initialize tooltips and UI elements after a short delay to ensure DOM is ready
  setTimeout(async () => {
    try {
      await useInitTooltip();
      
      // Ensure form fields are properly activated
      const mfeInput = document.querySelector('input[placeholder="MFE Price"]');
      if (mfeInput) {
        mfeInput.disabled = false;
        mfeInput.focus();
        mfeInput.blur();
      }
      
      const tagInputEl = document.querySelector('.tag-input');
      if (tagInputEl) {
        tagInputEl.disabled = false;
        tagInputEl.focus();
        tagInputEl.blur();
      }
      
      const noteTextarea = document.querySelector('#floatingTextarea');
      if (noteTextarea) {
        noteTextarea.disabled = false;
        noteTextarea.focus();
        noteTextarea.blur();
      }
    } catch (err) {
      console.error("Error initializing UI elements:", err);
    }
  }, 300);
}

// Add these methods after the processTradeData method
function handleTagRemove(index) {
  if (props.trade && props.trade.id && props.dateUnix) {
    tradeTagsId.value = props.trade.id;
    tradeTagsDateUnix.value = props.dateUnix;
  }
  useTradeTagsChange('remove', index);
}

function handleTagAdd() {
  if (props.trade && props.trade.id && props.dateUnix) {
    tradeTagsId.value = props.trade.id;
    tradeTagsDateUnix.value = props.dateUnix;
  }
  useTradeTagsChange('add', tagInput.value);
}

function handleTagAddFromDropdown(suggestion) {
  if (props.trade && props.trade.id && props.dateUnix) {
    tradeTagsId.value = props.trade.id;
    tradeTagsDateUnix.value = props.dateUnix;
  }
  useTradeTagsChange('addFromDropdownMenu', suggestion);
  localShowTagsList.value = false;
}

// Load and process chart data
async function loadChartData(trade) {
  if (!trade || apiIndex.value === -1) {
    candlestickChartFailureMessage.value = "Missing API Key. To see your entry and exit on a chart, insert your API key in settings.";
    return;
  }
  
  apiKey.value = apis[apiIndex.value].key;
  
  try {
    // Check for special conditions
    if (trade.type === "future" && 
        (apiIndex.value === -1 || apis[apiIndex.value].provider !== "databento" || !apis[apiIndex.value].key)) {
      candlestickChartFailureMessage.value = "You need a Databento API for Futures.";
      return;
    }
    
    if (!apiKey.value) {
      candlestickChartFailureMessage.value = "Missing API Key. To see your entry and exit on a chart, insert your API key in settings.";
      return;
    }
    
    // Get OHLC data
    let ohlcTimestamps, ohlcPrices, ohlcVolumes;
    const existingDataIndex = ohlcArray.findIndex(obj => obj.date === trade.td && obj.symbol === trade.symbol);
    
    if (existingDataIndex !== -1) {
      // Use existing data
      const data = ohlcArray[existingDataIndex];
      ohlcTimestamps = data.ohlcTimestamps;
      ohlcPrices = data.ohlcPrices;
      ohlcVolumes = data.ohlcVolumes;
    } else {
      // Fetch new data
      await getOHLC(trade.td, trade.symbol, trade.type);
      const newDataIndex = ohlcArray.findIndex(obj => obj.date === trade.td && obj.symbol === trade.symbol);
      
      if (newDataIndex !== -1) {
        const data = ohlcArray[newDataIndex];
        ohlcTimestamps = data.ohlcTimestamps;
        ohlcPrices = data.ohlcPrices;
        ohlcVolumes = data.ohlcVolumes;
      }
    }
    
    // Render chart if data was loaded
    if (ohlcTimestamps && ohlcPrices && ohlcVolumes) {
      await useCandlestickChart(ohlcTimestamps, ohlcPrices, ohlcVolumes, trade, true);
    }
  } catch (error) {
    if (error.response && error.response.status === 429) {
      candlestickChartFailureMessage.value = "Too many requests, try again later";
    } else if (error.response) {
      candlestickChartFailureMessage.value = error.response.statusText;
    } else {
      candlestickChartFailureMessage.value = "Error loading chart data";
    }
    console.error("Chart error:", error);
  }
}

// Get OHLC data from API
async function getOHLC(date, symbol, type) {
  if (apiSource.value === "databento") {
    return getOHLCFromDatabento(date, symbol, type);
  } else if (apiSource.value === "polygon") {
    return getOHLCFromPolygon(date, symbol, type);
  }
  return Promise.reject("No valid API source");
}

// Get OHLC data from Databento
async function getOHLCFromDatabento(date, symbol, type) {
  try {
    let temp = { symbol };
    let databentoSymbol = symbol;
    let stype_in = "raw_symbol";
    let toDate = dayjs(date * 1000).tz(timeZoneTrade.value).endOf('day').unix();
    let dataset;
    
    if (type === "future") {
      dataset = "GLBX.MDP3";
      databentoSymbol = `${symbol}.c.0`;
      stype_in = "continuous";
    } else if (type === "stock") {
      dataset = "XNAS.ITCH";
    }
    
    const data = {
      'dataset': dataset,
      'stype_in': stype_in,
      'symbols': databentoSymbol,
      'schema': 'ohlcv-1m',
      'start': date * 1000000000,
      'end': toDate * 1000000000,
      'encoding': 'csv',
      'pretty_px': 'true',
      'pretty_ts': 'true',
      'map_symbols': 'true',
      'username': apiKey.value
    };
    
    const response = await axios.post('/api/databento', data);
    const res = await useCreateOHLCV(response.data, temp);
    
    // Create formatted array for charts
    const tempArray = {
      date,
      symbol,
      ohlcTimestamps: [],
      ohlcPrices: [],
      ohlcVolumes: []
    };
    
    for (let i = 0; i < res.ohlcv.length; i++) {
      const element = res.ohlcv[i];
      
      tempArray.ohlcTimestamps.push(element.t);
      tempArray.ohlcPrices.push([element.c, element.o, element.l, element.h]);
      tempArray.ohlcVolumes.push(element.v);
    }
    
    ohlcArray.push(tempArray);
    return tempArray;
  } catch (error) {
    console.error("Error in Databento API:", error);
    throw error;
  }
}

// Get OHLC data from Polygon
async function getOHLCFromPolygon(date, symbol, type) {
  try {
    let ticker;
    
    if (type === "put" || type === "call" || type === "option") {
      ticker = "O:" + symbol;
    } else if (type === "future") {
      ticker = "I:" + symbol;
    } else if (type === "forex") {
      ticker = "C:" + symbol;
    } else if (type === "crypto") {
      ticker = "X:" + symbol;
    } else {
      ticker = symbol;
    }
    
    const formattedDate = useDateCalFormat(date);
    const url = `https://api.polygon.io/v2/aggs/ticker/${ticker}/range/1/minute/${formattedDate}/${formattedDate}?adjusted=true&sort=asc&limit=50000&apiKey=${apiKey.value}`;
    
    const response = await axios.get(url);
    
    // Create formatted array for charts
    const tempArray = {
      date,
      symbol,
      ohlcTimestamps: [],
      ohlcPrices: [],
      ohlcVolumes: []
    };
    
    for (const element of response.data.results) {
      tempArray.ohlcTimestamps.push(element.t);
      tempArray.ohlcPrices.push([element.c, element.o, element.l, element.h]);
      tempArray.ohlcVolumes.push(element.v);
    }
    
    ohlcArray.push(tempArray);
    return tempArray;
  } catch (error) {
    console.error("Error in Polygon API:", error);
    throw error;
  }
}

// Reset excursion data
function resetExcursion() {
  for (let key in excursion) delete excursion[key];
  excursion.stopLoss = null;
  excursion.maePrice = null;
  excursion.mfePrice = null;
}

// Handle excursion change
function tradeExcursionClicked() {
  tradeExcursionChanged.value = true;
  saveButton.value = true;
}

function tradeExcursionChange(param1, param2) {
  if (param2 === "stopLoss") {
    excursion.stopLoss = param1 ? parseFloat(param1) : null;
  } else if (param2 === "maePrice") {
    excursion.maePrice = parseFloat(param1);
  } else if (param2 === "mfePrice") {
    excursion.mfePrice = parseFloat(param1);
  }
  
  // Set the trade ID and date for excursion updates
  if (props.trade && props.trade.id && props.dateUnix) {
    tradeExcursionId.value = props.trade.id;
    tradeExcursionDateUnix.value = props.dateUnix;
    tradeExcursionChanged.value = true;
    saveButton.value = true;
  }
}

// Handle note change
function tradeNoteChange(param) {
  tradeNote.value = param;
  tradeNoteChanged.value = true;
  saveButton.value = true;
}

// Save changes and close modal
async function saveAndClose() {
  spinnerSetups.value = true;
  
  try {
    // Save any pending changes
    if (tradeNoteChanged.value) {
      console.log("Saving note changes...");
      await useUpdateNote();
      await useGetNotes();
      console.log("Note changes saved successfully");
    }
    
    if (tradeExcursionChanged.value) {
      console.log("Saving excursion changes...");
      // Add tradeExcursionId and tradeExcursionDateUnix values if needed
      if (tradeExcursionId.value && tradeExcursionDateUnix.value) {
        // Update excursion in the database using the API
        try {
          const excursionData = {
            tradeId: tradeExcursionId.value,
            dateUnix: tradeExcursionDateUnix.value,
            ...excursion
          };
          
          console.log("Excursion data to save:", excursionData);
          await axios.post('/api/updateExcursion', excursionData);
          console.log("Excursion saved successfully");
          
          // Refresh excursions data
          await useGetExcursions();
        } catch (error) {
          console.error("Failed to update excursion:", error);
        }
      }
    }
    
    if (tradeTagsChanged.value) {
      console.log("Saving tag changes...");
      console.log("Current tradeTags:", JSON.stringify(tradeTags));
      
      // CRITICAL: Always ensure we have the correct trade ID and date for tag updates
      if (props.trade && props.trade.id && props.dateUnix) {
        tradeTagsId.value = props.trade.id;
        tradeTagsDateUnix.value = props.dateUnix;
        console.log("Ensuring correct tradeTagsId:", tradeTagsId.value);
        console.log("Ensuring correct tradeTagsDateUnix:", tradeTagsDateUnix.value);
      } else {
        console.error("Missing trade ID or date for tag updates!");
      }
      
      // Now save tags with the correct IDs
      await Promise.all([useUpdateAvailableTags(), useUpdateTags()]);
      
      // Refresh tag data
      await Promise.all([useGetTags(), useGetAvailableTags()]);
      useCreateAvailableTagsArray();
      console.log("Tag changes saved successfully");
    }
    
    if (tradeScreenshotChanged.value) {
      console.log("Saving screenshot changes...");
      await useSaveScreenshot();
      console.log("Screenshot changes saved successfully");
    }
    
    // Reset flags
    tradeNoteChanged.value = false;
    tradeExcursionChanged.value = false;
    tradeScreenshotChanged.value = false;
    tradeTagsChanged.value = false;
    showTagsList.value = false;
    
    // Close the modal
    if (modal) {
      try {
        modal.hide();
      } catch (error) {
        console.error('Error hiding modal:', error);
        // Fallback - emit save event directly
        emit('save');
      }
    } else {
      // No modal instance, just emit save
      emit('save');
    }
  } catch (error) {
    console.error("Error saving changes:", error);
    // Still close the modal even if there's an error
    if (modal) {
      try {
        modal.hide();
      } catch (modalError) {
        console.error('Error hiding modal:', modalError);
      }
    }
    emit('save');
  } finally {
    spinnerSetups.value = false;
  }
}

// Cancel and close modal without saving
function cancel() {
  // Reset flags
  tradeNoteChanged.value = false;
  tradeExcursionChanged.value = false;
  tradeScreenshotChanged.value = false;
  tradeTagsChanged.value = false;
  
  // Close modal
  if (modal) {
    try {
      modal.hide();
    } catch (error) {
      console.error('Error hiding modal:', error);
      // Fallback - emit close event directly
      emit('close');
    }
  } else {
    // No modal instance, just emit close
    emit('close');
  }
}

// Handle satisfaction change
function tradeSatisfactionChange(trade, value) {
  if (!trade) return;
  
  trade.satisfaction = value;
  useDailySatisfactionChange(trade.id, trade.td, value);
}

// Toggle tag dropdown
function toggleTagDropdown() {
  localShowTagsList.value = !localShowTagsList.value;
}

// Close tag dropdown when clicking outside
function setupTagDropdownClickOutside() {
  document.addEventListener('click', handleClickOutside);
}

function cleanupTagDropdownClickOutside() {
  document.removeEventListener('click', handleClickOutside);
}

function handleClickOutside(event) {
  const tagContainer = document.querySelector('.tag-container');
  const dropdown = document.querySelector('.dropdown-menu-tags');
  
  if (tagContainer && dropdown && localShowTagsList.value && 
      !tagContainer.contains(event.target) && 
      !dropdown.contains(event.target)) {
    localShowTagsList.value = false;
  }
}

// Helper function to check if there are any visible tags
function hasVisibleTags() {
  for (const group of availableTags) {
    const filteredGroup = useFilterSuggestions(group.id).filter(obj => obj.id === group.id)[0];
    if (filteredGroup && filteredGroup.tags && filteredGroup.tags.length > 0) {
      return true;
    }
  }
  return false;
}
</script>

<template>
  <!-- Standalone Trade Modal -->
  <teleport to="body">
    <div class="modal fade" id="standaloneTradeModal" tabindex="-1" aria-labelledby="tradeModalLabel" aria-hidden="true">
      <div class="modal-dialog modal-xl">
    <div class="modal-content">
      <div class="modal-header">
            <h5 class="modal-title" id="tradeModalLabel">Trade Details</h5>
            <button type="button" class="btn-close" @click="cancel" aria-label="Close"></button>
      </div>
            
      <div class="modal-body">
            <!-- Loading indicator -->
            <div v-if="loading" class="text-center p-4">
              <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
              </div>
              <p class="mt-2">Loading trade data...</p>
            </div>
            
            <!-- Error message -->
            <div v-if="error" class="alert alert-danger" role="alert">
              {{ error }}
              <button type="button" class="btn-close float-end" @click="error = null" aria-label="Close"></button>
            </div>
            
            <!-- Trade content -->
            <div v-if="trade && !loading">
              <!-- Screenshot or chart -->
              <div v-if="screenshot.originalBase64">
                <Screenshot :screenshot-data="screenshot" source="dailyModal" />
              </div>
              <div v-show="!candlestickChartFailureMessage && !screenshot.originalBase64" id="candlestickChart" class="candlestickClass">
              </div>
              <div class="container mt-2 text-center" v-show="candlestickChartFailureMessage">
                {{ candlestickChartFailureMessage }}
              </div>

              <!-- Trade details table -->
              <div class="mt-3 table-responsive">
                <table class="table">
            <thead>
              <tr>
                      <th scope="col">Symbol</th>
                      <th scope="col">Vol</th>
                      <th scope="col">Position</th>
                      <th scope="col">Entry</th>
                      <th scope="col">Price</th>
                      <th scope="col">Exit</th>
                      <th scope="col">Price</th>
                      <th scope="col">Duration</th>
                      <th scope="col">P&L/Vol</th>
                      <th scope="col">P/L(n)</th>
              </tr>
            </thead>
            <tbody>
                    <tr>
                <td>{{ trade.symbol }}</td>
                      <td>{{ trade.buyQuantity + trade.sellQuantity }}</td>
                      <td>{{ trade.side === 'B' ? 'Long' : 'Short' }}</td>
                      
                      <!-- Entry -->
                      <td>
                        <span v-if="trade.tradesCount === 0">
                          <span v-if="trade.openPosition">
                            Open<i class="ps-1 uil uil-info-circle" data-bs-toggle="tooltip" data-bs-html="true"
                               :data-bs-title="'Swing trade opened on ' + useDateCalFormat(trade.entryTime)"></i>
                          </span>
                          <span v-else>
                            Closed<i class="ps-1 uil uil-info-circle" data-bs-toggle="tooltip" data-bs-html="true"
                                 :data-bs-title="'Swing trade closed on ' + useDateCalFormat(trade.exitTime)"></i>
                          </span>
                        </span>
                        <span v-else>
                          {{ useTimeFormat(trade.entryTime) }}
                        </span>
                      </td>
                      
                      <!-- Entry Price -->
                      <td>
                        <span v-if="trade.tradesCount === 0"></span>
                        <span v-else-if="trade.type === 'forex'">
                          {{ (trade.entryPrice).toFixed(5) }}
                        </span>
                        <span v-else>
                          {{ useTwoDecCurrencyFormat(trade.entryPrice) }}
                        </span>
                      </td>
                      
                      <!-- Exit -->
                      <td>
                        <span v-if="trade.tradesCount === 0"></span>
                        <span v-else>{{ useTimeFormat(trade.exitTime) }}</span>
                      </td>
                      
                      <!-- Exit Price -->
                      <td>
                        <span v-if="trade.tradesCount === 0"></span>
                        <span v-else-if="trade.type === 'forex'">
                          {{ (trade.exitPrice).toFixed(5) }}
                        </span>
                        <span v-else>
                          {{ useTwoDecCurrencyFormat(trade.exitPrice) }}
                        </span>
                      </td>
                      
                      <!-- Duration -->
                      <td>
                        <span v-if="trade.tradesCount === 0"></span>
                        <span v-else>
                          {{ useTimeDuration(trade.exitTime - trade.entryTime) }}
                        </span>
                      </td>
                      
                      <!-- P&L/Vol -->
                      <td>
                        <span v-if="trade.tradesCount === 0"></span>
                        <span v-else-if="trade.type === 'forex'"></span>
                        <span v-else :class="[(trade.grossSharePL) > 0 ? 'greenTrade' : 'redTrade']">
                          {{ useTwoDecCurrencyFormat(trade.grossSharePL) }}
                        </span>
                      </td>
                      
                      <!-- P&L -->
                      <td>
                        <span v-if="trade.tradesCount === 0"></span>
                        <span v-else :class="[trade.netProceeds > 0 ? 'greenTrade' : 'redTrade']">
                          {{ useTwoDecCurrencyFormat(trade.netProceeds) }}
                        </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
              
              <!-- Trade inputs -->
              <div class="mt-1 mb-2 row align-items-center ms-1 me-1 tradeSetup">
                <div class="col-12" v-show="!spinnerSetups">
                  <div class="row align-items-center">
                    <!-- Satisfaction -->
                    <div class="col-1">
                      <i @click="tradeSatisfactionChange(trade, true)"
                         :class="[trade.satisfaction === true ? 'greenTrade' : '', 'uil', 'uil-thumbs-up', 'pointerClass', 'me-1']"></i>
                      <i @click="tradeSatisfactionChange(trade, false)"
                         :class="[trade.satisfaction === false ? 'redTrade' : '', 'uil', 'uil-thumbs-down', 'pointerClass']"></i>
                    </div>
                    
                    <!-- Tags -->
                    <div class="container-tags col-8">
                      <div class="tag-container form-control dropdown form-select" style="height: auto;">
                        <div style="display: flex; align-items: center; flex-wrap: wrap;">
                          <span v-for="(tag, index) in tradeTags" :key="index"
                                class="tag txt-small"
                                :style="{ 'background-color': useGetTagInfo(tag.id).groupColor }"
                                @click="handleTagRemove(index)">
                            {{ tag.name }}<span class="remove-tag">×</span>
                          </span>
                          
                          <input type="text" v-model="tagInput" 
                                 @input="useFilterTags"
                                 @keydown.enter.prevent="handleTagAdd"
                                 @keydown.tab.prevent="handleTagAdd"
                                 @focus="localShowTagsList = true"
                                 class="form-control tag-input" 
                                 placeholder="Add a tag"
                                 :disabled="false">
                          <div class="clickable-area" @click="toggleTagDropdown">
                            <i class="uil uil-angle-down"></i>
                          </div>
                        </div>
                      </div>
                      
                      <ul class="dropdown-menu-tags" 
                          :style="{ display: localShowTagsList ? 'block' : 'none' }">
                        <span v-for="group in availableTags" :key="group.id">
                          <h6 class="p-1 mb-0"
                              :style="'background-color: ' + group.color + ';'"
                              v-show="useFilterSuggestions(group.id).filter(obj => obj.id == group.id)[0].tags.length > 0">
                            {{ group.name }}
                          </h6>
                          <li v-for="(suggestion, index) in useFilterSuggestions(group.id).filter(obj => obj.id == group.id)[0].tags"
                              :key="index" 
                              :class="{ active: index === selectedTagIndex }"
                              @click="handleTagAddFromDropdown(suggestion)"
                              class="dropdown-item dropdown-item-tags">
                            <span class="ms-2">{{ suggestion.name }}</span>
                          </li>
                        </span>
                        <!-- No results message -->
                        <li v-if="!hasVisibleTags()" class="no-results-message">
                          <span v-if="tagInput && tagInput.trim().length > 0">
                            No matching tags found. Press Enter to create "{{ tagInput }}".
                          </span>
                          <span v-else>No tags available</span>
                        </li>
                      </ul>
                    </div>
                    
                    <!-- MFE -->
                    <div class="col-3">
                      <input type="number" class="form-control" placeholder="MFE Price"
                             style="font-size: small;" v-bind:value="excursion.mfePrice"
                             @click="tradeExcursionClicked"
                             @change="tradeExcursionChange($event.target.value, 'mfePrice')"
                             :disabled="false">
                    </div>
                  </div>
                </div>
                
                <!-- Notes -->
                <div class="col-12 mt-2" v-show="!spinnerSetups">
                  <textarea class="form-control" placeholder="note" id="floatingTextarea"
                           v-bind:value="tradeNote"
                           @input="tradeNoteChange($event.target.value)"
                           :disabled="false"></textarea>
                </div>
                
                <!-- File upload -->
                <div class="col-12 mt-3" v-show="!spinnerSetups">
                  <input class="screenshotFile" type="file"
                         @change="useSetupImageUpload($event, trade.entryTime, trade.symbol, trade.side)"
                         :disabled="false" />
                </div>
                
                <!-- Loading spinner -->
                <div v-show="spinnerSetups" class="col-12">
                  <div class="d-flex justify-content-center">
                    <div class="spinner-border spinner-border-sm text-blue" role="status"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="cancel">
              Cancel
            </button>
            <button type="button" class="btn btn-primary" @click="saveAndClose" :disabled="loading">
              {{ saveButton ? 'Save Changes' : 'Close' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<style scoped>
.modal {
  z-index: 9999 !important;
  position: fixed !important;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.modal-backdrop {
  z-index: 9998 !important;
  opacity: 0.7 !important;
  background-color: #000 !important;
}

.modal-dialog {
  max-width: 80%;
  margin: 1.75rem auto;
  z-index: 10000 !important;
}

.modal-content {
  background-color: #1e1e2f;
  color: #e0e0e0;
  border-radius: 12px;
  border: none;
  box-shadow: 0 5px 25px rgba(0, 0, 0, 0.7);
  position: relative;
  z-index: 10001 !important;
}

.modal-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background-color: #252539;
}

.modal-footer {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.candlestickClass {
  width: 100%;
  height: 400px;
}

.form-control {
  background-color: #2a2a4a;
  color: #e0e0e0;
  border: 1px solid rgba(255, 255, 255, 0.1);
  opacity: 1 !important;
}

.form-control::placeholder {
  color: #a0a0a0;
  opacity: 0.8;
}

.form-control:focus {
  background-color: #3a3a5a;
  color: #ffffff;
  border-color: #6a8dff;
  box-shadow: 0 0 0 0.2rem rgba(106, 141, 255, 0.25);
}

/* Ensure inputs don't appear disabled */
input, textarea, select {
  opacity: 1 !important;
}

input::placeholder, textarea::placeholder {
  opacity: 0.7;
}

.tag-input {
  border: none;
  outline: none;
  flex-grow: 1;
  min-width: 50px;
  background-color: transparent;
  opacity: 1 !important;
}

.pointerClass {
  cursor: pointer;
}

.greenTrade {
  color: #4caf50 !important;
}

.redTrade {
  color: #ff6b6b !important;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 20px;
  margin-right: 6px;
  margin-bottom: 6px;
  color: white;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.tag:hover {
  transform: translateY(-1px);
}

.remove-tag {
  margin-left: 6px;
  font-size: 1.1rem;
  font-weight: bold;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.remove-tag:hover {
  opacity: 1;
}

.container-tags {
  position: relative;
  z-index: 10500;
}

.tag-container {
  background-color: #2a2a4a;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  padding: 8px;
  min-height: 42px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.tag-container:focus-within {
  border-color: #6a8dff;
  box-shadow: 0 0 0 0.2rem rgba(106, 141, 255, 0.25);
}

.dropdown-menu-tags {
  position: absolute;
  top: calc(100% + 5px);
  left: 0;
  z-index: 10500;
  width: 100%;
  max-height: 250px;
  overflow-y: auto;
  background-color: #2a2a4a;
  border: 1px solid rgba(106, 141, 255, 0.3);
  border-radius: 6px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  padding: 8px;
  margin-top: 2px;
  animation: fadeIn 0.2s ease-in-out;
  scrollbar-width: thin;
  scrollbar-color: #6a8dff #2a2a4a;
}

.dropdown-menu-tags::-webkit-scrollbar {
  width: 6px;
}

.dropdown-menu-tags::-webkit-scrollbar-track {
  background: #2a2a4a;
  border-radius: 3px;
}

.dropdown-menu-tags::-webkit-scrollbar-thumb {
  background-color: #6a8dff;
  border-radius: 3px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}

.dropdown-item-tags {
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.15s ease;
  margin-bottom: 2px;
  list-style-type: none;
}

.dropdown-item-tags:hover {
  background-color: #3a3a5a;
}

.dropdown-item-tags.active {
  background-color: #6a8dff;
  color: white;
}

.no-results-message {
  padding: 10px;
  text-align: center;
  color: #a0a0a0;
  font-size: 0.9rem;
  list-style-type: none;
}

.clickable-area {
  cursor: pointer;
  padding: 5px 8px;
  margin-left: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(106, 141, 255, 0.15);
  border-radius: 4px;
  transition: all 0.2s ease;
}

.clickable-area:hover {
  background-color: rgba(106, 141, 255, 0.3);
}

.clickable-area i {
  font-size: 1.1rem;
  color: #6a8dff;
}

/* Button styling */
.btn-primary {
  background-color: #6a8dff;
  border-color: #6a8dff;
}

.btn-primary:hover {
  background-color: #5a7ce0;
  border-color: #5a7ce0;
}

.btn-secondary {
  background-color: #3a3a5a;
  border-color: #3a3a5a;
}

.btn-secondary:hover {
  background-color: #4a4a6a;
  border-color: #4a4a6a;
}

table {
  background-color: #252539;
  border-radius: 8px;
}

table th {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
</style> 