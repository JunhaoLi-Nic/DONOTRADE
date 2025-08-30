<script setup>
import { onBeforeMount, onMounted, computed, reactive, ref, watch, nextTick, onBeforeUnmount } from 'vue';
import Filters from '../components/Filters.vue'
import NoData from '../components/NoData.vue';
import SpinnerLoadingPage from '../components/SpinnerLoadingPage.vue';
import Calendar from '../components/Calendar.vue'
import Screenshot from '../components/Screenshot.vue'
import OrderLinkPopup from '../components/OrderLinkPopup.vue'
import TradeDetailsModal from '../components/TradeDetailsModal.vue';

import { spinnerLoadingPage, calendarData, filteredTrades, screenshots, diaries, modalDailyTradeOpen, amountCase, markerAreaOpen, screenshot, tradeScreenshotChanged, excursion, tradeExcursionChanged, spinnerSetups, spinnerSetupsText, tradeExcursionId, tradeExcursionDateUnix, hasData, tradeId, excursions, saveButton, itemTradeIndex, tradeIndex, tradeIndexPrevious, spinnerLoadMore, endOfList, selectedGrossNet, availableTags, tradeTagsChanged, tagInput, tags, tradeTags, showTagsList, selectedTagIndex, tradeTagsId, tradeTagsDateUnix, newTradeTags, notes, tradeNote, tradeNoteChanged, tradeNoteDateUnix, tradeNoteId, availableTagsArray, timeZoneTrade, screenshotsInfos, idCurrentType, idCurrentNumber, tabGettingScreenshots, currentUser, apis, satisfactionTradeArray, satisfactionArray, dailyPageMounted } from '../stores/globals';

import { useCreatedDateFormat, useTwoDecCurrencyFormat, useTimeFormat, useTimeDuration, useMountDaily, useGetSelectedRange, useLoadMore, useCheckVisibleScreen, useDecimalsArithmetic, useInitTooltip, useDateCalFormat, useSwingDuration, useStartOfDay, useInitTab } from '../utils/utils';

import { useSetupImageUpload, useSaveScreenshot, useGetScreenshots } from '../utils/screenshots';

import { useGetExcursions, useGetTags, useGetAvailableTags, useUpdateAvailableTags, useUpdateTags, useFindHighestIdNumber, useFindHighestIdNumberTradeTags, useUpdateNote, useGetNotes, useGetTagInfo, useCreateAvailableTagsArray, useFilterSuggestions, useTradeTagsChange, useFilterTags, useToggleTagsDropdown, useResetTags, useDailySatisfactionChange } from '../utils/daily';

import { useCandlestickChart, useRenderDoubleLineChart, useRenderPieChart } from '../utils/charts';

import { useGetMFEPrices } from '../utils/addTrades';

// Import OrderSyncService for fetching orders
import orderSyncService from '../services/orderSyncService';

/* MODULES */
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc.js'
dayjs.extend(utc)
import isoWeek from 'dayjs/plugin/isoWeek.js'
dayjs.extend(isoWeek)
import timezone from 'dayjs/plugin/timezone.js'
dayjs.extend(timezone)
import duration from 'dayjs/plugin/duration.js'
dayjs.extend(duration)
import updateLocale from 'dayjs/plugin/updateLocale.js'
dayjs.extend(updateLocale)
import localizedFormat from 'dayjs/plugin/localizedFormat.js'
dayjs.extend(localizedFormat)
import customParseFormat from 'dayjs/plugin/customParseFormat.js'
dayjs.extend(customParseFormat)
import axios from 'axios'
import { useCreateOHLCV } from '../utils/addTrades';

// Store MongoDB orders
const mongoDbOrders = ref([]);
// Track linked orders by trade ID
const linkedOrders = reactive({});
// Track which trades are currently showing the dropdown
const showOrderDropdown = reactive({});
// Track if we're loading orders
const loadingOrders = ref(false);
// State for the popup
const showOrderPopup = ref(false);
const currentTradeForPopup = ref(null);
const currentSymbolForPopup = ref('');

// In the data section, add state for managing the standalone modal
// Replace the existing modal-related state with these
const showStandaloneModal = ref(false);
const currentTradeData = ref(null);
const currentTradeIndex = ref(null);
const currentItemTradeIndex = ref(null);
const currentDateUnix = ref(null);

const dailyTabs = [{
    id: "trades",
    label: "Trades",
    target: "#tradesNav"
},
{
    id: "blotter",
    label: "Blotter",
    target: "#blotterNav"
},
{
    id: "screenshots",
    label: "Screenshots",
    target: "#screenshotsNav"
},
{
    id: "diaries",
    label: "Diary",
    target: "#diariesNav"
},
]

let tradesModal = null
let tagsModal = null

let tradeSatisfactionId
let tradeSatisfaction
let tradeSatisfactionDateUnix


let ohlcArray = [] // array used for charts
let ohlcv = [] // array used for MFE / excursion calculation (same as in addTrades.js)


const candlestickChartFailureMessage = ref(null)
const apiIndex = ref(-1)
const apiKey = ref(null)
const apiSource = ref(null)

onBeforeMount(async () => {
    dailyPageMounted.value = false
})
onMounted(async () => {
    await useMountDaily()
    await useInitTooltip()
    useCreateAvailableTagsArray()

    // Fetch orders from MongoDB
    await fetchMongoDbOrders();

    // Add click handler to close dropdowns when clicking outside
    document.addEventListener('click', closeAllDropdowns);

    tradesModal = new bootstrap.Modal("#tradesModal")
    document.getElementById("tradesModal").addEventListener('shown.bs.modal', async (event) => {
        if (event.relatedTarget && event.relatedTarget.dataset) {
            const index = event.relatedTarget.dataset.index
            const index2 = event.relatedTarget.dataset.indextwo
        clickTradesModal(index, index2, index2)
        }
    })

    // Remove problematic event listeners
    if (document.getElementById("tradesModal").dataset.bsListener) {
        document.getElementById("tradesModal").removeEventListener('hide.bs.modal', null)
    }

    tagsModal = new bootstrap.Modal("#tagsModal")
    document.getElementById("tagsModal").addEventListener('shown.bs.modal', async (event) => {
        if (event.relatedTarget && event.relatedTarget.dataset) {
            const index = event.relatedTarget.dataset.index
        clickTagsModal(index)
        }
    })

    // Remove problematic event listeners
    if (document.getElementById("tagsModal").dataset.bsListener) {
        document.getElementById("tagsModal").removeEventListener('hide.bs.modal', null)
    }
})

// Clean up event listeners when component is unmounted
onBeforeUnmount(() => {
    document.removeEventListener('click', closeAllDropdowns);
})

// Function to close all dropdowns
function closeAllDropdowns() {
    Object.keys(showOrderDropdown).forEach(key => {
        showOrderDropdown[key] = false;
    });
}

// Open the order popup
function toggleOrderPopup(tradeId, symbol, event) {
    console.log('Opening popup for trade:', tradeId, 'with symbol:', symbol);

    // Stop event propagation
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    // Set the current trade and symbol for the popup
    currentTradeForPopup.value = tradeId;
    currentSymbolForPopup.value = symbol;

    // Show the popup
    showOrderPopup.value = true;
}

watch(spinnerLoadingPage, async (isLoading) => {
    // When loading is finished and the spinner is hidden
    if (!isLoading) {
        // Wait for Vue to update the DOM
        await nextTick();
        console.log("DOM updated, attempting to render charts...");

        // Now that the DOM is ready, render the charts
        useRenderDoubleLineChart();
        useRenderPieChart();
    }
});

/**************
 * MODAL INTERACTION
 ***************/
let loadScreenshots = false
let initCandleChart = true // needed to init or not candlestickCharts in useCandlestickChart

