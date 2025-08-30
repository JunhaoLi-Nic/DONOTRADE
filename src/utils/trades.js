import { pageId, spinnerLoadingPage, selectedRange, selectedDateRange, filteredTrades, filteredTradesTrades, selectedPositions, selectedAccounts, pAndL, queryLimit, blotter, totals, totalsByDate, groups, profitAnalysis, timeFrame, timeZoneTrade, hasData, satisfactionArray, satisfactionTradeArray, tags, filteredTradesDaily, dailyPagination, dailyQueryLimit, endOfList, excursions, selectedTags, availableTags, selectedItem, imports, daysBack } from "../stores/globals.js"
import { useMountDashboard, useMountDaily, useMountCalendar, useDateTimeFormat } from "./utils.js";
import { useCreateBlotter, useCreatePnL } from "./addTrades.js"

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
import _ from 'lodash'
import { useGetTagInfo } from "./daily.js";
import axios from 'axios';
import { AuthService } from "../services/auth.js";

let trades = []
/**
 * useGetFilteredTrades
 * 
 * This function fetches all trades (via useGetTrades), then filters, processes, and enriches them
 * according to the current dashboard filters (date range, selected positions, accounts, tags, etc).
 * 
 * The main steps are:
 * 1. Fetch all trades for the current user and date range.
 * 2. Clear any previously filtered trades.
 * 3. If there are no trades, set hasData to false and exit.
 * 4. For each trade day (element), create a new object with date info and satisfaction (if on daily page).
 * 5. For each trade within the day:
 *    - Calculate price variation.
 *    - Determine if the trade matches the selected tags.
 *    - Determine if the trade is in the selected date range, position, and account.
 *    - If so, enrich the trade with tags, satisfaction, and excursion data (stopLoss, maePrice, mfePrice).
 *    - Add the trade to the filtered lists.
 * 6. Add P&L and blotter info to each filtered trade day.
 * 7. Sort the filtered trades by date descending.
 */
export async function useGetFilteredTrades() {
    console.log("\nGETTING FILTERED TRADES");
    
    try {
        // 1. Fetch all trades for the current user and date range
        await useGetTrades();

        // 2. Determine the date range for filtering
        const startDate = selectedRange.value?.start || dayjs().startOf('month').unix();
        const endDate = selectedRange.value?.end || dayjs().endOf('month').unix();
        console.log(" -> Filtering trades (" + useDateTimeFormat(startDate) + " - " + useDateTimeFormat(endDate) + ")");

        // 3. Clear previous filtered results
        filteredTrades.length = 0;
        filteredTradesDaily.length = 0;
        filteredTradesTrades.length = 0;

        console.log(`Trades available: ${trades.length}`);

        // 4. If no trades, set hasData to false and exit
        if (!trades || trades.length === 0) {
            console.log("No trades found to filter - using sample data to create structure");
            hasData.value = false;
            return;
        }

        // 5. Process and filter trades
        let loopTrades = (tradeDays) => {
            if (!tradeDays || !Array.isArray(tradeDays)) {
                console.error("Invalid tradeDays format:", tradeDays);
                hasData.value = false;
                return;
            }
            
            if (tradeDays.length > 0) hasData.value = true;
            tradeDays.forEach(day => {
                if (!day || !day.trades || !Array.isArray(day.trades)) {
                    console.warn("Invalid day format or missing trades array:", day);
                    return;
                }

                // Create a new object for the day, omitting trades, pAndL, blotter
                let tempDay = _.omit(day, ["trades", "pAndL", "blotter"]);
                tempDay.trades = [];
               
                // Add date info
                if (day.dateUnix) {
                    tempDay.date = dayjs.unix(day.dateUnix).tz(timeZoneTrade.value).date();
                    tempDay.month = dayjs.unix(day.dateUnix).tz(timeZoneTrade.value).month();
                    tempDay.year = dayjs.unix(day.dateUnix).tz(timeZoneTrade.value).year();
                } else {
                    console.warn("Day missing dateUnix:", day);
                    return;
                }

                // Add satisfaction for daily page
                if (pageId.value == "daily") {
                    tempDay.satisfaction = null;
                    for (let el of satisfactionArray) {
                        if (el.dateUnix == day.dateUnix) {
                            tempDay.satisfaction = el.satisfaction;
                            break;
                        }
                    }
                }

                // Process each trade in the day
                day.trades.forEach(trade => {
                    // Create a full copy of the trade object to preserve all properties
                    const localTrade = { ...trade };

                    // Omit excursions from the trade object
                    delete localTrade.excursions;

                    // Calculate price variation
                    localTrade.priceVar = (localTrade.side == "long")
                        ? localTrade.entryPrice - localTrade.exitPrice
                        : localTrade.exitPrice - localTrade.entryPrice;

                    // Determine if trade matches selected tags
                    let tradeTagsSelected = false;
                    let selectedTagsArray = [];
                    
                    // Make sure selectedTags.value is an array
                    if (typeof selectedTags.value === 'string') {
                        try {
                            selectedTagsArray = selectedTags.value.split(',');
                        } catch (e) {
                            console.error("Error parsing selectedTags:", e);
                            selectedTagsArray = [];
                        }
                    } else if (Array.isArray(selectedTags.value)) {
                        selectedTagsArray = selectedTags.value;
                    } else if (selectedTags.value && typeof selectedTags.value === 'object') {
                        selectedTagsArray = Object.values(selectedTags.value);
                    }
                    
                    // Find tag indices - moved outside to fix scope issues
                    let tagsIndex = tags.findIndex(obj => obj.tradeId == localTrade.id);
                    let dayTagsIndex = tags.findIndex(obj => obj.tradeId == localTrade.td);
                    
                    // If no tags are selected or "t000t" (No Tags) is selected, all trades should match
                    if (selectedTagsArray.length === 0 || selectedTagsArray.includes("t000t")) {
                        tradeTagsSelected = true;
                    } else {
                        // Check if trade has matching tags
                        if (tagsIndex != -1) {
                            if (selectedTagsArray.some(value => tags[tagsIndex].tags.find(obj => obj === value))) {
                                tradeTagsSelected = true;
                            }
                        }
                        
                        // Also check day tags
                        if (dayTagsIndex != -1 && !tradeTagsSelected) {
                            if (selectedTagsArray.some(value => tags[dayTagsIndex].tags.find(obj => obj === value))) {
                                tradeTagsSelected = true;
                            }
                        }
                    }

                    // Get satisfaction for this trade
                    let tradeSatisfaction = null;
                    for (let el of satisfactionTradeArray) {
                        if (el.tradeId == localTrade.id) {
                            tradeSatisfaction = el.satisfaction;
                            break;
                        }
                    }

                    // Check if trade is in date range and matches filters
                    const isInDateRange = (startDate === 0 && endDate === 0) 
                        ? true  // If both dates are 0, include all trades
                        : (localTrade.td || localTrade.entryTime) >= startDate && 
                          (localTrade.td || localTrade.entryTime) <= endDate;

                    if (
                        isInDateRange &&
                        selectedPositions.value.includes(localTrade.strategy) &&
                        selectedAccounts.value.includes(localTrade.account) &&
                        tradeTagsSelected
                    ) {
                        // Build tags array for this trade
                        let tempArray = [];
                        
                        // Safely check and process trade tags
                        if (tagsIndex !== -1 && tags[tagsIndex] && tags[tagsIndex].tags) {
                            for (let tagId of tags[tagsIndex].tags) {
                                for (let obj of availableTags) {
                                    for (let tag of obj.tags) {
                                        if (tag.id === tagId && selectedTagsArray.includes(tag.id)) {
                                            tempArray.push({ id: tag.id, name: tag.name });
                                        }
                                    }
                                }
                            }
                        }
                        
                        // Safely check and process day tags
                        if (dayTagsIndex !== -1 && tags[dayTagsIndex] && tags[dayTagsIndex].tags) {
                            for (let tagId of tags[dayTagsIndex].tags) {
                                for (let obj of availableTags) {
                                    for (let tag of obj.tags) {
                                        if (tag.id === tagId && selectedTagsArray.includes(tag.id)) {
                                            tempArray.push({ id: tag.id, name: tag.name });
                                        }
                                    }
                                }
                            }
                        }
                        
                        localTrade.tags = tempArray;

                        // Add satisfaction and excursion data
                        localTrade.satisfaction = tradeSatisfaction;
                        localTrade.stopLoss = null;
                        localTrade.maePrice = null;
                        localTrade.mfePrice = null;

                        let indexExcursion = excursions.findIndex(obj => obj.tradeId == localTrade.id);
                        if (indexExcursion != -1) {
                            if (excursions[indexExcursion].stopLoss) localTrade.stopLoss = excursions[indexExcursion].stopLoss;
                            if (excursions[indexExcursion].maePrice) localTrade.maePrice = excursions[indexExcursion].maePrice;
                            if (excursions[indexExcursion].mfePrice) localTrade.mfePrice = excursions[indexExcursion].mfePrice;
                        }

                        // Add to filtered lists
                        tempDay.trades.push(localTrade);
                        filteredTradesTrades.push(localTrade);
                    }
                });

                // If any trades matched, add the day to filteredTrades
                if (tempDay.trades.length > 0) {
                    filteredTrades.push(tempDay);
                    console.log("Pushed to filteredTrades:", tempDay);
                } else {
                    console.log("Skipped pushing to filteredTrades (no trades in tempDay):");
                }
            });
        };

        // 6. Run the filter process
        loopTrades(trades);
        
        console.log(`After filtering: Found ${filteredTrades.length} filtered trade days with ${filteredTradesTrades.length} total trades`);

        // 7. Enrich filtered trades with P&L and blotter info
        await useCreateBlotter(true);
        await useCreatePnL();

        let keys = Object.keys(pAndL);
        for (const key of keys) {
            let index = filteredTrades.findIndex(obj => obj.dateUnix == key);
            if (index !== -1) {
                filteredTrades[index].pAndL = pAndL[key];
                filteredTrades[index].blotter = blotter[key];
            }
        }

        // 8. Sort filtered trades by date descending
        filteredTrades.sort((a, b) => b.dateUnix - a.dateUnix);
    } catch (error) {
        console.error("Error in useGetFilteredTrades:", error);
        // Set hasData to false so UI can show appropriate message
        hasData.value = false;
        // Clear any partial results
        filteredTrades.length = 0;
        filteredTradesDaily.length = 0;
        filteredTradesTrades.length = 0;
    }
}


