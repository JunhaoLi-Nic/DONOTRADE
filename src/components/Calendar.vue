<script setup>
import { pageId, selectedMonth, selectedPlSatisfaction, amountCase, calendarData, miniCalendarsData, timeZoneTrade, spinnerLoadingPage, selectedPeriodRange } from '../stores/globals';
import { useThousandCurrencyFormat, useMountCalendar, useMountDaily, validateDateTimestamp } from '../utils/utils';
import { useGetFilteredTrades } from '../utils/trades';
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
import { useRouter } from 'vue-router';
import { computed, onMounted, watch, ref } from 'vue';
import TradeDetailsModal from './TradeDetailsModal.vue';

const router = useRouter();
const days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];

// Add previousMonthKey for tracking month changes
const previousMonthKey = ref('');

// State for the modal
const isModalVisible = ref(false);
const selectedDayTrades = ref([]);
const selectedDayDate = ref('');

// Computed property to safely access calendar month
const currentMonth = computed(() => {
    if (calendarData.value && calendarData.value[0] && calendarData.value[0][0]) {
        return calendarData.value[0][0].month;
    }
    return dayjs.unix(selectedMonth.value.start).format("MMMM YYYY");
});

// Make sure we have the correct case for amount (gross/net)
const currentAmountCase = computed(() => {
    return amountCase.value || 'gross';
});

// Force a calendar refresh on component mount
onMounted(() => {
    // If calendarData is empty but we have a valid selectedMonth, force a refresh
    if ((!calendarData.value || Object.keys(calendarData.value).length === 0) && selectedMonth.value) {
        monthLastNext(0); // Refresh without changing month
    }
});

async function monthLastNext(param) {
    spinnerLoadingPage.value = true;
    
    // Get the current start timestamp
    const currentStart = selectedMonth.value.start;
    
    // Calculate new month based on param (-1 for previous month, 1 for next month)
    const newStart = dayjs.tz(currentStart * 1000, timeZoneTrade.value).add(param, 'month').startOf('month').unix();
    const newEnd = dayjs.tz(newStart * 1000, timeZoneTrade.value).endOf('month').unix();
    
    // Log the month change
    console.log(`Calendar: Changing month from ${dayjs.unix(currentStart).format('MMMM YYYY')} to ${dayjs.unix(newStart).format('MMMM YYYY')}`);
    
    // Validate the dates (ensure they're not in future, etc.)
    const validatedDates = validateDateTimestamp({ start: newStart, end: newEnd });
    
    // Update the global selectedMonth
    selectedMonth.value.start = validatedDates.start;
    selectedMonth.value.end = validatedDates.end;
    
    // Store in localStorage for persistence
    localStorage.setItem('selectedMonth', JSON.stringify(selectedMonth.value));
    
    // Based on current page, update the appropriate view
    if (pageId.value == "calendar") {
        useMountCalendar();
    }

    if (pageId.value == "daily") {
        // Update selectedPeriodRange to match the new month
        if (selectedPeriodRange && selectedPeriodRange.value) {
            selectedPeriodRange.value.start = validatedDates.start;
            selectedPeriodRange.value.end = validatedDates.end;
            localStorage.setItem('selectedPeriodRange', JSON.stringify(selectedPeriodRange.value));
            console.log(`Daily: Updated selectedPeriodRange to match new month: ${dayjs.unix(validatedDates.start).format('MMMM YYYY')}`);
        }
        
        useMountDaily();
    }
}

// Ensure we have proper data when opening trade details modal
function showTradeDetails(day) {
  console.log("Showing trade details for day:", day);
  if (day && day.tradeList && day.tradeList.length > 0) {
    selectedDayTrades.value = day.tradeList;
    selectedDayDate.value = day.date;
    isModalVisible.value = true;
    console.log("Opening modal with trades:", selectedDayTrades.value);
  } else if (day && day.pAndL && day.pAndL.trades === 0) {
    console.log("Day has P&L but no trades");
    // If you want to navigate on days with $0 P&L but no trades, handle it here.
  } else {
    console.log("No trade data found for this day");
  }
}

function navigateToDaily(day) {
    if (day.pAndL) {
        router.push(`/daily/${day.date}`);
    }
}

// Helper function to check trade data - used in template
function logDayData(dayData) {
    console.log("Calendar day data:", dayData);
    console.log(`Checking day ${dayData.date} - Has pAndL: ${!!dayData.pAndL}, Amount: ${dayData.pAndL ? dayData.pAndL[currentAmountCase.value + 'Proceeds'] : 'N/A'}`);
    return true; // Always return true to not affect rendering
}