async function clickTradesModal(param1, param2, param3) {
  // Case 1: Closing the modal (no parameters provided)
  if (param1 === undefined && param2 === undefined && param3 === undefined) {
    console.log("Closing trades modal");
    
    // First hide the modal UI immediately to unblock the user
    if (tradesModal) {
      tradesModal.hide();
    }
    
    // Reset all state variables
    itemTradeIndex.value = undefined;
    tradeIndexPrevious.value = undefined;
    tradeIndex.value = undefined;
    modalDailyTradeOpen.value = false;
    
    // Reset flags
    tradeNoteChanged.value = false;
    tradeExcursionChanged.value = false;
    tradeScreenshotChanged.value = false;
    tradeTagsChanged.value = false;
    showTagsList.value = false;
    
    // Turn off spinner if it's on
    spinnerSetups.value = false;
    
    // Do cleanup operations separately after modal is closed
    setTimeout(async () => {
      try {
        await useInitTab("daily");
        loadScreenshots = false;
        initCandleChart = true;
        console.log("Modal cleanup complete");
      } catch (error) {
        console.error("Error in modal cleanup:", error);
      }
    }, 100);
    
    return;
  }
  
  // Case 2: Opening or navigating in the modal
  console.log(`Opening/navigating modal: ${param1}, ${param2}, ${param3}`);
  
  try {
    // Check if annotation is active
    if (markerAreaOpen.value === true) {
      alert("Please save your screenshot annotation");
      return;
    }
    
    // Turn on loading spinner
    spinnerSetups.value = true;
    
    // Set basic parameters first to show something to the user
    itemTradeIndex.value = Number(param1);
    tradeIndexPrevious.value = Number(param2);
    tradeIndex.value = Number(param3);
    modalDailyTradeOpen.value = true;
    
    // Process data in the background
    setTimeout(async () => {
      try {
        // Save any pending changes
        if (tradeNoteChanged.value) {
          try {
            await useUpdateNote();
            await useGetNotes();
          } catch (err) {
            console.error("Error updating notes:", err);
          }
        }

        if (tradeExcursionChanged.value) {
          try {
            await updateExcursions();
          } catch (err) {
            console.error("Error updating excursions:", err);
          }
        }

        if (tradeTagsChanged.value) {
          try {
            await Promise.all([
              useUpdateAvailableTags(),
              useUpdateTags()
            ]);
            await Promise.all([
              useGetTags(),
              useGetAvailableTags()
            ]);
            useCreateAvailableTagsArray();
          } catch (err) {
            console.error("Error updating tags:", err);
          }
        }

        if (tradeScreenshotChanged.value) {
          try {
            await useSaveScreenshot();
          } catch (err) {
            console.error("Error saving screenshot:", err);
          }
        }

        // Reset change flags
        tradeNoteChanged.value = false;
        tradeExcursionChanged.value = false;
        tradeScreenshotChanged.value = false;
        tradeTagsChanged.value = false;
        showTagsList.value = false;

        // Process API data
        try {
          apiIndex.value = -1;
          let databentoIndex = apis.findIndex(obj => obj.provider === "databento");
          let polygonIndex = apis.findIndex(obj => obj.provider === "polygon");

            if (databentoIndex > -1 && apis[databentoIndex].key != "") {
            apiIndex.value = databentoIndex;
            apiSource.value = "databento";
            } else if (polygonIndex > -1 && apis[polygonIndex].key != "") {
            apiIndex.value = polygonIndex;
            apiSource.value = "polygon";
            }

                if (loadScreenshots === false) {
            let screenshotsDate = filteredTrades[param1].dateUnix;
                    if (screenshots.length == 0 || (screenshots.length > 0 && screenshots[0].dateUnixDay != screenshotsDate)) {
              await useGetScreenshots(true, screenshotsDate);
            }
            loadScreenshots = true;
          }

          let filteredTradeId = filteredTrades[itemTradeIndex.value].trades[param3].id;
          await Promise.all([resetExcursion(), useResetTags()]);

          // Process screenshot data
          let findScreenshot = screenshots.find(obj => obj.name == filteredTradeId);
          for (let key in screenshot) delete screenshot[key];
          candlestickChartFailureMessage.value = null;

                if (findScreenshot) {
                    for (let key in findScreenshot) {
              screenshot[key] = findScreenshot[key];
                    }
                } else {
            screenshot.side = null;
            screenshot.type = null;

                    if (apiIndex.value != -1) {
              processChartData(filteredTrades[itemTradeIndex.value].trades[param3]);
                            } else {
              candlestickChartFailureMessage.value = "Missing API Key. To see your entry and exist on a chart, insert your API key in settings.";
            }
          }

          // Process tags
          let findTags = tags.find(obj => obj.tradeId == filteredTradeId);
                if (findTags) {
                    findTags.tags.forEach(element => {
                        for (let obj of availableTags) {
                            for (let tag of obj.tags) {
                                if (tag.id === element) {
                    let temp = {};
                    temp.id = tag.id;
                    temp.name = tag.name;
                    tradeTags.push(temp);
                                }
                            }
                        }
                    });
                }

          // Process notes
          let noteIndex = notes.findIndex(obj => obj.tradeId == filteredTradeId);
          tradeNote.value = null;
                if (noteIndex != -1) {
            tradeNote.value = notes[noteIndex].note;
                }

          // Process excursion data
          let findExcursion = excursions.filter(obj => obj.tradeId == filteredTradeId);
                if (findExcursion.length) {
            findExcursion[0].stopLoss != null ? excursion.stopLoss = findExcursion[0].stopLoss : null;
            findExcursion[0].maePrice != null ? excursion.maePrice = findExcursion[0].maePrice : null;
            findExcursion[0].mfePrice != null ? excursion.mfePrice = findExcursion[0].mfePrice : null;
          }
          
          await useInitTooltip();
          tagInput.value = '';
          saveButton.value = false;
        } catch (err) {
          console.error("Error processing trade data:", err);
        }
      } catch (err) {
        console.error("Error in modal background processing:", err);
      } finally {
        // Always turn off spinner
        spinnerSetups.value = false;
      }
    }, 100);
  } catch (error) {
    console.error("Error in clickTradesModal:", error);
    spinnerSetups.value = false;
    
    // Try to recover UI state
    if (tradesModal) {
      tradesModal.hide();
    }
    modalDailyTradeOpen.value = false;
  }
}

// Helper function to process chart data (moved from clickTradesModal)
function processChartData(filteredTradesObject) {
  apiKey.value = apis[apiIndex.value].key;
  
  if (filteredTradesObject.type == "future" && 
     (apiIndex.value === -1 || apis[apiIndex.value].provider !== "databento" || !apis[apiIndex.value].key)) {
    candlestickChartFailureMessage.value = "You need a Databento API for Futures.";
    return;
  } 
  
  if (!apiKey.value) {
    candlestickChartFailureMessage.value = "Missing API Key. To see your entry and exist on a chart, insert your API key in settings.";
    return;
  }
  
  try {
    candlestickChartFailureMessage.value = null;
    
    // Process OHLC data (this is non-blocking and will update when ready)
    setTimeout(async () => {
      try {
        let ohlcTimestamps, ohlcPrices, ohlcVolumes;
        
        if (ohlcArray.length == 0) {
          await getOHLC(filteredTradesObject.td, filteredTradesObject.symbol, filteredTradesObject.type);
          if (ohlcArray.length > 0) {
            ohlcTimestamps = ohlcArray[0].ohlcTimestamps;
            ohlcPrices = ohlcArray[0].ohlcPrices;
            ohlcVolumes = ohlcArray[0].ohlcVolumes;
          }
        } else {
          let index = ohlcArray.findIndex(obj => 
            obj.date == filteredTradesObject.td && obj.symbol == filteredTradesObject.symbol
          );

          if (index != -1) {
            ohlcTimestamps = ohlcArray[index].ohlcTimestamps;
            ohlcPrices = ohlcArray[index].ohlcPrices;
            ohlcVolumes = ohlcArray[index].ohlcVolumes;
          } else {
            await getOHLC(filteredTradesObject.td, filteredTradesObject.symbol, filteredTradesObject.type);
            let index = ohlcArray.findIndex(obj => 
              obj.date === filteredTradesObject.td && obj.symbol === filteredTradesObject.symbol
            );
            
            if (index != -1) {
              ohlcTimestamps = ohlcArray[index].ohlcTimestamps;
              ohlcPrices = ohlcArray[index].ohlcPrices;
              ohlcVolumes = ohlcArray[index].ohlcVolumes;
            }
          }
        }
        
        if (ohlcTimestamps && ohlcPrices && ohlcVolumes) {
          await useCandlestickChart(ohlcTimestamps, ohlcPrices, ohlcVolumes, filteredTradesObject, initCandleChart);
          initCandleChart = false;
        }
      } catch (error) {
        if (error.response && error.response.status === 429) {
          candlestickChartFailureMessage.value = "Too many requests, try again later";
        }
        else if (error.response) {
          candlestickChartFailureMessage.value = error.response.statusText;
        }
        else {
          candlestickChartFailureMessage.value = "Error loading chart data";
        }
        console.error("Chart error:", error);
      }
    }, 300);
  } catch (error) {
    candlestickChartFailureMessage.value = "Error initializing chart";
    console.error(error);
  }
}

const clickTagsModal = (param1) => {
    itemTradeIndex.value = Number(param1)
    tradeTags.length = 0
    let findTags = tags.find(obj => obj.tradeId == filteredTrades[itemTradeIndex.value].dateUnix)
    if (findTags) {
        findTags.tags.forEach(element => {
            for (let obj of availableTags) {
                for (let tag of obj.tags) {
                    if (tag.id === element) {
                        let temp = {}
                        temp.id = tag.id
                        temp.name = tag.name
                        tradeTags.push(temp)
                    }
                }
            }
        });
    }
}

const saveDailyTags = async () => {
    if (tradeTagsChanged.value) {
        await Promise.all([useUpdateAvailableTags(), useUpdateTags()])
        await Promise.all([useGetTags(), useGetAvailableTags()])
    }
    tradeTagsChanged.value = false
    closeTagsModal()
}

const closeTagsModal = async () => {
    tradeTags.length = 0
    tradeTagsChanged.value = false
    if (tagsModal) {
    tagsModal.hide()
    }
}

const checkDate = ((param1, param2) => {
    //console.log("param 1 "+param1)
    //console.log("param 2 "+param2)
    let tdDateUnix = dayjs(param1 * 1000).tz(timeZoneTrade.value)
    let tradeDateUnix = dayjs(param2 * 1000).tz(timeZoneTrade.value)
    let check = tdDateUnix.isSame(tradeDateUnix, 'day')
    return check
})

/**************
 * SATISFACTION
 ***************/

async function dailySatisfactionChange(dateUnix, satisfaction, itemTrade) {
    await useDailySatisfactionChange(null, dateUnix, satisfaction, itemTrade)
}

async function tradeSatisfactionChange(param1, param2) {
    tradeSatisfactionId = param1.id
    tradeSatisfactionDateUnix = param1.td
    tradeSatisfaction = param2
    param1.satisfaction = tradeSatisfaction
    await useDailySatisfactionChange(tradeSatisfactionId, tradeSatisfactionDateUnix, tradeSatisfaction)

}

/**************
 * EXCURSIONS
 ***************/

function tradeExcursionClicked() {
    //console.log("click")
    tradeExcursionChanged.value = true
    saveButton.value = true
}
function tradeExcursionChange(param1, param2) {
    console.log("param 1: " + param1 + " param2: " + param2)
    if (param2 == "stopLoss") {
        if (param1) {
            excursion.stopLoss = parseFloat(param1)
        } else {
            excursion.stopLoss = null
        }

    }
    if (param2 == "maePrice") {
        excursion.maePrice = parseFloat(param1)
    }
    if (param2 == "mfePrice") {
        excursion.mfePrice = parseFloat(param1)
    }
    tradeExcursionDateUnix.value = filteredTrades[itemTradeIndex.value].dateUnix
    tradeExcursionId.value = filteredTrades[itemTradeIndex.value].trades[tradeIndex.value].id
    //console.log("Excursion has changed: " + JSON.stringify(tradeExcursion))

}