/***************************************
 * GETTING DATA FROM PARSE DB 
 ***************************************/
export async function useGetTrades(param) {
    return new Promise(async (resolve, reject) => {
        console.log("\nGETTING TRADES");
        console.time("  --> Duration getting trades");
        //spinnerLoadingPageText.value = "Getting trades from ParseDB"

        try {
            // Use our direct API instead of Parse
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                trades = [];
                imports.length = 0;
                resolve();
                return;
            }
            
            let url = '/api/trades';
            const params = {};
            
            if (param === "imports") {
                // For imports page, don't need to filter by date
                params.limit = 10000; // Increase limit for imports page
                params.sort = "dateUnix";
                params.sortDirection = "desc";
            } else {
                // For other pages, apply date range filters
                let startD = selectedRange.value?.start || dayjs().startOf('month').unix();
                let endD = selectedRange.value?.end || dayjs().endOf('month').unix();
                
                // Ensure dates aren't identical (add 1 day if they are)
                if (startD === endD) {
                    endD = dayjs.unix(startD).add(1, 'day').endOf('day').unix();
                }
                
                params.startDate = startD;
                params.endDate = endD;
                params.limit = queryLimit.value; // Use global limit for non-imports pages
            }
            
            // Add auth token to headers
            const headers = {
                'Authorization': `Bearer ${AuthService.token}`
            };
            
            console.log(`[Frontend] Sending Request: GET ${url}${params ? '?' + new URLSearchParams(params).toString() : ''}`);
            
            const response = await axios.get(url, { 
                params,
                headers
            });
            
            console.log(`[Frontend] Received Response: ${response.status} ${url}${params ? '?' + new URLSearchParams(params).toString() : ''}`);
            
            // Clear existing trades
            trades = [];
            imports.length = 0;
            
            // Process the response
            if (response.data && Array.isArray(response.data) && response.data.length > 0) {
                console.log(`[Frontend] Found ${response.data.length} trades in API response`);
                
                // Sample the data structure 
                console.log(`[Frontend] First trade sample fields: ${Object.keys(response.data[0]).join(', ')}`);
                console.log(`[Frontend] First trade account: ${response.data[0].account || 'undefined'}`);
                
                // Group trades by date regardless of page
                const tradesByDate = {};
                response.data.forEach(trade => {
                    if (!trade.test) { // Skip test trades
                        const dateUnix = trade.td || trade.dateUnix;
                        if (dateUnix) {
                            if (!tradesByDate[dateUnix]) {
                                tradesByDate[dateUnix] = {
                                    dateUnix,
                                    trades: []
                                };
                            }
                            tradesByDate[dateUnix].trades.push(trade);
                        }
                    }
                });
                
                // Convert to array and sort by date
                trades = Object.values(tradesByDate).sort((a, b) => b.dateUnix - a.dateUnix);
                
                if (param === "imports") {
                    imports.value = trades;
                } else {
                    imports.value = response.data.filter(trade => !trade.test); // Filter out test trades
                }
            } else {
                console.log(`[Frontend] No trades found in API response or invalid response format`);
                console.log(`[Frontend] Response data:`, response.data);
            }
            
        } catch (error) {
            console.error("Error getting trades:", error);
            trades = [];
            imports.length = 0;
        }
        
        
        console.timeEnd("  --> Duration getting trades");
        resolve();
        //console.log("trades "+JSON.stringify(trades));
    });
}

export function useGetFilteredTradesForDaily() {
    for (let index = dailyPagination.value; index < (dailyPagination.value + dailyQueryLimit.value); index++) {
        const element = filteredTradesDaily[index];
        //console.log("element "+JSON.stringify(element))
        if (!element) {
            endOfList.value = true
        } else {
            filteredTrades.push(element)
        }
    }
    //console.log("filtered trade for daily " + JSON.stringify(filteredTrades))
    dailyPagination.value = dailyPagination.value + dailyQueryLimit.value
}

/*============= Prepare Trades (#4) =============

* Here we are going to create general totals
* Create a list of all trades needed for grouping by date but also by strategy, price, etc.
* Create totals per date needed for grouping monthly, weekly and daily
***************************************/

