<script setup>
import { onMounted, ref, watchEffect } from 'vue'
import SpinnerLoadingPage from '../components/SpinnerLoadingPage.vue';
import Filters from '../components/Filters.vue'
import NoData from '../components/NoData.vue';
import Calendar from '../components/Calendar.vue';
import { spinnerLoadingPage, calendarData, filteredTrades, amountCase, selectedMonth } from '../stores/globals';
import { useMountCalendar } from '../utils/utils'
import { useGetFilteredTrades } from '../utils/trades'
import dayjs from 'dayjs';

// Make sure amountCase is properly initialized
if (!amountCase.value) {
    amountCase.value = localStorage.getItem('selectedGrossNet') || 'gross';
}

// Always ensure selectedMonth is set to current month on page load
const ensureCurrentMonth = () => {
    // Check if selectedMonth is null or undefined
    if (!selectedMonth.value) {
        selectedMonth.value = {
            start: dayjs().startOf('month').unix(), 
            end: dayjs().endOf('month').unix()
        };
        localStorage.setItem('selectedMonth', JSON.stringify(selectedMonth.value));
        console.log("Set selectedMonth to current month");
    }
    
    // Check if we're showing a past month - always include current month in query
    const currentMonthStart = dayjs().startOf('month').unix();
    const currentMonthEnd = dayjs().endOf('month').unix();
    
    console.log("Selected month is:", dayjs.unix(selectedMonth.value.start).format('YYYY-MM-DD'), 
                "to", dayjs.unix(selectedMonth.value.end).format('YYYY-MM-DD'));
    console.log("Current month is:", dayjs.unix(currentMonthStart).format('YYYY-MM-DD'), 
                "to", dayjs.unix(currentMonthEnd).format('YYYY-MM-DD'));
}

// Add this before the watchEffect
const previousMonthKey = ref('');

// Force initial load when component mounts
onMounted(() => {
  console.log("Calendar view mounted, forcing initial load");
  // Set spinnerLoadingPage to true initially
  spinnerLoadingPage.value = true;
  
  // Give a slight delay to ensure reactivity is set up
  setTimeout(async () => {
    try {
      // Reset the previous key to force a reload
      previousMonthKey.value = "";
      
      // Ensure month is set correctly
      ensureCurrentMonth();
      
      // Initialize calendar data if needed
      if (!calendarData.value) {
        calendarData.value = {};
      }
      
      // Load trades and calendar
      await useGetFilteredTrades();
      console.log(`Initial calendar load: ${filteredTrades?.length || 0} days of trades`);
      await useMountCalendar();
      console.log("Initial calendar load complete");
    } catch (error) {
      console.error("Error during initial calendar load:", error);
    } finally {
      spinnerLoadingPage.value = false;
    }
  }, 100);
});

watchEffect(async () => {
    // Prevent multiple executions for the same data
    const currentKey = JSON.stringify(selectedMonth.value);
    
    // Only run if this is a different month selection than before
    if (previousMonthKey.value === currentKey) {
        console.log("Skipping duplicate calendar load for same month");
        return;
    }
    
    previousMonthKey.value = currentKey;
    spinnerLoadingPage.value = true;
    
    try {
        // Ensure the month is set, then fetch and mount
        ensureCurrentMonth();

        // Make sure calendarData is initialized
        if (!calendarData.value) {
            calendarData.value = {};
        }
        
        // First fetch the trades
        await useGetFilteredTrades();
        console.log(`Calendar view: Loaded ${filteredTrades?.length || 0} days of trades`);

        // Now mount the calendar with the preloaded trades
        await useMountCalendar();
        console.log("Calendar mounted successfully");
    } catch (error) {
        console.error("Error in calendar watchEffect:", error);
    } finally {
        spinnerLoadingPage.value = false;
    }
});

</script>

<template>
    <SpinnerLoadingPage />
    <div v-show="!spinnerLoadingPage" class="row mt-2 mb-2">
        <Filters />
        <div v-if="filteredTrades.length == 0">
            <NoData />
        </div>
        <div v-else>
            <div>
                <!-- ============ CALENDAR ============ -->
                <div v-show="calendarData.value" class="col-12 text-center mt-2 align-self-start">
                    <div class="dailyCard">
                        <div class="row justify-content-center">
                            <Calendar />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.dailyCard {
    background-color: #202124;
    border-radius: 10px;
    padding: 10px;
    position: relative;
    z-index: 1; /* Lower z-index to prevent dropdown overlap */
}

/* Ensure all calendar content stays below dropdowns */
.row, .col, .col-md-12, .calendar-container, .calendar-wrapper {
    position: relative;
    z-index: 1;
}
</style>