/**************
 * MISC
 ***************/

function resetExcursion() {
    //console.log(" -> Resetting excursion")
    //we need to reset the setup variable each time
    for (let key in excursion) delete excursion[key]
    excursion.stopLoss = null
    excursion.maePrice = null
    excursion.mfePrice = null
}

/**************
 * TAGS
 ***************/


/**************
 * NOTES
 ***************/

const tradeNoteChange = (param) => {
    tradeNote.value = param
    //console.log(" -> New note " + tradeNote.value)
    tradeNoteDateUnix.value = filteredTrades[itemTradeIndex.value].dateUnix
    tradeNoteId.value = filteredTrades[itemTradeIndex.value].trades[tradeIndex.value].id
    //console.log(" tradeNoteId.value " + tradeNoteId.value)
    tradeNoteChanged.value = true
    saveButton.value = true

}

/**************
 * SCREENSHOTS
 ***************/
const filteredScreenshots = (param1, param2) => {
    //console.log(" param1 dateUnix " + JSON.stringify(param1.dateUnix))
    //console.log(" filteredScreenshots")
    /*if (param1) {

        console.log(" param1 ")
    }
    */if (param2) {
        console.log(" param2 ")
    }
    let screenshotArray = []
    //console.log(" screenshotsInfos "+JSON.stringify(screenshotsInfos))
    for (let index = 0; index < param1.trades.length; index++) {
        const el1 = param1.trades[index];
        let screenshotsArray = []
        if (param2) {
            screenshotsArray = screenshots
        } else {
            screenshotsArray = screenshotsInfos

        }
        for (let index2 = 0; index2 < screenshotsArray.length; index2++) {
            const el2 = screenshotsArray[index2]
            if (el2.name == el1.id && (screenshotArray.findIndex(obj => obj == el2) == -1)) {
                screenshotArray.push(el2)
            } else if (useStartOfDay(el2.dateUnix) == param1.dateUnix && (screenshotArray.findIndex(obj => obj == el2) == -1)) {
                screenshotArray.push(el2)
            }
        }

    }
    //console.log(" screenshotArray " + JSON.stringify(screenshotArray))
    return screenshotArray
}

const filterDiary = (param) => {
    //console.log(" filter diary ")
    return diaries.filter(obj => obj.dateUnix == param)
}



function getOHLC(date, symbol, type) {
    if (apiSource.value === "databento") {
        console.log(" -> getting OHLC from " + apiSource.value + " for date " + useDateCalFormat(date))

        return new Promise(async (resolve, reject) => {
            let temp = {}
            temp.symbol = symbol

            let databentoSymbol = temp.symbol
            let stype_in = "raw_symbol"
            let toDate = dayjs(date * 1000).tz(timeZoneTrade.value).endOf('day').unix()
            let dataset
            //console.log("toDate "+toDate)
            temp.ohlcv = []

            if (type === "future") {
                dataset = "GLBX.MDP3"
                databentoSymbol = temp.symbol + ".c.0"
                stype_in = "continuous"

            } else if (type === "stock") {
                dataset = "XNAS.ITCH"

            } else if (tradedSymbols[i].secType === "call" || tradedSymbols[i].secType === "put") {

            } else if (tradedSymbols[i].secType === "forex") {

            }

            let data =
            {
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
            }

            axios.post('/api/databento', data)
                .then(async (response) => {
                    //console.log(" response "+JSON.stringify(response.data))

                    let res = await useCreateOHLCV(response.data, temp)
                    ohlcv.push(res) // used for MFE calculation (same as in addTrades.js)

                    let tempArray = {}
                    tempArray.date = date
                    tempArray.symbol = symbol
                    tempArray.ohlcTimestamps = []
                    tempArray.ohlcPrices = []
                    tempArray.ohlcVolumes = []

                    for (let index = 0; index < res.ohlcv.length; index++) {
                        const element = res.ohlcv[index];

                        let temp = []

                        tempArray.ohlcTimestamps.push(element.t)
                        temp.push(element.c)
                        temp.push(element.o)
                        temp.push(element.l)
                        temp.push(element.h)
                        tempArray.ohlcPrices.push(temp)
                        tempArray.ohlcVolumes.push(element.v)
                    }

                    ohlcArray.push(tempArray)
                    //console.log("ohlcArray "+JSON.stringify(ohlcArray))
                    resolve()
                })
                .catch((error) => {
                    console.log(" -> Error in databento response " + error)
                    reject(error)
                });
        })

    }
    else if (apiSource.value === "polygon") {

        let ticker
        if (type === "put" || type === "call" || type === "option") {
            ticker = "O:" + symbol
        } else if (type === "future") {
            ticker = "I:" + symbol
        } else if (type === "forex") {
            ticker = "C:" + symbol
        } else if (type === "crypto") {
            ticker = "X:" + symbol
        } else {
            ticker = symbol
        }
        console.log("  --> Getting OHLC for ticker " + ticker + " on " + date)

        return new Promise(async (resolve, reject) => {
            await axios.get("https://api.polygon.io/v2/aggs/ticker/" + ticker + "/range/1/minute/" + useDateCalFormat(date) + "/" + useDateCalFormat(date) + "?adjusted=true&sort=asc&limit=50000&apiKey=" + apiKey.value)

                .then((response) => {
                    let tempArray = {}
                    tempArray.date = date
                    tempArray.symbol = symbol
                    tempArray.ohlcTimestamps = []
                    tempArray.ohlcPrices = []
                    tempArray.ohlcVolumes = []

                    let temp = {}
                    temp.symbol = symbol
                    temp.ohlcv = response.data.results
                    ohlcv.push(temp) // used for MFE calculation (same as in addTrades.js)

                    for (let index = 0; index < response.data.results.length; index++) {
                        const element = response.data.results[index];

                        let temp = []

                        tempArray.ohlcTimestamps.push(element.t)
                        temp.push(element.c)
                        temp.push(element.o)
                        temp.push(element.l)
                        temp.push(element.h)
                        tempArray.ohlcPrices.push(temp)
                        tempArray.ohlcVolumes.push(element.v)
                    }

                    ohlcArray.push(tempArray)
                })
                .catch((error) => {
                    reject(error)
                })
                .finally(function () {
                    // always executed
                })

            resolve()

        })
    }

}

// Fetch orders from MongoDB
async function fetchMongoDbOrders() {
    // Check if we've already loaded orders recently (within last 30 seconds)
    const lastFetchTime = localStorage.getItem('lastOrderFetchTime');
    const now = Date.now();
    
    if (lastFetchTime && (now - parseInt(lastFetchTime)) < 30000) {
        console.log('Skipping MongoDB order fetch - last fetch was less than 30 seconds ago');
        return;
    }
    
    // Set loading state
    loadingOrders.value = true;
    
    // Store the fetch time immediately to prevent simultaneous requests
    localStorage.setItem('lastOrderFetchTime', now.toString());
    
    // Use setTimeout to run this asynchronously and not block UI
    setTimeout(async () => {
        try {
            console.log('Starting to fetch orders from MongoDB');
            
            // Fetch orders from MongoDB
            const orders = await orderSyncService.fetchOrdersFromMongoDB();
            console.log('Raw orders from MongoDB:', orders);
            
            // Make sure orders is an array before filtering
            if (Array.isArray(orders)) {
                mongoDbOrders.value = orders.filter(order => order.isExecutedOrder === true);
                console.log(`Loaded ${mongoDbOrders.value.length} executed orders from MongoDB`);
                
                // Build linked orders index
                linkedOrders = {}; // Reset existing links
                mongoDbOrders.value.forEach(order => {
                    // Skip orders that don't have trade IDs
                    if (!order.tradeId) return;
                    
                    // Add order to the linked orders for this trade
                    if (!linkedOrders[order.tradeId]) {
                        linkedOrders[order.tradeId] = [];
                    }
                    linkedOrders[order.tradeId].push(order);
                });
            } else {
                console.warn('Orders returned from MongoDB is not an array:', orders);
                mongoDbOrders.value = [];
            }
            
            // If no orders were found, create test orders for debugging
            if (mongoDbOrders.value.length === 0 && process.env.NODE_ENV === 'development') {
                console.log('No orders found, creating test orders');
                createTestOrders();
            }
        } catch (error) {
            console.error('Error in fetchMongoDbOrders:', error);
            // Initialize with empty array to prevent errors
            mongoDbOrders.value = [];
            
            // Create test orders for debugging in development
            if (process.env.NODE_ENV === 'development') {
                console.log('Error fetching orders, creating test orders');
                createTestOrders();
            }
        } finally {
            // Clear loading state
            loadingOrders.value = false;
        }
    }, 0);
}

// Function to create test orders for debugging
function createTestOrders() {
    console.log('Creating test orders');
    // Create some sample orders for testing
    mongoDbOrders.value = [
        {
            orderId: 'test-order-1',
            symbol: 'AAPL',
            action: 'BUY',
            orderType: 'LIMIT',
            totalQuantity: 100,
            limitPrice: 200.99,
            isExecutedOrder: true,
            timestamp: new Date().toISOString()
        },
        {
            orderId: 'test-order-2',
            symbol: 'TSLA',
            action: 'BUY',
            orderType: 'LIMIT',
            totalQuantity: 50,
            limitPrice: 850.50,
            isExecutedOrder: true,
            timestamp: new Date().toISOString()
        },
        {
            orderId: 'test-order-3',
            symbol: 'MSFT',
            action: 'BUY',
            orderType: 'LIMIT',
            totalQuantity: 75,
            limitPrice: 310.25,
            isExecutedOrder: true,
            timestamp: new Date().toISOString()
        }
    ];
    console.log('Created test orders:', mongoDbOrders.value);
}