/* List of all trades inside trades column (needed for grouping) */
let temp1 = []
/* 1b - Create a json that we push to totals */
let temp2 = {}
/* Totals per date */
let temp3 = {}

export async function useTotalTrades() {
    console.log("\nCREATING TOTAL TRADES")
    return new Promise(async (resolve, reject) => {
        /* Variables */
        temp1 = []
        temp2 = {}
        temp3 = {}

        var totalQuantity = 0

        var totalCommission = 0
        var totalOtherCommission = 0
        var totalFees = 0
        var totalLocateFees = 0
        var totalSoftwareFees = 0
        var totalBankingFees = 0

        var totalGrossProceeds = 0
        var totalGrossWins = 0
        var totalGrossLoss = 0
        var totalGrossSharePL = 0
        var totalGrossSharePLWins = 0
        var totalGrossSharePLLoss = 0
        var highGrossSharePLWin = 0
        var highGrossSharePLLoss = 0

        var totalNetProceeds = 0
        var totalNetWins = 0
        var totalNetLoss = 0
        var totalNetSharePL = 0
        var totalNetSharePLWins = 0
        var totalNetSharePLLoss = 0
        var highNetSharePLWin = 0
        var highNetSharePLLoss = 0

        var totalExecutions = 0
        var totalTrades = 0

        var totalGrossWinsQuantity = 0
        var totalGrossLossQuantity = 0
        var totalGrossWinsCount = 0
        var totalGrossLossCount = 0

        var totalNetWinsQuantity = 0
        var totalNetLossQuantity = 0
        var totalNetWinsCount = 0
        var totalNetLossCount = 0
        var financials = {}

        //console.log("filtered trades "+JSON.stringify(filteredTrades[0].trades))



        /*============= 1- CREATING GENERAL TOTALS =============
    
        * needed for dashboard
        * we start by iterating trades to created totals
        * Note: during iteration, we will also push to create a list of trades needed for grouping
        * Then we prepare a json that we push to totals
        */

        /* 1a - In each filtered trade, we will iterate trade to create totals */
        //console.log("filteredTrades  "+JSON.stringify(filteredTrades))
        filteredTrades.forEach((element, index) => {
            // Other fees
            if (element.cashJournal != undefined) {
                //console.log("cash journal " + JSON.stringify(element.cashJournal))
                totalLocateFees += element.cashJournal.locate
                totalSoftwareFees += element.cashJournal.software
                totalBankingFees += element.cashJournal.banking.fee
                //console.log("totalLocateFees" + totalLocateFees)
            }

            element.trades.forEach(el => {
                /*============= NOTE - Creating list of trades =============
    
                * at the same time, we will push each trade inside trades
                * way.value we have a list of trades that we can group 
                * according to grouping need (per date but also entry, strategy, etc.)
                */
                temp1.push(el)

                /******************** */
                
                // Validate that required properties exist and are numeric
                const validateNumericProperty = (obj, prop) => {
                    return (obj[prop] !== undefined && obj[prop] !== null && !isNaN(obj[prop])) ? obj[prop] : 0;
                };
                
                // Apply validation to each property we use in calculations
                const buyQuantity = validateNumericProperty(el, 'buyQuantity');
                const sellQuantity = validateNumericProperty(el, 'sellQuantity');
                const commission = validateNumericProperty(el, 'commission');
                const sec = validateNumericProperty(el, 'sec');
                const taf = validateNumericProperty(el, 'taf');
                const nscc = validateNumericProperty(el, 'nscc');
                const nasdaq = validateNumericProperty(el, 'nasdaq');
                
                const grossProceeds = validateNumericProperty(el, 'grossProceeds');
                const grossWins = validateNumericProperty(el, 'grossWins');
                const grossLoss = validateNumericProperty(el, 'grossLoss');
                const grossSharePL = validateNumericProperty(el, 'grossSharePL');
                const grossSharePLWins = validateNumericProperty(el, 'grossSharePLWins');
                const grossSharePLLoss = validateNumericProperty(el, 'grossSharePLLoss');
                
                const netProceeds = validateNumericProperty(el, 'netProceeds');
                const netWins = validateNumericProperty(el, 'netWins');
                const netLoss = validateNumericProperty(el, 'netLoss');
                const netSharePL = validateNumericProperty(el, 'netSharePL');
                const netSharePLWins = validateNumericProperty(el, 'netSharePLWins');
                const netSharePLLoss = validateNumericProperty(el, 'netSharePLLoss');
                
                const executionsCount = validateNumericProperty(el, 'executionsCount');
                const tradesCount = validateNumericProperty(el, 'tradesCount');
                const grossWinsQuantity = validateNumericProperty(el, 'grossWinsQuantity');
                const grossLossQuantity = validateNumericProperty(el, 'grossLossQuantity');
                const grossWinsCount = validateNumericProperty(el, 'grossWinsCount');
                const grossLossCount = validateNumericProperty(el, 'grossLossCount');
                
                const netWinsQuantity = validateNumericProperty(el, 'netWinsQuantity');
                const netLossQuantity = validateNumericProperty(el, 'netLossQuantity');
                const netWinsCount = validateNumericProperty(el, 'netWinsCount');
                const netLossCount = validateNumericProperty(el, 'netLossCount');

                // Now use validated values in calculations
                totalQuantity += buyQuantity + sellQuantity;
                totalCommission += commission;
                totalOtherCommission += sec + taf + nscc + nasdaq;
                totalFees += commission + sec + taf + nscc + nasdaq;

                totalGrossProceeds += grossProceeds;
                totalGrossWins += grossWins;
                totalGrossLoss += grossLoss;
                totalGrossSharePL += grossSharePL;
                totalGrossSharePLWins += grossSharePLWins;
                totalGrossSharePLLoss += grossSharePLLoss;

                // High values calculations remain unchanged since they compare, not sum
                if (grossSharePL >= 0) {
                    if (grossSharePL > highGrossSharePLWin) {
                        highGrossSharePLWin = grossSharePL;
                    }
                }
                if (grossSharePL < 0) {
                    if (grossSharePL < highGrossSharePLLoss) {
                        highGrossSharePLLoss = grossSharePL;
                    }
                }

                totalNetProceeds += netProceeds;
                totalNetWins += netWins;
                totalNetLoss += netLoss;
                totalNetSharePL += netSharePL;
                totalNetSharePLWins += netSharePLWins;
                totalNetSharePLLoss += netSharePLLoss;

                if (netSharePL >= 0) {
                    if (netSharePL > highNetSharePLWin) {
                        highNetSharePLWin = netSharePL;
                    }
                }
                if (netSharePL < 0) {
                    if (netSharePL < highNetSharePLLoss) {
                        highNetSharePLLoss = netSharePL;
                    }
                }

                totalExecutions += executionsCount;
                totalTrades += tradesCount;
                totalGrossWinsQuantity += grossWinsQuantity;
                totalGrossLossQuantity += grossLossQuantity;
                totalGrossWinsCount += grossWinsCount;
                totalGrossLossCount += grossLossCount;

                totalNetWinsQuantity += netWinsQuantity;
                totalNetLossQuantity += netLossQuantity;
                totalNetWinsCount += netWinsCount;
                totalNetLossCount += netLossCount;
                financials += el.financials || {};

            })


        })

        /* 1b - Create a json that we push to totals */

        /*******************
         * Info
         *******************/
        temp2.quantity = totalQuantity

        /*******************
         * Commissions and fees
         *******************/
        temp2.commission = totalCommission
        temp2.otherCommission = totalOtherCommission
        temp2.fees = totalFees
        temp2.locateFees = totalLocateFees
        temp2.softwareFees = totalSoftwareFees
        temp2.bankingFees = totalBankingFees
        temp2.otherFees = totalLocateFees + totalSoftwareFees + totalBankingFees

        /*******************
         * Gross proceeds and P&L
         *******************/
        temp2.grossProceeds = totalGrossProceeds
        temp2.grossWins = totalGrossWins
        temp2.grossLoss = totalGrossLoss
        temp2.grossSharePL = totalGrossSharePL
        /*totalGrossWinsQuantity == 0 ? temp2.grossSharePLWins = 0 : temp2.grossSharePLWins = (totalGrossWins / totalGrossWinsQuantity)
        totalGrossLossQuantity == 0 ? temp2.grossSharePLLoss = 0 : temp2.grossSharePLLoss = totalGrossLoss / totalGrossLossQuantity*/
        temp2.grossSharePLWins = totalGrossSharePLWins
        temp2.grossSharePLLoss = totalGrossSharePLLoss
        temp2.highGrossSharePLWin = highGrossSharePLWin
        temp2.highGrossSharePLLoss = highGrossSharePLLoss


        /*******************
         * Net proceeds and P&L
         *******************/
        temp2.netProceeds = totalNetProceeds
        temp2.netFeesProceeds = totalNetProceeds - temp2.otherFees
        temp2.netWins = totalNetWins
        temp2.netLoss = totalNetLoss
        temp2.netSharePL = totalNetSharePL
        /*totalNetWinsQuantity == 0 ? temp2.netSharePLWins = 0 : temp2.netSharePLWins = totalNetWins / totalNetWinsQuantity
        totalNetLossQuantity == 0 ? temp2.netSharePLLoss = 0 : temp2.netSharePLLoss = totalNetLoss / totalNetLossQuantity*/
        temp2.netSharePLWins = totalNetSharePLWins
        temp2.netSharePLLoss = totalNetSharePLLoss
        temp2.highNetSharePLWin = highNetSharePLWin
        temp2.highNetSharePLLoss = highNetSharePLLoss
        temp2.netProceedsEstimations = temp2.grossProceedsEstimations - temp2.feesEstimations
        temp2.netWinsEstimations = temp2.grossWinsEstimations - temp2.feesEstimations
        temp2.netLossEstimations = temp2.grossLossEstimations - temp2.feesEstimations


        /*******************
         * Counts
         *******************/
        temp2.executions = totalExecutions
        temp2.trades = totalTrades

        temp2.grossWinsQuantity = totalGrossWinsQuantity
        temp2.grossLossQuantity = totalGrossLossQuantity
        temp2.grossWinsCount = totalGrossWinsCount
        temp2.grossLossCount = totalGrossLossCount

        temp2.netWinsQuantity = totalNetWinsQuantity
        temp2.netLossQuantity = totalNetLossQuantity
        temp2.netWinsCount = totalNetWinsCount
        temp2.netLossCount = totalNetLossCount

        //temp2.netSharePLWins = totalNetSharePLWins
        //temp2.netSharePLLoss = totalNetSharePLLoss

        //Needed for Dashboard
        temp2.probGrossWins = (totalGrossWinsCount / totalTrades)
        temp2.probGrossLoss = (totalGrossLossCount / totalTrades)
        temp2.probNetWins = (totalNetWinsCount / totalTrades)
        temp2.probNetLoss = (totalNetLossCount / totalTrades)
        //console.log("prob net win "+temp2.probNetWins+" and loss "+temp2.probNetLoss)

        temp2.avgGrossWins = (totalGrossWins / totalGrossWinsCount)
        temp2.avgGrossLoss = -(totalGrossLoss / totalGrossLossCount)
        temp2.avgNetWins = (totalNetWins / totalNetWinsCount)
        temp2.avgNetLoss = -(totalNetLoss / totalNetLossCount)

        temp2.avgGrossSharePLWins = (totalGrossSharePLWins / totalGrossWinsCount)
        temp2.avgGrossSharePLLoss = -(totalGrossSharePLLoss / totalGrossLossCount)
        temp2.avgNetSharePLWins = (totalNetSharePLWins / totalNetWinsCount)
        temp2.avgNetSharePLLoss = -(totalNetSharePLLoss / totalNetLossCount)
        for (let key in totals) delete totals[key]
        Object.assign(totals, temp2)
        //console.log(" -> TOTALS " + JSON.stringify(totals))



        /*============= 2- RECREATING TOTALS BY DATE =============
         *
         * Create totals per date needed for grouping monthly, weekly and daily
         */

        //console.log("temp2 "+JSON.stringify(temp2))
        var z = _
            .chain(temp1)
            .orderBy(["td"], ["asc"])
            .groupBy("td")

        let objectY = JSON.parse(JSON.stringify(z))
        const keys3 = Object.keys(objectY);
        //console.log(" keys 3 "+keys3)
        for (const key3 of keys3) {
            //console.log("key 3 " + key3)
            //console.log("z "+JSON.stringify(z))
            var tempTrades = objectY[key3]
            //console.log("tempTrades " + JSON.stringify(tempTrades));
            temp3[key3] = {};

            /*******************
             * Info
             *******************/
            var sumBuyQuantity = 0
            var sumSellQuantity = 0

            /*******************
             * Commissions and fees
             *******************/
            var sumCommission = 0
            var sumSec = 0
            var sumTaf = 0
            var sumNscc = 0
            var sumNasdaq = 0
            var sumOtherCommission = 0
            var sumFees = 0

            /*******************
             * Gross proceeds and P&L
             *******************/
            var sumGrossProceeds = 0
            var sumGrossWins = 0
            var sumGrossLoss = 0
            var sumGrossSharePL = 0 //On a trade level, it's Proceeds per share traded. But as we blotter and create global P&L, it is a cumulative number (like proceeds). way.value we can calculate estimations. If we need and average per share, it's a different calculation
            var sumGrossSharePLWins = 0
            var sumGrossSharePLLoss = 0
            var highGrossSharePLWin = 0
            var highGrossSharePLLoss = 0


            /*******************
             * Net proceeds and P&L
             *******************/
            var sumNetProceeds = 0
            var sumNetWins = 0
            var sumNetLoss = 0
            var sumNetSharePL = 0
            var sumNetSharePLWins = 0
            var sumNetSharePLLoss = 0
            var highNetSharePLWin = 0
            var highNetSharePLLoss = 0

            /*******************
             * Counts
             *******************/
            var sumExecutions = 0
            var sumTrades = 0
            var sumGrossWinsQuantity = 0
            var sumGrossLossQuantity = 0
            var sumGrossWinsCount = 0
            var sumGrossLossCount = 0
            var sumNetWinsQuantity = 0
            var sumNetLossQuantity = 0
            var sumNetWinsCount = 0
            var sumNetLossCount = 0



            tempTrades.forEach(element => {
                sumBuyQuantity += element.buyQuantity
                sumSellQuantity += element.sellQuantity
                sumCommission += element.commission
                sumSec += element.sec
                sumTaf += element.taf
                sumNscc += element.nscc
                sumNasdaq += element.nasdaq
                sumOtherCommission += element.sec + element.taf + element.nscc + element.nasdaq
                sumFees += element.commission + element.sec + element.taf + element.nscc + element.nasdaq

                sumGrossProceeds += element.grossProceeds
                sumGrossWins += element.grossWins
                sumGrossLoss += element.grossLoss
                sumGrossSharePL += element.grossSharePL
                sumGrossSharePLWins += element.grossSharePLWins
                sumGrossSharePLLoss += element.grossSharePLLoss
                if (element.grossSharePL >= 0) {
                    if (element.grossSharePL > highGrossSharePLWin) {
                        highGrossSharePLWin = element.grossSharePL
                    }
                }
                if (element.grossSharePL < 0) {
                    if (element.grossSharePL < highGrossSharePLLoss) {
                        highGrossSharePLLoss = element.grossSharePL
                    }

                }

                sumNetProceeds += element.netProceeds
                sumNetWins += element.netWins
                sumNetLoss += element.netLoss
                sumNetSharePL += element.netSharePL
                sumNetSharePLWins += element.netSharePLWins
                sumNetSharePLLoss += element.netSharePLLoss
                if (element.netSharePL >= 0) {
                    if (element.netSharePL > highNetSharePLWin) {
                        highNetSharePLWin = element.netSharePL
                    }

                }
                if (element.netSharePL < 0) {
                    if (element.netSharePL < highNetSharePLLoss) {
                        highNetSharePLLoss = element.netSharePL
                    }

                }


                sumExecutions += element.executionsCount
                sumGrossWinsQuantity += element.grossWinsQuantity
                sumGrossLossQuantity += element.grossLossQuantity
                sumGrossWinsCount += element.grossWinsCount

                sumNetWinsQuantity += element.netWinsQuantity
                sumNetLossQuantity += element.netLossQuantity
                sumNetWinsCount += element.netWinsCount
                sumGrossLossCount += element.grossLossCount
                sumNetLossCount += element.netLossCount
                sumTrades += element.tradesCount

            })

            /*******************
             * Info
             *******************/
            //temp3[key3].symbol = key3;
            temp3[key3].buyQuantity = sumBuyQuantity
            temp3[key3].sellQuantity = sumSellQuantity

            /*******************
             * Commissions and fees
             *******************/
            temp3[key3].commission = sumCommission;
            temp3[key3].sec = sumSec
            temp3[key3].taf = sumTaf
            temp3[key3].nscc = sumNscc
            temp3[key3].nasdaq = sumNasdaq
            temp3[key3].otherCommission = sumOtherCommission;
            temp3[key3].fees = sumFees;
            //console.log("totalLocateFees" + JSON.stringify(temp2))

            /*******************
             * Gross proceeds and P&L
             *******************/
            temp3[key3].grossProceeds = sumGrossProceeds;
            temp3[key3].grossWins = sumGrossWins;
            temp3[key3].grossLoss = sumGrossLoss;
            temp3[key3].grossSharePL = sumGrossSharePL
            //temp3[key3].grossSharePL = sumGrossProceeds / sumBuyQuantity

            /*sumGrossWinsQuantity == 0 ? temp3[key3].grossSharePLWins = 0 : temp3[key3].grossSharePLWins = sumGrossWins / sumGrossWinsQuantity
            sumGrossLossQuantity == 0 ? temp3[key3].grossSharePLLoss = 0 : temp3[key3].grossSharePLLoss = sumGrossLoss / sumGrossLossQuantity*/
            temp3[key3].grossSharePLWins = sumGrossSharePLWins
            temp3[key3].grossSharePLLoss = sumGrossSharePLLoss
            temp3[key3].highGrossSharePLWin = highGrossSharePLWin;
            temp3[key3].highGrossSharePLLoss = highGrossSharePLLoss;

            /*******************
             * Net proceeds and P&L
             *******************/
            temp3[key3].netProceeds = sumNetProceeds;
            temp3[key3].netWins = sumNetWins;
            temp3[key3].netLoss = sumNetLoss;
            temp3[key3].netSharePL = sumNetSharePL
            //temp3[key3].netSharePL = sumNetProceeds / sumBuyQuantity

            /*sumNetWinsQuantity == 0 ? temp3[key3].netSharePLWins = 0 : temp3[key3].netSharePLWins = sumNetWins / sumNetWinsQuantity
            sumNetLossQuantity == 0 ? temp3[key3].netSharePLLoss = 0 : temp3[key3].netSharePLLoss = sumNetLoss / sumNetLossQuantity*/
            temp3[key3].netSharePLWins = sumNetSharePLWins
            temp3[key3].netSharePLLoss = sumNetSharePLLoss
            temp3[key3].highNetSharePLWin = highNetSharePLWin;
            temp3[key3].highNetSharePLLoss = highNetSharePLLoss;

            /*******************
             * Counts
             *******************/
            temp3[key3].executions = sumExecutions;
            temp3[key3].trades = sumTrades;

            temp3[key3].grossWinsQuantity = sumGrossWinsQuantity;
            temp3[key3].grossLossQuantity = sumGrossLossQuantity;
            temp3[key3].grossWinsCount = sumGrossWinsCount;
            temp3[key3].grossLossCount = sumGrossLossCount;

            temp3[key3].netWinsQuantity = sumNetWinsQuantity;
            temp3[key3].netLossQuantity = sumNetLossQuantity;
            temp3[key3].netWinsCount = sumNetWinsCount;
            temp3[key3].netLossCount = sumNetLossCount;

            /*******************
             * Financials
             *******************/
            temp3[key3].financials = tempTrades[0].financials



        }
        //console.log(" temp 3 " + JSON.stringify(temp3))
        for (let key in totalsByDate) delete totalsByDate[key]
        Object.assign(totalsByDate, temp3)
        //console.log(" -> TOTALS BY DATE " + JSON.stringify(totalsByDate))
        //console.log(" -> TOTALS BY DATE (length) " + Object.keys(totalsByDate).length)
        resolve()
    })
}