// Create a watch to update when selectedMonth changes from outside this component
watch(() => selectedMonth.value, (newValue) => {
  console.log("Calendar: selectedMonth changed externally:", newValue);
  if (newValue && newValue.start && newValue.end) {
    // Generate a key for the current month value
    const currentKey = JSON.stringify(newValue);
    
    // Skip if we've already processed this month
    if (previousMonthKey.value === currentKey) {
      console.log("Calendar: Skipping duplicate month update");
      return;
    }
    
    // Log current calendar month
    const currentMonthDisplay = dayjs.unix(newValue.start).format("MMMM YYYY");
    console.log("Updating calendar to show month:", currentMonthDisplay);
    
    // Store the key to prevent duplicate processing
    previousMonthKey.value = currentKey;
    
    // Force refresh calendar with new month
    spinnerLoadingPage.value = true;
    
    // Set a small delay to ensure UI updates properly
    setTimeout(async () => {
      try {
        // Just use useMountCalendar which will handle everything including getting trades
        await useMountCalendar();
        console.log("Calendar refreshed for new month:", currentMonthDisplay);
      } catch (error) {
        console.error("Error updating calendar for month change:", error);
      } finally {
        spinnerLoadingPage.value = false;
      }
    }, 100);
  }
}, { deep: true });
</script>
<template>
    <div class="calendar-container">
        <div class="calendar-header">
            <i class="uil uil-angle-left-b pointerClass" @click="monthLastNext(-1)"></i>
            <h2>{{ currentMonth }}</h2>
            <i class="uil uil-angle-right-b pointerClass" @click="monthLastNext(1)"></i>
        </div>

        <div class="calendar-grid" v-if="calendarData.value && Object.keys(calendarData.value).length">
            <div class="calendar-day-name" v-for="day in days" :key="day">{{ day }}</div>
            <template v-for="lineKey in Object.keys(calendarData.value)" :key="lineKey">
                <div v-for="dayData in calendarData.value[lineKey]" :key="dayData.date" class="calendar-day" :class="[{
                    'is-today': dayData.isToday,
                    'is-active': dayData.pAndL && (dayData.pAndL[currentAmountCase + 'Proceeds'] !== 0),
                    'is-positive': selectedPlSatisfaction == 'pl' 
                        ? (dayData.pAndL && dayData.pAndL[currentAmountCase + 'Proceeds'] > 0) 
                        : (dayData.satisfaction == true && dayData.pAndL && dayData.pAndL[currentAmountCase + 'Proceeds'] !== 0),
                    'is-negative': selectedPlSatisfaction == 'pl' 
                        ? (dayData.pAndL && dayData.pAndL[currentAmountCase + 'Proceeds'] < 0) 
                        : (dayData.satisfaction == false && dayData.pAndL && dayData.pAndL[currentAmountCase + 'Proceeds'] !== 0),
                    'is-clickable': dayData.pAndL && (dayData.pAndL[currentAmountCase + 'Proceeds'] !== 0)
                }]" @click="showTradeDetails(dayData)" data-bs-toggle="tooltip" data-bs-html="true" :title="dayData.pAndL && (dayData.pAndL[currentAmountCase + 'Proceeds'] !== 0) ? `${dayData.pAndL.trades} trades <br> ${useThousandCurrencyFormat(parseInt(dayData.pAndL[currentAmountCase + 'Proceeds'] || 0))}` : ''">
                    <div class="day-number">
                        {{ dayData.day }}
                    </div>
                    <div class="day-details" v-if="dayData.pAndL && (dayData.pAndL[currentAmountCase + 'Proceeds'] !== 0)">
                        <p class="trades">{{ dayData.pAndL.trades }} trades</p>
                        <p class="pnl">{{ useThousandCurrencyFormat(parseInt(dayData.pAndL[currentAmountCase + 'Proceeds'] || 0)) }}</p>
                    </div>
                </div>
            </template>
        </div>
        <div v-else class="calendar-loading">
            Loading calendar data...
        </div>
    </div>

    <div class="mini-calendars-container" v-if="pageId === 'calendar' && miniCalendarsData.length > 0">
        <div class="mini-calendar" v-for="(calData, idx) in miniCalendarsData" :key="idx">
            <h3>{{ calData[0] && calData[0][0] ? calData[0][0].month : '' }}</h3>
            <div class="mini-calendar-grid">
                <div class="mini-calendar-day-name" v-for="day in days" :key="day">{{ day }}</div>
                <template v-for="(line, lineIdx) in calData" :key="lineIdx">
                    <div v-for="(dayData, dayIdx) in line" :key="dayIdx" class="mini-calendar-day" :class="[{
                        'is-active': dayData.pAndL,
                        'is-positive': selectedPlSatisfaction == 'pl' ? (dayData.pAndL && dayData.pAndL[currentAmountCase + 'Proceeds'] >= 0) : dayData.satisfaction == true,
                        'is-negative': selectedPlSatisfaction == 'pl' ? (dayData.pAndL && dayData.pAndL[currentAmountCase + 'Proceeds'] < 0) : dayData.satisfaction == false,
                    }]">
                        {{ dayData.day }}
                    </div>
                </template>
            </div>
        </div>
    </div>
    
    <TradeDetailsModal 
      :is-open="isModalVisible" 
      :date-unix="selectedDayDate" 
      :trade="selectedDayTrades && selectedDayTrades.length > 0 ? selectedDayTrades[0] : null"
      :trade-index="0"
      @close="isModalVisible = false" 
      @save="isModalVisible = false"
    />