// Link a trade to an order
function linkTradeToOrder(tradeId, orderId) {
    linkedOrders[tradeId] = orderId;
    // Hide the dropdown after selection
    showOrderDropdown[tradeId] = false;

    // Save the link to localStorage for persistence
    try {
        const storedLinks = JSON.parse(localStorage.getItem('tradeOrderLinks') || '{}');
        storedLinks[tradeId] = orderId;
        localStorage.setItem('tradeOrderLinks', JSON.stringify(storedLinks));
    } catch (error) {
        console.error('Error saving trade-order link to localStorage:', error);
    }
}

// Get filtered orders for a specific symbol
function getFilteredOrders(symbol) {
    console.log('Getting filtered orders for symbol:', symbol);
    console.log('mongoDbOrders.value:', mongoDbOrders.value);
    console.log('linkedOrders:', linkedOrders);

    if (!mongoDbOrders.value || !Array.isArray(mongoDbOrders.value)) {
        console.warn('mongoDbOrders.value is not an array or is null/undefined');
        return [];
    }

    const filteredOrders = mongoDbOrders.value.filter(order =>
        order.symbol === symbol &&
        !Object.values(linkedOrders).includes(order.orderId)
    );

    console.log(`Found ${filteredOrders.length} matching orders for ${symbol}`);
    return filteredOrders;
}

// Load saved links from localStorage
function loadSavedLinks() {
    try {
        const storedLinks = JSON.parse(localStorage.getItem('tradeOrderLinks') || '{}');
        Object.keys(storedLinks).forEach(tradeId => {
            linkedOrders[tradeId] = storedLinks[tradeId];
        });
    } catch (error) {
        console.error('Error loading trade-order links from localStorage:', error);
    }
}

// Call this function during component initialization
loadSavedLinks();

// Initialize showOrderDropdown for each trade
function initializeDropdowns() {
    console.log('Initializing dropdowns');
    if (filteredTrades && filteredTrades.length > 0) {
        filteredTrades.forEach(itemTrade => {
            if (itemTrade.trades && itemTrade.trades.length > 0) {
                itemTrade.trades.forEach(trade => {
                    if (trade.id) {
                        showOrderDropdown[trade.id] = false;
                    }
                });
            }
        });
    }
    console.log('Initialized dropdowns:', showOrderDropdown);
}

// Call initializeDropdowns after filteredTrades is populated
watch(filteredTrades, (newValue) => {
    if (newValue && newValue.length > 0) {
        console.log('filteredTrades changed, initializing dropdowns');
        initializeDropdowns();
    }
}, { deep: true });

// Replace the handleRowClick function with this implementation
function handleRowClick(event, itemIndex, tradeIndex) {
  // Check if the click was inside the order cell
  if (event.target.closest('.order-cell') ||
      event.target.closest('.order-link-container') ||
      event.target.closest('.order-dropdown') ||
      event.target.closest('.order-dropdown-menu')) {
    // Don't open the modal if clicking inside the order cell
    return;
  }

  // Set current trade data for the standalone modal
  currentItemTradeIndex.value = itemIndex;
  currentTradeIndex.value = tradeIndex;
  currentTradeData.value = filteredTrades[itemIndex].trades[tradeIndex];
  currentDateUnix.value = filteredTrades[itemIndex].dateUnix;
  
  // Show the standalone modal
  showStandaloneModal.value = true;
}

// Add handler for modal close
function handleModalClose() {
  showStandaloneModal.value = false;
  currentTradeData.value = null;
  
  // Reset state
  setTimeout(() => {
    // Refresh data if needed
    useCheckVisibleScreen();
  }, 100);
}

// Add handler for modal save
function handleModalSave() {
  showStandaloneModal.value = false;
  currentTradeData.value = null;
  
  // Refresh specific data instead of remounting the entire page
  setTimeout(async () => {
    try {
      console.log("Refreshing specific data after modal save...");
      
      // Only refresh tags, notes, and excursions which might have changed
      await Promise.all([
        useGetTags().catch(e => console.error("Error refreshing tags:", e)),
        useGetNotes().catch(e => console.error("Error refreshing notes:", e)),
        useGetExcursions().catch(e => console.error("Error refreshing excursions:", e))
      ]);
      
      // Refresh charts without reloading everything
      useRenderDoubleLineChart();
      useRenderPieChart();
      
      // Don't call useCheckVisibleScreen() as it may trigger loading more data
      console.log("Modal data refresh complete");
    } catch (error) {
      console.error("Error refreshing data after modal save:", error);
    }
  }, 100);
}
</script>