export async function useGroupTrades() {
    console.log("\nGROUPING TRADES")
    return new Promise(async (resolve, reject) => {
        /*============= 3- MISC GROUPING =============
        
        * Miscelanious grouping of trades by entry, price, etc.
        */
        var thousand = 1000
        var million = 1000000

        /*******************
         * GROUP BY DAY OF WEEK
         *******************/

        groups.day = _
            .groupBy(temp1, t => dayjs.unix(t.entryTime).day()); //temp1 is json array with trades and is created during totals
        //console.log("day  "+JSON.stringify(groups.day))

        /*******************
         * GROUP BY MONTH OF YEAR
         *******************/
        var b = _
            .groupBy(temp1, t => dayjs.unix(t.entryTime).month());
        //console.log("b "+JSON.stringify(b))

        /*******************
         * GROUP BY ENTRY TIMEFRAME
         *******************/
        groups.timeframe = _(temp1)
            .groupBy(x => {
                var secondTimeFrame = timeFrame.value
                var msTimeFrame = secondTimeFrame * 60 * 1000; /*ms*/

                //console.log("entry time " + dayjs.unix(x.entryTime).format("HH:mm"))
                //console.log(" -> Entrytime "+x.entryTime)
                let entryTF = Math.floor(x.entryTime / secondTimeFrame) * secondTimeFrame
                //console.log("  --> entryTF "+entryTF)
                var entryTimeTF = dayjs(Math.floor((+dayjs.unix(x.entryTime)) / msTimeFrame) * msTimeFrame);
                //console.log("  --> entryTimeTF "+entryTimeTF)
                return entryTimeTF.tz(timeZoneTrade.value).format("HH:mm")
            })
            .toPairs()
            .sortBy(0)
            .fromPairs()
            .value()

        //console.log("timeframe " + JSON.stringify(groups.timeframe))

        /* ==== Group by trade duration ==== */
        groups.duration = _(temp1)
            .orderBy(x => x.exitTime - x.entryTime)
            .groupBy(t => {
                // under 1mn, 1mn-2mn, 2-5mn, 5-10mn, 10-20mn, 20-40mn, 40-60mn, above 60mn
                var tradeDuration = t.exitTime - t.entryTime // in seconds  
                var tradeDurationDiv = tradeDuration / 60

                var floorDurationSeconds
                if (tradeDurationDiv < 1) {
                    floorDurationSeconds = 0 // 0-1mn
                }
                if (tradeDurationDiv >= 1 && tradeDurationDiv < 2) {
                    floorDurationSeconds = 1 // 1-2mn
                }
                if (tradeDurationDiv >= 2 && tradeDurationDiv < 5) {
                    floorDurationSeconds = 2 // 2-5mn
                }
                if (tradeDurationDiv >= 5 && tradeDurationDiv < 10) {
                    floorDurationSeconds = 5 // 5-10mn
                }
                if (tradeDurationDiv >= 10 && tradeDurationDiv < 20) {
                    floorDurationSeconds = 10 // 10-20mn
                }
                if (tradeDurationDiv >= 20 && tradeDurationDiv < 40) {
                    floorDurationSeconds = 20 // 20-40mn
                }
                if (tradeDurationDiv >= 40 && tradeDurationDiv < 60) {
                    floorDurationSeconds = 40 // 40-60mn
                }
                if (tradeDurationDiv >= 60) {
                    floorDurationSeconds = 60 // >60mn
                }
                //console.log(" -> duration " + dayjs.duration(tradeDuration * 1000).format('HH:mm:ss') + " - interval in seconds " + floorDurationSeconds + " - formated interval " + dayjs.duration(floorDurationSeconds * 1000).format('HH:mm:ss'))

                return floorDurationSeconds
            })
            .toPairs()
            .sortBy(0)
            .fromPairs()
            .value()
        //console.log("d "+JSON.stringify(groups.duration))



        /*******************
         * GROUP BY NUMBER OF TRADES
         *******************/
        groups.trades = _(temp3)
            .groupBy(x => {
                let ceilTrades
                // under 5, 6-10, 11-15, 16-20, 21-30, above 30 trades
                if (x.trades <= 30) {
                    var range = 5
                    ceilTrades = (Math.ceil(x.trades / range) * range);
                }
                if (x.trades > 30) {
                    ceilTrades = 30
                }
                //console.log(" -> trades " + x.trades +" and interval "+ceilTrades)

                return ceilTrades
            })
            .value()

        //console.log("trades " + JSON.stringify(groups.trades))

        /*******************
         * GROUP BY NUMBER OF EXECUTIONS PER TRADE
         *******************/
        groups.executions = _(temp1)
            .groupBy('executionsCount')
            .value()

        //console.log("executions " + JSON.stringify(groups.executions))

        /*******************
        * GROUP BY POSITION
        *******************/
        groups.position = _(temp1)
            .groupBy('strategy')
            .value()
        //console.log("group by position " + JSON.stringify(groups.position))

        /*******************
        * GROUP BY TAGS
        *******************/
        //console.log(" temp1 " + JSON.stringify(temp1))
        //console.log(" tags " + JSON.stringify(tags))

        // Flatten the array of tags and add the id and name properties to each tag object
        const flattenedData = temp1.reduce((acc, obj) => {
            if (obj.tags) {
                obj.tags.forEach(tag => {
                    acc.push({ ...obj, tag });
                });
            } else {
                acc.push({ ...obj, tag: { id: 'no_tags', name: 'No Tags' } });
            }
            return acc;
        }, []);

        // Group by tag id
        //console.log(" flattenedData "+JSON.stringify(flattenedData))
        flattenedData.forEach(element => {
           let tagInfo = useGetTagInfo(element.tag.id) 
           //console.log(" tagInfo "+JSON.stringify(tagInfo))
           element.tag.groupName = tagInfo.tagGroupName
           element.tag.groupId = tagInfo.tagGroupId
        });
        const groupByTag = _.groupBy(flattenedData, 'tag.id');

        // Convert the grouped data object to an object with the desired structure
        const result = Object.keys(groupByTag).reduce((acc, key) => {
            acc[key] = groupByTag[key].map(obj => ({
                tagName: obj.tag.name,
                tagGroupName: obj.tag.groupName,
                ...obj
            }));
            return acc;
        }, {});

        groups.tags = result
        //console.log("tags " + JSON.stringify(groups.tags))

        /****
         * Group by group tags and then create groups by these groups to get the tags
         */
        const groupByTagGroup = _.groupBy(flattenedData, 'tag.groupId');

        // Convert the grouped data object to an object with the desired structure
        const result2 = Object.keys(groupByTagGroup).reduce((acc, key) => {
            acc[key] = groupByTagGroup[key].map(obj => ({
                tagName: obj.tag.name,
                tagGroupName: obj.tag.groupName,
                ...obj
            }));
            return acc;
        }, {});

        //console.log(" groupByTagGroup "+JSON.stringify(groupByTagGroup))
        for (let key in result2) {
            groups[key] = _.groupBy(result2[key], 'tag.id');
        }
        
        //console.log(" groups "+JSON.stringify(groups))

        /*******************
         * GROUP BY SYMBOL
         *******************/
        groups.symbols = _(temp1)
            .groupBy('symbol')
            .value()

        /*******************
         * GROUP BY PUBLIC FLOAT
         *******************/
        let path = "financials.publicFloat";
        groups.shareFloat = _(temp1)
            .filter(object => _.has(object, path))
            .groupBy(x => {
                let ceilFloor
                var publicFloatFinviz = x.financials.publicFloat.finviz
                if (publicFloatFinviz != "-") {
                    //console.log("public float (finviz) " + JSON.stringify(publicFloatFinviz))

                    // under 10M, 10-20M, 20-30, 30-50, above 50M float
                    if (publicFloatFinviz < 20 * million) {
                        var range = 5 * 1000000
                        ceilFloor = (Math.floor(publicFloatFinviz / range) * range);
                    }
                    if ((publicFloatFinviz >= 20 * million) && (publicFloatFinviz < 50 * million)) {
                        var range = 10 * 1000000
                        ceilFloor = (Math.floor(publicFloatFinviz / range) * range);
                    }
                    if (publicFloatFinviz >= 50 * million) {
                        ceilFloor = 50 * million
                    }
                    //console.log(" -> trades " + x.trades +" and interval "+ceilFloor)

                    return ceilFloor
                }
            })
            .value()

        //console.log("group by share float " + JSON.stringify(groups.shareFloat))

        /*******************
         * GROUP BY MARKET CAP
         *******************/
        groups.mktCap = _(temp1)
            .filter(object => _.has(object, path))
            .groupBy(x => {
                let ceilTrades
                var mktCap = x.financials.mktCap
                if (mktCap != null) {
                    //console.log("mktCap " + mktCap)
                    //Mega-cap: Market cap of $200 billion and greater
                    //Big-cap: $10 billion and greater
                    //Mid-cap: $2 billion to $10 billion
                    //Small-cap: $300 million to $2 billion
                    //Micro-cap: $50 million to $300 million
                    //Nano-cap: Under $50 million
                    if (mktCap <= 50 * 1000000) {
                        ceilTrades = 50 * 1000000
                    }
                    if (mktCap > 50 * 1000000 && mktCap <= 300 * 1000000) {
                        ceilTrades = 300 * 1000000
                    }
                    if (mktCap > 300 * 1000000 && mktCap <= 2000 * 1000000) {
                        ceilTrades = 2000 * 1000000
                    }
                    if (mktCap > 2000 * 1000000 && mktCap <= 10000 * 1000000) {
                        ceilTrades = 10000 * 1000000
                    }
                    if (mktCap > 10000 * 1000000) {
                        ceilTrades = 10001 * 1000000
                    }
                    //console.log(" -> interval "+ceilTrades)

                    return ceilTrades
                }
            })
            .value()

        //console.log("group by mktCap " + JSON.stringify(groups.mktCap))


        /*******************
         * GROUP BY ENTRYPRICE
         *******************/
        groups.entryPrice = _(temp1)
            .groupBy(x => {
                // under 5, 5-9.99, 10-14.99, 15-19.99, 20-29.99, above 30 trades
                let floorNum
                if (x.entryPrice < 30) {
                    var range = 5
                    floorNum = (Math.floor(x.entryPrice / range) * range);
                }
                if (x.entryPrice >= 30) {
                    floorNum = 30
                }
                //console.log(" -> Entry price "+x.entryPrice+" and interval "+floor)

                return floorNum
            })
            .value()
        //console.log("group by entryprice " + JSON.stringify(groups.entryPrice))
        resolve()
    })
}

