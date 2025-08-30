import { renderingCharts, pageId, filteredTrades, selectedMonth, calendarData, miniCalendarsData, timeZoneTrade, filteredTradesDaily } from "../stores/globals.js"
import { useMonthFormat } from "./utils.js"
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
import calendarize from 'calendarize';

// Flag to track if calendar is already loading
let isLoadingCalendar = false;

export async function useLoadCalendar() {
    console.log("\nLOADING CALENDAR");
    
    // Prevent duplicate calls while calendar is loading
    if (isLoadingCalendar) {
        console.log("Calendar is already loading, skipping duplicate call");
        return Promise.resolve();
    }
    
    isLoadingCalendar = true;
    
    return new Promise(async (resolve, reject) => {
        try {
            renderingCharts.value = true;
            miniCalendarsData.length = 0;
            
            // Initialize calendarData if it doesn't already exist
            if (!calendarData.value) {
                calendarData.value = {};
            }
            
            let currentMonthNumber = dayjs(selectedMonth.value.start * 1000).tz(timeZoneTrade.value).month();
            let tradesArray = [];

            tradesArray = filteredTrades;
            
            // Debug: Check if we have trades to display
            console.log(`Calendar: Found ${tradesArray.length} days with trades to display`);
            if (tradesArray.length > 0) {
                // Show first few trade days to debug
                tradesArray.slice(0, 3).forEach((day, i) => {
                    console.log(`Calendar: Day ${i+1} - dateUnix: ${day.dateUnix}, date: ${dayjs.unix(day.dateUnix).format('YYYY-MM-DD')}`);
                    console.log(`Calendar: Day ${i+1} - trades: ${day.trades ? day.trades.length : 'undefined'}`);
                    console.log(`Calendar: Day ${i+1} - pAndL: ${day.pAndL ? JSON.stringify(day.pAndL) : 'undefined'}`);
                });
            } else {
                console.warn("Calendar: No filtered trades available to display");
            }

        const createCalendar = async (param1, param2) => {
            try {
                // Ensure we're working with the correct timezone and format
                const selectedDate = dayjs.unix(param1).tz(timeZoneTrade.value);
                const dateForCalendarize = new Date(selectedDate.format('YYYY-MM-DD'));
                let calendarizeData = calendarize(dateForCalendarize, 1);

                // Get the correct month and year values directly from the dayjs object
                let month = selectedDate.month() + 1; // month is 0-indexed in dayjs
                let year = selectedDate.year();
                
                let calendarJson = {};

                // Check if the current date is today
                const today = dayjs().tz(timeZoneTrade.value);
                const todayDay = today.date();
                const todayMonth = today.month() + 1;
                const todayYear = today.year();
                
                console.log(`Calendar: Creating calendar for ${year}-${month} (Month: ${selectedDate.format('MMMM')})`);

                // Create a map of dateUnix to trade day for faster lookup
                const tradeDayMap = {};
                tradesArray.forEach(day => {
                    if (day.dateUnix) {
                        tradeDayMap[day.dateUnix] = day;
                    }
                });
                console.log(`Calendar: Created lookup map with ${Object.keys(tradeDayMap).length} days`);

                for (let index1 = 0; index1 < calendarizeData.length; index1++) {
                    let element = calendarizeData[index1];
                    calendarJson[index1] = [];
                    
                    for (let index = 0; index < element.length; index++) {
                        const dayNumber = calendarizeData[index1][index];
                        let tempData = {};
                        tempData.month = useMonthFormat(param1);
                        tempData.day = dayNumber;

                        // Check if this day is today
                        tempData.isToday = (dayNumber === todayDay && month === todayMonth && year === todayYear);

                        if (dayNumber !== 0) {
                            // Construct the date string with consistent format
                            const elementDate = `${year}-${String(month).padStart(2, '0')}-${String(dayNumber).padStart(2, '0')}`;
                            tempData.date = elementDate;
                            
                            // Calculate the Unix timestamp for the start of this calendar day
                            // Use dayjs to ensure proper timezone handling
                            const currentDayUnix = dayjs(elementDate).tz(timeZoneTrade.value).startOf('day').unix();

                            // Find the corresponding day in filteredTrades (tradesArray)
                            const matchingTradeDay = tradeDayMap[currentDayUnix] || 
                                tradesArray.find(tradeDay => tradeDay.dateUnix === currentDayUnix);

                            if (matchingTradeDay) {
                                tempData.pAndL = matchingTradeDay.pAndL;
                                tempData.satisfaction = matchingTradeDay.satisfaction;
                                tempData.tradeList = matchingTradeDay.trades;
                                
                                // Debug info for days with trades
                                if (matchingTradeDay.pAndL) {
                                    console.log(`Calendar: Found trades for ${tempData.date} - ${matchingTradeDay.pAndL.trades} trades, P&L: ${matchingTradeDay.pAndL.grossProceeds}`);
                                }
                            } else {
                                tempData.pAndL = {}; // Use an empty object for consistency
                                tempData.tradeList = []; // Ensure tradeList is always present
                            }
                        } else {
                            tempData.date = null; // Set to null if it's a filler day
                            tempData.pAndL = {}; // Use an empty object for consistency
                            tempData.tradeList = []; // Ensure tradeList is always present
                        }
                        calendarJson[index1].push(tempData);
                    }
                }

                if (param1 === selectedMonth.value.start) {
                    // Create a new object and assign it to calendarData.value
                    // This ensures reactivity is triggered for the entire object replacement
                    calendarData.value = {...calendarJson};
                    console.log("Calendar data updated:", Object.keys(calendarData.value).length);
                } else {
                    miniCalendarsData.unshift(calendarJson);
                }
            } catch (error) {
                console.error("Error in createCalendar:", error);
            }
        }

            if (pageId.value == 'calendar') {
                let i = 0;
                while (i <= currentMonthNumber) {
                    let tempUnix = dayjs(selectedMonth.value.start * 1000).tz(timeZoneTrade.value).subtract(i, 'month').startOf('month').unix();
                    await createCalendar(tempUnix);
                    i++;
            }
        } else {
                await createCalendar(selectedMonth.value.start);
            }
            
            // Ensure calendarData is defined after processing
            if (!calendarData.value || Object.keys(calendarData.value).length === 0) {
                console.warn("Calendar data is empty after processing, initializing empty structure");
                calendarData.value = { 0: [] };
            }
            
            resolve();
        } catch (error) {
            console.error("Error loading calendar:", error);
            reject(error);
        } finally {
            isLoadingCalendar = false;
        }
    });
}