<template>
    <SpinnerLoadingPage />
    <div v-if="!spinnerLoadingPage && filteredTrades" class="row mt-2 mb-2">
        <Filters />
        <div v-if="!hasData">
            <NoData />
        </div>
        <div v-show="hasData">
            <!-- added v-if instead v-show because need to wait for patterns to load -->
            <div class="row">
                <!-- ============ CARD ============ -->
                <div class="col-12 col-xl-8">
                    <!-- v-show insead of v-if or else init tab does not work cause div is not created until spinner is false-->
                    <div v-for="(itemTrade, index) in filteredTrades" class="row mt-2">
                        <div class="col-12">
                            <div class="dailyCard">
                                <div class="row">
                                    <!-- ============ PART 1 ============ -->
                                    <!-- Line 1 : Date and P&L -->
                                    <!--<input id="providers" type="text" class="form-control" placeholder="Fournisseur*" autocomplete="off"/>-->


                                    <div class="col-12 cardFirstLine mb-2">
                                        <div class="row">
                                            <div class="col-12 col-lg-auto">{{ useCreatedDateFormat(itemTrade.dateUnix)
                                            }}
                                                <i v-on:click="dailySatisfactionChange(itemTrade.dateUnix, true, itemTrade)"
                                                    v-bind:class="[itemTrade.satisfaction == true ? 'greenTrade' : '', 'uil', 'uil-thumbs-up', 'ms-2', 'me-1', 'pointerClass']"></i>
                                                <i v-on:click="dailySatisfactionChange(itemTrade.dateUnix, false, itemTrade)"
                                                    v-bind:class="[itemTrade.satisfaction == false ? 'redTrade' : '', , 'uil', 'uil-thumbs-down', 'pointerClass']"></i>

                                                <i v-show="tags.filter(obj => obj.tradeId == itemTrade.dateUnix.toString()).length == 0 || (tags.filter(obj => obj.tradeId == itemTrade.dateUnix.toString()).length > 0 && tags.filter(obj => obj.tradeId == itemTrade.dateUnix.toString())[0].tags.length === 0)"
                                                    data-bs-toggle="modal" data-bs-target="#tagsModal"
                                                    :data-index="index" class="ms-2 uil uil-tag-alt pointerClass"></i>

                                            </div>
                                            <div v-if="itemTrade.pAndL" class="col-12 col-lg-auto ms-auto">P&L({{
                                                selectedGrossNet.charAt(0)
                                                }}):
                                                <span
                                                    v-bind:class="[itemTrade.pAndL[amountCase + 'Proceeds'] > 0 ? 'greenTrade' : 'redTrade']">{{
                                                        useTwoDecCurrencyFormat(itemTrade.pAndL[amountCase + 'Proceeds'])
                                                    }}</span>
                                            </div>

                                        </div>
                                        <div>
                                            <span
                                                v-for="tags in tags.filter(obj => obj.tradeId == itemTrade.dateUnix.toString())">
                                                <span v-for="tag in tags.tags.slice(0, 7)"
                                                    class="tag txt-small pointerClass"
                                                    :style="{ 'background-color': useGetTagInfo(tag).groupColor }"
                                                    data-bs-toggle="modal" data-bs-target="#tagsModal"
                                                    :data-index="index">{{
                                                        useGetTagInfo(tag).tagName
                                                    }}
                                                </span>
                                                <span v-show="tags.tags.length > 7">+{{
                                                    tags.tags.length
                                                    - 7 }}</span>
                                            </span>
                                        </div>
                                    </div>

                                    <!-- Line 2 : Charts and total data -->
                                    <div class="col-12 d-flex align-items-center text-center">
                                        <div class="row" v-if="itemTrade.pAndL">

                                            <!--  -> Win Loss Chart -->
                                            <div class="col-12 col-lg-6">
                                                <div class="row">
                                                    <div class="col-4">
                                                        <div :id="'pieChart' + itemTrade.dateUnix"
                                                            :key="'pie-' + itemTrade.dateUnix" class="chartIdDailyClass"
                                                            style="min-height: 100px;">
                                                        </div>
                                                    </div>
                                                    <!--  -> Win Loss evolution Chart -->
                                                    <div class="col-8 chartCard">
                                                        <div :id="'doubleLineChart' + itemTrade.dateUnix"
                                                            :key="'line-' + itemTrade.dateUnix"
                                                            class="chartIdDailyClass" style="min-height: 100px;">
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>

                                            <!--  -> Tot trades and total executions -->
                                            <div class="col-12 col-lg-6">
                                                <div class="row">
                                                    <div class="col row">
                                                        <div>
                                                            <label>Executions</label>
                                                            <p>{{ itemTrade.pAndL.executions }}</p>
                                                        </div>
                                                        <div>
                                                            <label>Trades</label>
                                                            <p>{{ itemTrade.pAndL.trades }}</p>
                                                        </div>
                                                    </div>

                                                    <!--  -> Tot Wins and losses -->
                                                    <div class="col row">
                                                        <div>
                                                            <label>Wins</label>
                                                            <p>{{ itemTrade.pAndL.grossWinsCount }}</p>
                                                        </div>
                                                        <div>
                                                            <label>Losses</label>
                                                            <p>{{ itemTrade.pAndL.grossLossCount }}</p>
                                                        </div>
                                                    </div>

                                                    <!--  -> Tot commission and gross p&l -->
                                                    <div class="col row">
                                                        <div>
                                                            <label>Tot Fees</label>
                                                            <p>{{ useTwoDecCurrencyFormat(itemTrade.pAndL.fees) }}</p>
                                                        </div>
                                                        <div>
                                                            <label>P&L(g)</label>
                                                            <p>{{ useTwoDecCurrencyFormat(itemTrade.pAndL.grossProceeds)
                                                            }}
                                                            </p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <!-- end PART 1 -->

                                    <!-- ============ PART 2 ============ -->
                                    <div v-if="!modalDailyTradeOpen" class="col-12 table-responsive">
                                        <nav>
                                            <!--------------------
                                            TABS
                                            --------------------->

                                            <!--Trades-->
                                            <div class="nav nav-tabs mb-2" id="nav-tab" role="tablist">
                                                <button class="nav-link" v-bind:id="'trades-' + index"
                                                    data-bs-toggle="tab" v-bind:data-bs-target="'#tradesNav-' + index"
                                                    type="button" role="tab" aria-controls="nav-overview"
                                                    aria-selected="true">Trades
                                                </button>

                                                <!--Blotter-->
                                                <button class="nav-link" v-bind:id="'blotter-' + index"
                                                    data-bs-toggle="tab" v-bind:data-bs-target="'#blotterNav-' + index"
                                                    type="button" role="tab" aria-controls="nav-overview"
                                                    aria-selected="true">Blotter
                                                </button>

                                                <!--Screenshots-->
                                                <button v-bind:id="'screenshots-' + index" data-bs-toggle="tab"
                                                    v-bind:data-bs-target="'#screenshotsNav-' + index" type="button"
                                                    role="tab" aria-controls="nav-overview" aria-selected="true"
                                                    v-bind:class="[filteredScreenshots(itemTrade).length > 0 ? '' : 'noDataTab', 'nav-link']">Screenshots<span
                                                        v-if="filteredScreenshots(itemTrade).length > 0"
                                                        class="txt-small">
                                                        ({{ filteredScreenshots(itemTrade).length }})</span>
                                                </button>

                                                <!--Diary-->
                                                <button v-bind:id="'diaries-' + index" data-bs-toggle="tab"
                                                    v-bind:data-bs-target="'#diariesNav-' + index" type="button"
                                                    role="tab" aria-controls="nav-overview" aria-selected="true"
                                                    v-bind:class="[filterDiary(itemTrade.dateUnix).length > 0 ? '' : 'noDataTab', 'nav-link']">Diary
                                                </button>
                                            </div>
                                        </nav>
                                        <div class="tab-content" id="nav-tabContent">

                                            <!-- TRADES TAB -->
                                            <div class="tab-pane fade txt-small" v-bind:id="'tradesNav-' + index"
                                                role="tabpanel" aria-labelledby="nav-overview-tab">
                                                <table class="table">
                                                    <thead>
                                                        <tr>
                                                            <th scope="col">Symbol</th>
                                                            <th scope="col">Vol<i class="ps-1 uil uil-info-circle"
                                                                    data-bs-toggle="tooltip"
                                                                    data-bs-title="Total number of securities during the trade (bought + sold or shorted + covered)"></i>
                                                            </th>
                                                            <th scope="col">Position</th>
                                                            <th scope="col">Entry</th>
                                                            <th scope="col">P&L/Sec<i class="ps-1 uil uil-info-circle"
                                                                    data-bs-toggle="tooltip"
                                                                    data-bs-title="Profit&Loss per unit of security traded (baught or shorted)"></i>
                                                            </th>
                                                            <th scope="col">P&L(n)</th>
                                                            <th scope="col">Tags</th>
                                                            <th scope="col">Note</th>
                                                            <th scope="col">Order</th>
                                                            <th scope="col"></th>
                                                            <th scope="col"></th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>

                                                        <!-- the page loads faster than the video blob => check if blob, that is after slash, is not null, and then load -->
                                                        <!--<tr v-if="/[^/]*$/.exec(videoBlob)[0]!='null'&&trade.videoStart&&trade.videoEnd">-->

                                                        <tr v-for="(trade, index2) in itemTrade.trades"
                                                            @click="handleRowClick($event, index, index2)"
                                                            class="pointerClass" :data-index="index"
                                                            :data-indextwo="index2">

                                                            <!--Symbol-->
                                                            <td>{{ trade.symbol }}</td>

                                                            <!--Vol-->
                                                            <td>{{ trade.buyQuantity + trade.sellQuantity }}</td>

                                                            <!--Position-->
                                                            <td>
                                                                {{
                                                                    trade.strategy.charAt(0).toUpperCase() +
                                                                    trade.strategy.slice(1)
                                                                }}
                                                            </td>

                                                            <!--Entry-->
                                                            <td>
                                                                <span v-if="trade.tradesCount == 0"><span
                                                                        v-if="trade.openPosition">Open<i
                                                                            class="ps-1 uil uil-info-circle"
                                                                            data-bs-toggle="tooltip" data-bs-html="true"
                                                                            v-bind:data-bs-title="'Swing trade opened on ' + useDateCalFormat(trade.entryTime)"></i></span><span
                                                                        v-else>Closed<i class="ps-1 uil uil-info-circle"
                                                                            data-bs-toggle="tooltip" data-bs-html="true"
                                                                            v-bind:data-bs-title="'Swing trade closed on ' + useDateCalFormat(trade.exitTime)"></i></span></span><span
                                                                    v-else>{{ useTimeFormat(trade.entryTime) }}<span
                                                                        v-if="checkDate(trade.td, trade.entryTime) == false"><i
                                                                            class="ps-1 uil uil-info-circle"
                                                                            data-bs-toggle="tooltip" data-bs-html="true"
                                                                            v-bind:data-bs-title="'Swing trade from ' + useDateCalFormat(trade.entryTime)"></i></span></span>
                                                            </td>

                                                            <!--P&L/Vol-->
                                                            <td>
                                                                <span v-if="trade.tradesCount == 0"></span><span
                                                                    v-else-if="trade.type == 'forex'">-</span><span
                                                                    v-else
                                                                    v-bind:class="[trade.grossSharePL > 0 ? 'greenTrade' : 'redTrade']">{{
                                                                        useTwoDecCurrencyFormat(trade.grossSharePL)
                                                                    }}</span>
                                                            </td>

                                                            <!--P&L-->
                                                            <td>
                                                                <span v-if="trade.tradesCount == 0"></span><span v-else
                                                                    v-bind:class="[trade.netProceeds > 0 ? 'greenTrade' : 'redTrade']">
                                                                    {{ useTwoDecCurrencyFormat(trade.netProceeds)
                                                                    }}</span>
                                                            </td>

                                                            <!--TAGS -->
                                                            <td>
                                                                <span
                                                                    v-for="tags in tags.filter(obj => obj.tradeId == trade.id)">
                                                                    <span v-for="tag in tags.tags.slice(0, 2)"
                                                                        class="tag txt-small"
                                                                        :style="{ 'background-color': useGetTagInfo(tag).groupColor }">{{
                                                                            useGetTagInfo(tag).tagName }}
                                                                    </span>
                                                                    <span v-show="tags.tags.length > 2">+{{
                                                                        tags.tags.length
                                                                        - 2 }}</span>
                                                                </span>
                                                            </td>
                                                            <td>
                                                                <span
                                                                    v-for="note in notes.filter(obj => obj.tradeId == trade.id)">
                                                                    <span v-if="note.note.length > 12">{{
                                                                        note.note.substring(0, 12) }}...</span><span
                                                                        v-else>{{ note.note }}</span>
                                                                </span>
                                                            </td>

                                                            <!-- Order ID Column -->
                                                            <td @click.stop class="order-cell">
                                                                <div class="order-link-container" @click.stop>
                                                                    <!-- Already linked order -->
                                                                    <div v-if="linkedOrders[trade.id]"
                                                                        class="linked-order">
                                                                        <span class="order-id">{{
                                                                            linkedOrders[trade.id].substring(0, 8)
                                                                            }}...</span>
                                                                        <i class="uil uil-link ms-1 text-success"></i>
                                                                    </div>

                                                                    <!-- Order needs to be linked -->
                                                                    <div v-else>
                                                                        <!-- Link button -->
                                                                        <button
                                                                            @click.stop.prevent="(event) => toggleOrderPopup(trade.id, trade.symbol, event)"
                                                                            class="btn btn-sm btn-outline-primary order-link-btn"
                                                                            style="color: white;"
                                                                            type="button">
                                                                            <i class="uil uil-link" style="color:white"></i>
                                                                            Link
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            </td>

                                                            <td>
                                                                <span v-if="trade.satisfaction == true">
                                                                    <i class="greenTrade uil uil-thumbs-up"></i>
                                                                </span>
                                                                <span v-if="trade.satisfaction == false">
                                                                    <i class="redTrade uil uil-thumbs-down"></i>
                                                                </span>
                                                            </td>

                                                            <td>
                                                                <span
                                                                    v-if="screenshotsInfos.findIndex(f => f.name == trade.id) != -1">
                                                                    <i class="uil uil-image-v"></i>
                                                                </span>
                                                            </td>

                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </div>

                                            <!-- BLOTTER TAB -->
                                            <div class="tab-pane fade txt-small" v-bind:id="'blotterNav-' + index"
                                                role="tabpanel" aria-labelledby="nav-overview-tab">
                                                <table v-bind:id="'table' + index" class="table">
                                                    <thead>
                                                        <tr>
                                                            <th scope="col">Symbol</th>
                                                            <th scope="col">Vol</th>
                                                            <th scope="col">P&L(g)</th>
                                                            <th scope="col">Tot Fees</th>
                                                            <th scope="col">P&L(n)</th>
                                                            <th scope="col">Wins</th>
                                                            <th scope="col">Losses</th>
                                                            <th scope="col">Trades</th>
                                                            <th scope="col">Executions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody v-if="itemTrade.blotter">
                                                        <tr v-for="blot in itemTrade.blotter">

                                                            <td>{{ blot.symbol }}</td>
                                                            <td>{{ useDecimalsArithmetic(blot.buyQuantity,
                                                                blot.sellQuantity) }}</td>
                                                            <td
                                                                v-bind:class="[blot.grossProceeds > 0 ? 'greenTrade' : 'redTrade']">
                                                                {{ useTwoDecCurrencyFormat(blot.grossProceeds) }}</td>
                                                            <td>{{ useTwoDecCurrencyFormat(blot.fees) }}</td>
                                                            <td
                                                                v-bind:class="[blot[amountCase + 'Proceeds'] > 0 ? 'greenTrade' : 'redTrade']">
                                                                {{ useTwoDecCurrencyFormat(blot.netProceeds) }}</td>
                                                            <td>{{ blot.grossWinsCount }}</td>
                                                            <td>{{ blot.grossLossCount }}</td>
                                                            <td>{{ blot.trades }}</td>
                                                            <td>{{ blot.executions }}</td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </div>

                                            <!-- SCREENSHOTS TAB -->
                                            <div class="tab-pane fade txt-small" v-bind:id="'screenshotsNav-' + index"
                                                role="tabpanel" aria-labelledby="nav-overview-tab">
                                                <div v-show="idCurrentType == 'screenshots' && idCurrentNumber == index && tabGettingScreenshots"
                                                    class="text-center spinnerHeigth">
                                                    <div class="spinner-border text-blue" role="status"></div>
                                                </div>
                                                <div v-if="filteredScreenshots(itemTrade).length > 0 && idCurrentType == 'screenshots' && idCurrentNumber == index"
                                                    v-for="itemScreenshot in filteredScreenshots(itemTrade, itemTrade.dateUnix)">
                                                    <span class="mb-2">
                                                        <Screenshot :screenshot-data="itemScreenshot" show-title
                                                            source="dailyTab" />
                                                    </span>
                                                </div>
                                            </div>

                                            <!-- DIARY TAB -->
                                            <div class="tab-pane fade" v-bind:id="'diariesNav-' + index" role="tabpanel"
                                                aria-labelledby="nav-overview-tab">
                                                <div
                                                    v-for="itemDiary in diaries.filter(obj => obj.dateUnix == itemTrade.dateUnix)">
                                                    <p v-html="itemDiary.diary"></p>
                                                </div>
                                            </div>

                                        </div>
                                    </div>
                                    <!-- end PART 2 -->

                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <!-- end card-->
                <!-- ============ CALENDAR ============ -->
                <div class="col-12 col-xl-4 text-center mt-2 align-self-start">
                    <div class="dailyCard calCard">
                        <div class="row">
                            <Calendar />
                        </div>
                    </div>
                </div>
            </div>

            <!-- Load more spinner -->
            <div v-if="spinnerLoadMore" class="d-flex justify-content-center mt-3">
                <div class="spinner-border text-blue" role="status"></div>
            </div>

        </div>
    </div>

    <!-- ============ TRADES MODAL ============ -->
    <!-- TODO: Remove this old modal markup once the standalone TradeDetailsModal is confirmed working -->
    <div class="modal fade" id="tradesModal" data-bs-backdrop="true" data-bs-keyboard="true" tabindex="-1"
        aria-labelledby="exampleModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Trade Details</h5>
                    <button type="button" class="btn-close" v-on:click="clickTradesModal()" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                <div v-if="modalDailyTradeOpen">
                    <div class="col-12 text-end mb-3">
                        <button type="button" class="btn btn-outline-danger" v-on:click="clickTradesModal()">
                            <i class="uil uil-times"></i> Close
                        </button>
                    </div>
                    <div v-if="screenshot.originalBase64">
                        <Screenshot :screenshot-data="screenshot" source="dailyModal" />
                    </div>
                    <div v-show="!candlestickChartFailureMessage && !screenshot.originalBase64" id="candlestickChart"
                        class="candlestickClass">
                    </div>
                    <div class="container mt-2 text-center" v-show="candlestickChartFailureMessage">{{
                        candlestickChartFailureMessage }}</div>

                    <!-- *** Table *** -->
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
                                    <th scope="col">Order</th>
                                </tr>
                            </thead>
                            <tbody>
                                <!-- the page loads faster than the video blob => check if blob, that is after slash, is not null, and then load -->
                                <tr>
                                    <td>{{ filteredTrades[itemTradeIndex].trades[tradeIndex].symbol }}</td>
                                    <td>{{ filteredTrades[itemTradeIndex].trades[tradeIndex].buyQuantity +
                                        filteredTrades[itemTradeIndex].trades[tradeIndex].sellQuantity }}
                                    </td>
                                    <td>{{ filteredTrades[itemTradeIndex].trades[tradeIndex].side == 'B' ? 'Long' :
                                        'Short'
                                    }}</td>

                                    <!--Entry-->
                                    <td>
                                        <span
                                            v-if="filteredTrades[itemTradeIndex].trades[tradeIndex].tradesCount == 0"><span
                                                v-if="filteredTrades[itemTradeIndex].trades[tradeIndex].openPosition">Open<i
                                                    class="ps-1 uil uil-info-circle" data-bs-toggle="tooltip"
                                                    data-bs-html="true"
                                                    v-bind:data-bs-title="'Swing trade opened on ' + useDateCalFormat(filteredTrades[itemTradeIndex].trades[tradeIndex].entryTime)"></i></span><span
                                                v-else>Closed<i class="ps-1 uil uil-info-circle"
                                                    data-bs-toggle="tooltip" data-bs-html="true"
                                                    v-bind:data-bs-title="'Swing trade closed on ' + useDateCalFormat(filteredTrades[itemTradeIndex].trades[tradeIndex].exitTime)"></i></span></span><span
                                            v-else>{{
                                                useTimeFormat(filteredTrades[itemTradeIndex].trades[tradeIndex].entryTime)
                                            }}<span
                                                v-if="checkDate(filteredTrades[itemTradeIndex].trades[tradeIndex].td, filteredTrades[itemTradeIndex].trades[tradeIndex].entryTime) == false"><i
                                                    class="ps-1 uil uil-info-circle" data-bs-toggle="tooltip"
                                                    data-bs-html="true"
                                                    v-bind:data-bs-title="'Swing trade from ' + useDateCalFormat(filteredTrades[itemTradeIndex].trades[tradeIndex].entryTime)"></i></span></span>
                                    </td>

                                    <!--Entry Price-->
                                    <td><span
                                            v-if="filteredTrades[itemTradeIndex].trades[tradeIndex].tradesCount == 0"></span><span
                                            v-else-if="filteredTrades[itemTradeIndex].trades[tradeIndex].type == 'forex'">{{
                                                (filteredTrades[itemTradeIndex].trades[tradeIndex].entryPrice).toFixed(5)
                                            }}</span><span v-else>{{
                                                useTwoDecCurrencyFormat(filteredTrades[itemTradeIndex].trades[tradeIndex].entryPrice)
                                            }}<span
                                                v-if="checkDate(filteredTrades[itemTradeIndex].trades[tradeIndex].td, filteredTrades[itemTradeIndex].trades[tradeIndex].entryTime) == false"><i
                                                    class="ps-1 uil uil-info-circle" data-bs-toggle="tooltip"
                                                    data-bs-html="true"
                                                    v-bind:data-bs-title="'Swing trade from ' + useDateCalFormat(filteredTrades[itemTradeIndex].trades[tradeIndex].entryTime)"></i></span></span>
                                    </td>

                                    <!--Exit-->
                                    <td><span
                                            v-if="filteredTrades[itemTradeIndex].trades[tradeIndex].tradesCount == 0"></span><span
                                            v-else>{{
                                                useTimeFormat(filteredTrades[itemTradeIndex].trades[tradeIndex].exitTime)
                                            }}</span></td>


                                    <!--Exit Price-->
                                    <td><span
                                            v-if="filteredTrades[itemTradeIndex].trades[tradeIndex].tradesCount == 0"></span><span
                                            v-else-if="filteredTrades[itemTradeIndex].trades[tradeIndex].type == 'forex'">{{
                                                (filteredTrades[itemTradeIndex].trades[tradeIndex].exitPrice).toFixed(5)
                                            }}</span><span v-else>{{
                                                useTwoDecCurrencyFormat(filteredTrades[itemTradeIndex].trades[tradeIndex].exitPrice)
                                            }}</span></td>

                                    <!--Duration-->
                                    <td><span
                                            v-if="filteredTrades[itemTradeIndex].trades[tradeIndex].tradesCount == 0"></span><span
                                            v-else><span
                                                v-if="checkDate(filteredTrades[itemTradeIndex].trades[tradeIndex].td, filteredTrades[itemTradeIndex].trades[tradeIndex].entryTime) == false">{{
                                                    useSwingDuration(filteredTrades[itemTradeIndex].trades[tradeIndex].exitTime
                                                        -
                                                        filteredTrades[itemTradeIndex].trades[tradeIndex].entryTime)
                                                }}</span><span v-else>{{
                                                    useTimeDuration(filteredTrades[itemTradeIndex].trades[tradeIndex].exitTime
                                                        -
                                                        filteredTrades[itemTradeIndex].trades[tradeIndex].entryTime)
                                                }}</span></span>
                                    </td>

                                    <!--P&L/Vol-->
                                    <td>
                                        <span
                                            v-if="filteredTrades[itemTradeIndex].trades[tradeIndex].tradesCount == 0"></span><span
                                            v-else-if="filteredTrades[itemTradeIndex].trades[tradeIndex].type == 'forex'"></span><span
                                            v-else
                                            v-bind:class="[(filteredTrades[itemTradeIndex].trades[tradeIndex].grossSharePL) > 0 ? 'greenTrade' : 'redTrade']">{{
                                                useTwoDecCurrencyFormat(filteredTrades[itemTradeIndex].trades[tradeIndex].grossSharePL)
                                            }}</span>
                                    </td>

                                    <!--P&L-->
                                    <td><span
                                            v-if="filteredTrades[itemTradeIndex].trades[tradeIndex].tradesCount == 0"></span><span
                                            v-else
                                            v-bind:class="[filteredTrades[itemTradeIndex].trades[tradeIndex].netProceeds > 0 ? 'greenTrade' : 'redTrade']">
                                            {{
                                                useTwoDecCurrencyFormat(filteredTrades[itemTradeIndex].trades[tradeIndex].netProceeds)
                                            }}</span>
                                    </td>

                                    <!-- Order ID in modal -->
                                    <td>
                                        <div v-if="linkedOrders[filteredTrades[itemTradeIndex].trades[tradeIndex].id]"
                                            class="linked-order-modal">
                                            <span class="order-id-modal">{{
                                                linkedOrders[filteredTrades[itemTradeIndex].trades[tradeIndex].id].substring(0,
                                                10) }}...</span>
                                            <i class="uil uil-link ms-1 text-success"></i>
                                        </div>
                                        <div v-else class="no-order">
                                            <span class="text-muted">No order linked</span>
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <!-- Order Details Section -->
                    <div v-if="linkedOrders[filteredTrades[itemTradeIndex].trades[tradeIndex].id]"
                        class="mt-3 mb-3 order-details-section">
                        <h6 class="mb-2">Linked Order Details</h6>
                        <div class="order-details-container">
                            <div class="order-details-row"
                                v-for="order in mongoDbOrders.value.filter(o => o.orderId === linkedOrders[filteredTrades[itemTradeIndex].trades[tradeIndex].id])">
                                <div class="order-detail-item">
                                    <span class="detail-label">Symbol:</span>
                                    <span class="detail-value">{{ order.symbol }}</span>
                                </div>
                                <div class="order-detail-item">
                                    <span class="detail-label">Action:</span>
                                    <span class="detail-value">{{ order.action }}</span>
                                </div>
                                <div class="order-detail-item">
                                    <span class="detail-label">Quantity:</span>
                                    <span class="detail-value">{{ order.totalQuantity }}</span>
                                </div>
                                <div class="order-detail-item">
                                    <span class="detail-label">Price:</span>
                                    <span class="detail-value">{{ useTwoDecCurrencyFormat(order.limitPrice ||
                                        order.stopPrice) }}</span>
                                </div>
                                <div class="order-detail-item">
                                    <span class="detail-label">Position Value:</span>
                                    <span class="detail-value">{{ useTwoDecCurrencyFormat(order.positionValue) }}</span>
                                </div>
                                <div class="order-detail-item">
                                    <span class="detail-label">Allocation %:</span>
                                    <span class="detail-value">{{ order.allocationPercent ?
                                        order.allocationPercent.toFixed(2) + '%' : 'N/A' }}</span>
                                </div>
                                <div class="order-detail-item">
                                    <span class="detail-label">Risk/Reward:</span>
                                    <span class="detail-value">{{ order.riskRewardRatio ?
                                        order.riskRewardRatio.toFixed(2) : 'N/A' }}</span>
                                </div>
                                <div class="order-detail-item">
                                    <span class="detail-label">Stop Loss:</span>
                                    <span class="detail-value">{{ order.stopLossPercent ?
                                        order.stopLossPercent.toFixed(2) + '%' : 'N/A' }}</span>
                                </div>
                                <div class="order-detail-item">
                                    <span class="detail-label">Potential Profit:</span>
                                    <span class="detail-value">{{ order.potentialProfitPercent ?
                                        order.potentialProfitPercent.toFixed(2) + '%' : 'N/A' }}</span>
                                </div>
                                <div class="order-detail-item">
                                    <span class="detail-label">Order ID:</span>
                                    <span class="detail-value order-id-full">{{ order.orderId }}</span>
                                </div>
                                <div class="order-detail-item">
                                    <button
                                        @click="linkTradeToOrder(filteredTrades[itemTradeIndex].trades[tradeIndex].id, null)"
                                        class="btn btn-sm btn-outline-danger">
                                        <i class="uil uil-unlink"></i> Unlink Order
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- *** VARIABLES *** -->
                    <div class="mt-1 mb-2 row align-items-center ms-1 me-1 tradeSetup">
                        <div class="col-12">
                            <div class="row">
                                <!-- First line -->
                                <div class="col-12" v-show="!spinnerSetups">
                                    <div class="row align-items-center">

                                        <!-- Satisfaction -->
                                        <div class="col-1">
                                            <i v-on:click="tradeSatisfactionChange(filteredTrades[itemTradeIndex].trades[tradeIndex], true)"
                                                v-bind:class="[filteredTrades[itemTradeIndex].trades[tradeIndex].satisfaction == true ? 'greenTrade' : '', 'uil', 'uil-thumbs-up', 'pointerClass', 'me-1']"></i>

                                            <i v-on:click="tradeSatisfactionChange(filteredTrades[itemTradeIndex].trades[tradeIndex], false)"
                                                v-bind:class="[filteredTrades[itemTradeIndex].trades[tradeIndex].satisfaction == false ? 'redTrade' : '', 'uil', 'uil-thumbs-down', 'pointerClass']"></i>
                                        </div>


                                        <!-- Tags -->
                                        <div class="container-tags col-8">
                                            <div class="form-control dropdown form-select" style="height: auto;">
                                                <div style="display: flex; align-items: center; flex-wrap: wrap;">
                                                    <span v-for="(tag, index) in tradeTags" :key="index"
                                                        class="tag txt-small"
                                                        :style="{ 'background-color': useGetTagInfo(tag.id).groupColor }"
                                                        @click="useTradeTagsChange('remove', index)">
                                                        {{ tag.name }}<span class="remove-tag">×</span>
                                                    </span>

                                                    <input type="text" v-model="tagInput" @input="useFilterTags"
                                                        @keydown.enter.prevent="useTradeTagsChange('add', tagInput)"
                                                        @keydown.tab.prevent="useTradeTagsChange('add', tagInput)"
                                                        class="form-control tag-input" placeholder="Add a tag">
                                                    <div class="clickable-area" v-on:click="useToggleTagsDropdown">
                                                    </div>
                                                </div>
                                            </div>

                                            <ul id="dropdown-menu-tags" class="dropdown-menu-tags"
                                                :style="[!showTagsList ? 'border: none;' : '']">
                                                <span v-show="showTagsList" v-for="group in availableTags">
                                                    <h6 class="p-1 mb-0"
                                                        :style="'background-color: ' + group.color + ';'"
                                                        v-show="useFilterSuggestions(group.id).filter(obj => obj.id == group.id)[0].tags.length > 0">
                                                        {{ group.name }}</h6>
                                                    <li v-for="(suggestion, index) in useFilterSuggestions(group.id).filter(obj => obj.id == group.id)[0].tags"
                                                        :key="index" :class="{ active: index === selectedTagIndex }"
                                                        @click="useTradeTagsChange('addFromDropdownMenu', suggestion)"
                                                        class="dropdown-item dropdown-item-tags">
                                                        <span class="ms-2">{{ suggestion.name }}</span>
                                                    </li>
                                                </span>
                                            </ul>
                                        </div>
                                        <!-- MFE -->
                                        <div class="col-3">
                                            <input type="number" class="form-control" placeholder="MFE Price"
                                                style="font-size: small;" v-bind:value="excursion.mfePrice"
                                                v-on:click="tradeExcursionClicked"
                                                v-on:change="tradeExcursionChange($event.target.value, 'mfePrice')">
                                        </div>
                                        <!-- Delete
                                        <div class="col-1">
                                            <i v-on:click="useDeleteSetup(filteredTrades[itemTradeIndex].dateUnix, filteredTrades[itemTradeIndex].trades[tradeIndex])"
                                                class="ps-2 uil uil-trash-alt pointerClass"></i>
                                        </div> -->
                                    </div>
                                </div>

                                <!-- Second line -->
                                <div class="col-12 mt-2" v-show="!spinnerSetups">
                                    <textarea class="form-control" placeholder="note" id="floatingTextarea"
                                        v-bind:value="tradeNote"
                                        @input="tradeNoteChange($event.target.value)"></textarea>
                                </div>

                                <!-- Forth line -->
                                <div class="col-12 mt-3" v-show="!spinnerSetups">
                                    <input class="screenshotFile" type="file"
                                        @change="useSetupImageUpload($event, filteredTrades[itemTradeIndex].trades[tradeIndex].entryTime, filteredTrades[itemTradeIndex].trades[tradeIndex].symbol, filteredTrades[itemTradeIndex].trades[tradeIndex].side)" />
                                </div>


                                <!-- Fifth line -->
                                <div class="col-12 mt-3" v-show="!spinnerSetups">
                                    <div class="row">
                                        <div class="col-4 text-start">
                                            <button
                                                v-show="filteredTrades[itemTradeIndex].trades.hasOwnProperty(tradeIndex - 1)"
                                                class="btn btn-outline-primary btn-sm ms-3 mb-2"
                                                v-on:click="clickTradesModal(itemTradeIndex, tradeIndex, tradeIndex - 1)"
                                                v-bind:disabled="spinnerSetups == true">
                                                <i class="fa fa-chevron-left me-2"></i></button>
                                        </div>
                                        <div class="col-4 text-center">
                                            <button v-if="saveButton" class="btn btn-outline-success btn-sm"
                                                v-on:click="clickTradesModal()">Close
                                                & Save</button>
                                            <button v-else class="btn btn-outline-primary btn-sm"
                                                v-on:click="clickTradesModal()">Close</button>
                                        </div>
                                        <div v-show="filteredTrades[itemTradeIndex].trades.hasOwnProperty(tradeIndex + 1)"
                                            class="ms-auto col-4 text-end">
                                            <button class="btn btn-outline-primary btn-sm me-3 mb-2"
                                                v-on:click="clickTradesModal(itemTradeIndex, tradeIndex, tradeIndex + 1)"
                                                v-bind:disabled="spinnerSetups == true">
                                                <i class="fa fa-chevron-right ms-2"></i></button>
                                        </div>
                                    </div>
                                </div>

                                <!-- Spinner -->
                                <div v-show="spinnerSetups" class="col-12">
                                    <div class="d-flex justify-content-center">
                                        <div class="spinner-border spinner-border-sm text-blue" role="status"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <hr>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- ============ TAGS MODAL ============ -->
    <div class="modal fade" id="tagsModal" data-bs-backdrop="true" data-bs-keyboard="true" tabindex="-1"
        aria-labelledby="exampleModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Edit Tags</h5>
                    <button type="button" class="btn-close" v-on:click="closeTagsModal()" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                <!-- Tags -->
                <div class="container col mt-4">
                    <div class="form-control dropdown form-select" style="height: auto;">
                        <div style="display: flex; align-items: center; flex-wrap: wrap;">
                            <span v-for="(tag, index) in tradeTags" :key="index" class="tag txt-small"
                                :style="{ 'background-color': useGetTagInfo(tag.id).groupColor }"
                                @click="useTradeTagsChange('remove', index)">
                                {{ tag.name }}<span class="remove-tag">×</span>
                            </span>

                            <input type="text" v-model="tagInput" @input="useFilterTags"
                                @keydown.enter.prevent="useTradeTagsChange('add', tagInput)"
                                @keydown.tab.prevent="useTradeTagsChange('add', tagInput)"
                                class="form-control tag-input" placeholder="Add a tag">
                            <div class="clickable-area" v-on:click="useToggleTagsDropdown">
                            </div>
                        </div>
                    </div>

                    <ul id="dropdown-menu-tags" class="dropdown-menu-tags"
                        :style="[!showTagsList ? 'border: none;' : '']">
                        <span v-show="showTagsList" v-for="group in availableTags">
                            <h6 class="p-1 mb-0" :style="'background-color: ' + group.color + ';'"
                                v-show="useFilterSuggestions(group.id).filter(obj => obj.id == group.id)[0].tags.length > 0">
                                {{ group.name }}</h6>
                            <li v-for="(suggestion, index) in useFilterSuggestions(group.id).filter(obj => obj.id == group.id)[0].tags"
                                :key="index" :class="{ active: index === selectedTagIndex }"
                                @click="useTradeTagsChange('addFromDropdownMenu', suggestion)"
                                class="dropdown-item dropdown-item-tags">
                                <span class="ms-2">{{ suggestion.name }}</span>
                            </li>
                        </span>
                    </ul>
                </div>
                <div class="col text-center mt-4 mb-4">
                        <button class="btn btn-outline-danger btn-sm" v-on:click="closeTagsModal()">
                            <i class="uil uil-times"></i> Close
                        </button>
                    <button class="btn btn-outline-success btn-sm ms-4" v-on:click="saveDailyTags()">Save</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Order Link Popup -->
    <OrderLinkPopup :is-open="showOrderPopup" :trade-id="currentTradeForPopup" :symbol="currentSymbolForPopup"
        :orders="currentSymbolForPopup ? getFilteredOrders(currentSymbolForPopup) : []" :loading-orders="loadingOrders"
        @close="showOrderPopup = false" @link-order="linkTradeToOrder" />

    <!-- Trade Details Modal -->
    <TradeDetailsModal 
      :is-open="showStandaloneModal" 
      :trade="currentTradeData" 
      :trade-index="currentTradeIndex" 
      :date-unix="currentDateUnix" 
      @close="handleModalClose" 
      @save="handleModalSave" 
    />