/***************************************
         * GETTING AND CALCULATING MFE
         ***************************************/
//get data from excursions db
export async function useCalculateProfitAnalysis(param) {
    console.log("\nCALCULATING PROFIT ANALYSIS")
    return new Promise(async (resolve, reject) => {
        //console.log(" -> Getting MFE Prices")
        let mfePricesArray = []
        for (let key in profitAnalysis) delete profitAnalysis[key]
        mfePricesArray = excursions
        //console.log("  --> MFE prices array "+JSON.stringify(mfePricesArray))
        /*console.log(" -> Getting average quantity")
        let averageQuantity = totals.quantity / 2 / totals.trades
        console.log("  --> Average quantity "+averageQuantity)*/
        //console.log(" totals "+JSON.stringify(totals))
        if (JSON.stringify(totals) != '{}') {
            // Debug the values needed for calculations
            console.log("Debugging profit analysis calculations:");
            console.log(`totals.grossSharePLWins = ${totals.grossSharePLWins}`);
            console.log(`totals.grossWinsCount = ${totals.grossWinsCount}`);
            console.log(`totals.grossSharePLLoss = ${totals.grossSharePLLoss}`);
            console.log(`totals.grossLossCount = ${totals.grossLossCount}`);
            console.log(`totals.highGrossSharePLWin = ${totals.highGrossSharePLWin}`);
            
            //console.log(" -> Calculating profit loss ratio risk&reward and MFE")
            //console.log(" -> Calculating gross and net Average Win Per Share")
            profitAnalysis.grossAvWinPerShare = totals.grossWinsCount > 0 ? (totals.grossSharePLWins / totals.grossWinsCount) : 0;
            profitAnalysis.netAvWinPerShare = totals.netWinsCount > 0 ? (totals.netSharePLWins / totals.netWinsCount) : 0;
            console.log(`Calculated profitAnalysis.grossAvWinPerShare = ${profitAnalysis.grossAvWinPerShare}`);
            console.log(`Calculated profitAnalysis.netAvWinPerShare = ${profitAnalysis.netAvWinPerShare}`);
            
            //console.log(" -> Calculating gross and net Average Loss Per Share")
            profitAnalysis.grossAvLossPerShare = totals.grossLossCount > 0 ? (-totals.grossSharePLLoss / totals.grossLossCount) : 0;
            profitAnalysis.netAvLossPerShare = totals.netLossCount > 0 ? (-totals.netSharePLLoss / totals.netLossCount) : 0;
            //console.log("  --> Gross Average Loss Per Share "+grossAvLossPerShare+" and net "+netAvLossPerShare)

            //console.log(" -> Calculating gross and net Highest Win Per Share")
            profitAnalysis.grossHighWinPerShare = totals.highGrossSharePLWin || 0;
            profitAnalysis.netHighWinPerShare = totals.highNetSharePLWin || 0;
            //console.log("  --> Gross Highest Win Per Share "+grossHighWinPerShare+" and net stop loss "+netHighWinPerShare)

            //console.log(" -> Calculating gross and net Highest Loss Per Share")
            profitAnalysis.grossHighLossPerShare = totals.highGrossSharePLLoss ? -totals.highGrossSharePLLoss : 0;
            profitAnalysis.netHighLossPerShare = totals.highNetSharePLLoss ? -totals.highNetSharePLLoss : 0;
            //console.log("  --> Gross Highest Loss Per Share "+grossHighLossPerShare+" and net stop loss "+netHighLossPerShare)

            // Calculate Win/Loss ratio (R-ratio) - this is Average Win divided by Average Loss
            // A ratio > 1 means your average wins are larger than your average losses (good)
            // A ratio < 1 means your average losses are larger than your average wins (bad)
            profitAnalysis.grossR = profitAnalysis.grossAvLossPerShare > 0 ? (profitAnalysis.grossAvWinPerShare / profitAnalysis.grossAvLossPerShare) : 0;
            profitAnalysis.netR = profitAnalysis.netAvLossPerShare > 0 ? (profitAnalysis.netAvWinPerShare / profitAnalysis.netAvLossPerShare) : 0;
            
            // Add descriptive properties for UI clarity
            profitAnalysis.grossWinLossRatio = profitAnalysis.grossR;
            profitAnalysis.netWinLossRatio = profitAnalysis.netR;
            //console.log("  --> Gross R " + profitAnalysis.grossR + " and net R " + profitAnalysis.netR)

            // Calculate Profit Factor - this is Total Wins divided by Total Losses
            // Similar to R-ratio but using total dollars instead of per-share average
            // A factor > 1 means you're profitable, < 1 means you're losing money
            const grossWins = totals.grossWins || 0;
            const grossLoss = -totals.grossLoss || 0; // Make loss positive for division
            const netWins = totals.netWins || 0;
            const netLoss = -totals.netLoss || 0; // Make loss positive for division
            
            profitAnalysis.grossProfitFactor = grossLoss > 0 ? grossWins / grossLoss : 0;
            profitAnalysis.netProfitFactor = netLoss > 0 ? netWins / netLoss : 0;
            
            console.log(`Calculated profitAnalysis.grossProfitFactor = ${profitAnalysis.grossProfitFactor}`);
            console.log(`Calculated profitAnalysis.netProfitFactor = ${profitAnalysis.netProfitFactor}`);

            //console.log(" -> Calculating gross and net mfe R")
            //console.log(" -> Filtered trades "+JSON.stringify(filteredTrades.trades))
            let grossMfeRArray = []
            let netMfeRArray = []

            mfePricesArray.forEach(element => {

                //console.log(" -> Filtered trades "+JSON.stringify(filteredTrades))
                if (filteredTrades.length > 0) {
                    //console.log(" filteredTrades "+JSON.stringify(filteredTrades))
                    //console.log(" date unix "+element.dateUnix)
                    let tradeFilter = filteredTrades.find(x => x.dateUnix == element.dateUnix)
                    //console.log(" tradeFilter "+JSON.stringify(tradeFilter))
                    if (tradeFilter != undefined) {
                        //console.log(" tradeFilter " + JSON.stringify(tradeFilter))
                        let trade = tradeFilter.trades.find(x => x.id == element.tradeId)
                        if (trade != undefined) {
                            //console.log(" -> Trade " + JSON.stringify(trade))
                            let tradeEntryPrice = trade.entryPrice
                            //console.log(" Entry price " + tradeEntryPrice + " | MFE Price " + element.mfePrice)
                            let entryMfeDiff
                            trade.strategy == "long" ? entryMfeDiff = (element.mfePrice - tradeEntryPrice) : entryMfeDiff = (tradeEntryPrice - element.mfePrice)
                            let grossMfeR = entryMfeDiff / profitAnalysis.grossAvLossPerShare
                            //console.log("  --> Strategy "+trade.strategy+", entry price : "+tradeEntryPrice+", mfe price "+element.mfePrice+", diff "+entryMfeDiff+" and grosmfe R "+grossMfeR)
                            grossMfeRArray.push(grossMfeR)
                            let netMfeR = entryMfeDiff / profitAnalysis.netAvLossPerShare
                            netMfeRArray.push(netMfeR)
                        }
                    }
                }
            })
            //console.log("  --> Gross mfeArray " + grossMfeRArray + " and net " + netMfeRArray)

            //console.log(" -> Getting gross and net win rate")
            let grossWin = totals.probGrossWins
            let netWin = totals.probNetWins
            //console.log("  --> Gross win "+grossWin+" and net win "+netWin)

            //console.log(" -> Calculating gross and net current expected return")
            let grossCurrExpectReturn = profitAnalysis.grossR * grossWin
            let netCurrExpectReturn = profitAnalysis.netR * netWin
            //console.log("  --> Gross current expected return "+grossCurrExpectReturn+" and net "+netCurrExpectReturn)

            //console.log(" -> Calculating mfe expected return")
            const takeProfitRLevels = []
            for (let index = 1; index <= 20; index += 0.5) {
                takeProfitRLevels.push(index)

            }

            let profitTakingAnalysis = []
            let grossMfeRArrayLength = grossMfeRArray.length
            let netMfeRArrayLength = netMfeRArray.length
            let previousGrossExpectReturn = 0
            let previousNetExpectReturn = 0
            let tempGrossMfeR
            let tempGrossExpectedReturn = 0
            let tempNetMfeR
            let tempNetExpectedReturn = 0
            takeProfitRLevels.forEach(element => {
                let temp = {}
                let occurenceGross = grossMfeRArray.filter(x => x >= element).length
                let occurenceNet = netMfeRArray.filter(x => x >= element).length
                temp.rLevel = element
                temp.winRateGross = occurenceGross / grossMfeRArrayLength
                temp.grossExpectReturn = temp.winRateGross * element
                temp.winRateNet = occurenceNet / netMfeRArrayLength
                temp.netExpectReturn = temp.winRateNet * element
                if (temp.grossExpectReturn > previousGrossExpectReturn) {
                    previousGrossExpectReturn = temp.grossExpectReturn
                    tempGrossMfeR = element
                    tempGrossExpectedReturn = temp.grossExpectReturn
                }
                if (temp.netExpectReturn > previousNetExpectReturn) {
                    previousNetExpectReturn = temp.netExpectReturn
                    tempNetMfeR = element
                    tempNetExpectedReturn = temp.netExpectReturn
                }
                profitTakingAnalysis.push(temp)
            });
            //console.log("  --> Profit Taking Analysis "+JSON.stringify(profitTakingAnalysis))
            //console.table(profitTakingAnalysis)
            profitAnalysis.grossMfeR = null
            profitAnalysis.netMfeR = null
            if (tempGrossExpectedReturn > grossCurrExpectReturn) profitAnalysis.grossMfeR = tempGrossMfeR
            if (tempNetExpectedReturn > netCurrExpectReturn) profitAnalysis.netMfeR = tempNetMfeR

            //console.log("  --> Gross MFE " + profitAnalysis.grossMfeR + " and net " + profitAnalysis.netMfeR)
            //console.log("  --> Profit analysis " + JSON.stringify(profitAnalysis))
        }

        resolve()
    })
}