</template>

<style scoped>
.calendar-container {
    background-color: #22272e; /* Dark slate */
    padding: 15px;
    border-radius: 10px;
    color: #adbac7; /* Lighter text for better contrast */
    max-width: 900px;
    margin: auto;
    border: 1px solid #444c56;
    box-shadow: 0 6px 20px rgba(0,0,0,0.4);
    position: relative;
    z-index: 1; /* Low z-index to prevent dropdown overlap */
}

.calendar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
}

.calendar-header h2 {
    font-size: 1.4rem;
    font-weight: 600;
    color: #fff;
}

.calendar-header .pointerClass {
    font-size: 1.6rem;
    color: #58a6ff;
    transition: transform 0.2s ease, color 0.2s ease;
}

.calendar-header .pointerClass:hover {
    transform: scale(1.2);
    color: #79c0ff;
}

.calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 5px; /* Re-introduce a gap */
}

.calendar-day-name {
    text-align: center;
    font-weight: 600;
    color: #768390;
    font-size: 0.8rem;
    padding-bottom: 10px;
    text-transform: uppercase;
}

.calendar-day {
    background-color: #2d333b;
    border-radius: 6px;
    border: 1px solid #444c56;
    padding: 8px;
    min-height: 100px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.2s ease-in-out;
    cursor: default;
}

.calendar-loading {
    text-align: center;
    padding: 40px;
    color: #768390;
    font-style: italic;
    font-size: 1rem;
}

.calendar-day.is-clickable {
    cursor: pointer;
}

.calendar-day.is-clickable:hover {
    transform: translateY(-4px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
    border-color: #58a6ff;
}

.calendar-day.is-today {
    border: 2px solid #58a6ff;
    background-color: #324152;
}

.calendar-day.is-active {
    color: #fff;
}

.calendar-day.is-active.is-positive {
    background-color: rgba(34, 197, 94, 0.2);
    border-color: rgba(34, 197, 94, 0.7);
}

.calendar-day.is-active.is-negative {
    background-color: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.7);
}

.day-number {
    font-size: 0.9rem;
    font-weight: 500;
    color: #adbac7;
}

.is-today .day-number {
    color: #fff;
    font-weight: 700;
}

.day-details {
    text-align: right;
}

.day-details .trades {
    font-size: 0.7rem;
    color: #adbac7;
    opacity: 0.8;
}

.day-details .pnl {
    font-size: 1rem;
    font-weight: 700;
}

.is-positive .pnl {
    color: #22c55e;
}

.is-negative .pnl {
    color: #ef4444;
}

.mini-calendars-container {
    margin-top: 20px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
}

.mini-calendar {
    background-color: #22272e;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #444c56;
}

.mini-calendar h3 {
    font-size: 1rem;
    margin-bottom: 8px;
    text-align: center;
    color: #fff;
}

.mini-calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
}

.mini-calendar-day-name {
    text-align: center;
    font-size: 0.7rem;
    color: #768390;
    font-weight: bold;
}

.mini-calendar-day {
    background-color: #2d333b;
    border-radius: 3px;
    padding: 5px 2px;
    text-align: center;
    font-size: 0.8rem;
    color: #adbac7;
}

.mini-calendar-day.is-active.is-positive {
    background-color: #22c55e;
    color: #fff;
}

.mini-calendar-day.is-active.is-negative {
    background-color: #ef4444;
    color: #fff;
}
</style>