</template>

<style scoped>
/* General Daily Page Styling */
.row.mt-2.mb-2 {
    padding: 0 15px;
    /* Add some horizontal padding to the main content area */
}

/* Modern Card Styling */
.dailyCard {
    background-color: #202124;
    border-radius: 10px;
    padding: 10px;
    position: relative;
    z-index: 1; /* Lower z-index to prevent dropdown overlap */
}

.dailyCard:hover {
    transform: translateY(-3px);
    /* Subtle lift effect on hover */
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    /* Enhanced shadow on hover */
}

.cardFirstLine {
    font-size: 1.1rem;
    font-weight: 600;
    color: #6a8dff;
    /* Accent color for date */
}

.dailyCard .dashInfoTitle {
    font-size: 0.9rem;
    color: #a0a0a0;
    /* Muted color for descriptions */
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Tab Navigation Styling */
.nav-tabs {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 20px;
}

.nav-link {
    color: #a0a0a0;
    /* Muted color for inactive tabs */
    border: none;
    border-radius: 8px 8px 0 0;
    padding: 12px 20px;
    transition: all 0.3s ease;
    font-weight: 600;
}

.nav-link:hover {
    background-color: #2a2a4a;
    /* Darker hover background */
    color: #fff;
}

.nav-link.active {
    background-color: #1e1e2f;
    /* Active tab background */
    color: #6a8dff;
    /* Accent color for active tab text */
    border-color: rgba(255, 255, 255, 0.1) rgba(255, 255, 255, 0.1) #1e1e2f;
    /* Match card background */
    border-bottom: 3px solid #6a8dff;
    /* Accent line for active tab */
}

.noDataTab {
    opacity: 0.6;
    cursor: not-allowed;
}

/* Table Styling */
.table {
    width: 100%;
    border-collapse: separate;
    /* For rounded corners on cells */
    border-spacing: 0 8px;
    /* Space between rows */
    color: #e0e0e0;
}

.table thead th {
    background-color: #3a3a5a;
    /* Header background */
    color: #fff;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.85rem;
    letter-spacing: 0.5px;
    padding: 12px 15px;
    text-align: left;
    border: none;
}

.table tbody tr {
    background-color: #2a2a4a;
    /* Row background */
    border-radius: 8px;
    /* Rounded rows */
    transition: background-color 0.2s ease;
}

.table tbody tr:hover {
    background-color: #2a2a4a;
    /* Darker row on hover */
}

.table th,
.table td {
    padding: 12px 15px;
    text-align: left;
    border: none;
    /* Remove default borders */
}

/* Chart Styling */
.chartIdDailyClass {
    max-width: 100%;
    height: 150px;
    /* Consistent height for daily charts */
    margin: 0 auto;
}

.chartCard {
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Typography and Colors */
.greenTrade {
    color: #4caf50 !important;
    /* Vibrant green for success */
}

.redTrade {
    color: #ff6b6b !important;
    /* Softer red for danger */
}

.txt-small {
    font-size: 0.85rem;
}

.tag {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 5px;
    margin-right: 5px;
    margin-bottom: 5px;
    color: #fff;
    font-weight: 500;
}

.pointerClass {
    cursor: pointer;
}

/* Order cell styles */
.order-cell {
    position: relative;
    z-index: 1; /* Reduced from 10 to ensure dropdown visibility */
}

.order-link-container {
    position: relative;
    display: inline-block;
}

.order-link-btn {
    position: relative;
    z-index: 5; /* Reduced from higher value */
    background-color: #6a8dff;
    /* Modern blue for buttons */
    border-color: #6a8dff;
    color: #fff;
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 5px;
    transition: background-color 0.3s ease, transform 0.2s ease;
}

.order-link-btn:hover {
    background-color: #5a7ce0;
    transform: translateY(-1px);
    /* Slight lift effect */
}

.linked-order {
    display: flex;
    align-items: center;
    font-size: 0.85rem;
    color: #e0e0e0;
}

.order-id {
    max-width: 80px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* Modal order styles */
.linked-order-modal {
    display: flex;
    align-items: center;
    color: #e0e0e0;
}

.order-id-modal {
    font-size: 0.85rem;
}

.no-order {
    font-size: 0.8rem;
    color: #a0a0a0;
}

.order-details-section {
    background-color: #1e1e2f;
    /* Darker background for details section */
    border-radius: 12px;
    padding: 20px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #e0e0e0;
}

.order-details-container {
    display: flex;
    flex-wrap: wrap;
}

.order-details-row {
    display: flex;
    flex-wrap: wrap;
    width: 100%;
}

.order-detail-item {
    margin-right: 1.5rem;
    margin-bottom: 0.5rem;
    min-width: 120px;
}

.detail-label {
    display: block;
    font-size: 0.75rem;
    color: #a0a0a0;
}

.detail-value {
    font-size: 0.9rem;
    font-weight: 500;
}

.order-id-full {
    font-family: monospace;
    font-size: 0.8rem;
}

tr.pointerClass {
    cursor: pointer;
}

.spinnerHeigth {
    height: 100px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.modal-content {
    background-color: #1e1e2f;
    /* Dark background for modal content */
    color: #e0e0e0;
    border-radius: 12px;
    border: none;
}

.modal-header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-footer {
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.form-control {
    background-color: #2a2a4a;
    /* Darker input fields */
    color: #e0e0e0;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.form-control::placeholder {
    color: #a0a0a0;
}

.btn-outline-primary {
    color: #6a8dff;
    border-color: #6a8dff;
}

.btn-outline-primary:hover {
    background-color: #6a8dff;
    color: #fff;
}

.btn-outline-success {
    color: #4caf50;
    border-color: #4caf50;
}

.btn-outline-success:hover {
    background-color: #4caf50;
    color: #fff;
}

.container-tags .tag-input {
    background-color: transparent;
    border: none;
    color: #e0e0e0;
}

.dropdown-menu-tags {
    background-color: #2a2a4a;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.dropdown-item-tags {
    color: #e0e0e0;
}

.dropdown-item-tags:hover {
    background-color: #3a3a5a;
}

.dropdown-item-tags.active {
    background-color: #6a8dff;
    color: #fff;
}

/* Fix for dropdown visibility */
.row, .col-12, .tab-content, .tab-pane {
  position: relative;
  z-index: 1; /* Keep content below dropdowns */
}
</style>