async function calculateSatisfaction(param) {
    console.log("\nCALCULATING SATISFACTION")
    return new Promise(async (resolve, reject) => {
        console.log(" -> Getting Satisfactions")
        const parseObject = Parse.Object.extend("satisfactions");
        const query = new Parse.Query(parseObject);
        query.equalTo("user", Parse.User.current())
        query.greaterThanOrEqualTo("dateUnix", selectedDateRange.value.start)
        query.lessThanOrEqualTo("dateUnix", selectedDateRange.value.end)
        query.ascending("order");
        query.limit(queryLimit.value); // limit to at most 10 results
        mfePricesArray = []
        const results = await query.find();
        mfePricesArray = JSON.parse(JSON.stringify(results))
        //console.log("  --> MFE prices "+mfePricesArray)
        resolve()
    })
}

export async function useRefreshTrades() {
    console.log("\nREFRESHING INFO")
    await (spinnerLoadingPage.value = true)
    if (pageId.value == "dashboard") {
        useMountDashboard()
    } else if (pageId.value == "daily") {
        useMountDaily()
    } else if (pageId.value == "calendar") {
        useMountCalendar()
    } else {
        window.location.href = "/dashboard"
    }
}

/***************************************
* IMPORTS
***************************************/

export const useDeleteTrade = async () => {
    return new Promise(async (resolve, reject) => {
        //console.log("screenshot "+JSON.stringify(screenshots))

        /* Now, let's delete screenshot */

        const parseObject = Parse.Object.extend("trades");
        const query = new Parse.Query(parseObject);
        query.equalTo("dateUnix", selectedItem.value);
        const results = await query.first();

        if (results) {
            await results.destroy()
            console.log('  --> Deleted trade with id ' + results.id)
            useGetTrades("imports")
            resolve()
        } else {
            alert("There was problem with deleting trade")
            reject("There was problem with deleting trade")
        }
    })
}

export const useDeleteExcursions = async () => {
    return new Promise(async (resolve, reject) => {

        const parseObject = Parse.Object.extend("excursions");
        const query = new Parse.Query(parseObject);
        query.equalTo("dateUnix", selectedItem.value);
        const results = await query.find();

        if (results.length > 0) {
            try {
                // Destroy each object in the results array
                await Promise.all(results.map(result => result.destroy()));
                console.log('  --> Deleted excursions with ids ' + results.map(result => result.id).join(', '));
                resolve();
            } catch (error) {
                alert("There was a problem with deleting excursions");
                reject(error);
            }
        } else {
            console.log("No excursions found to delete");
        }
    })
}

