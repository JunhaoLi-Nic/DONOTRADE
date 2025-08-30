<script setup>
import { ref, onBeforeMount, onMounted, computed } from "vue";
import { useMonthFormat, useDateCalFormat, useDateCalFormatMonth, useMountCalendar, useMountDashboard, useMountDaily, useCheckVisibleScreen, useExport, useThousandCurrencyFormat, useInitShepherd, useInitTooltip, useInitTab, validateDateTimestamp } from "../utils/utils.js";
import { pageId, currentUser, timeZoneTrade, periodRange, positions, timeFrames, ratios, grossNet, plSatisfaction, selectedPositions, selectedTimeFrame, selectedRatio, selectedAccounts, selectedGrossNet, selectedPlSatisfaction, selectedDateRange, selectedMonth, selectedPeriodRange, tempSelectedPlSatisfaction, amountCase, amountCapital, hasData, selectedTags, tags, availableTags, filteredTradesTrades } from "../stores/globals"
import { useECharts } from "../utils/charts.js";
import { useRefreshScreenshot } from "../utils/screenshots"
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

/*============================================
    VARIABLES
============================================*/

// Computed property to format selectedMonth for the input
const selectedMonthForInput = computed({
  get: () => {
    if (selectedMonth.value && selectedMonth.value.start) {
      return dayjs.unix(selectedMonth.value.start).format('YYYY-MM');
    }
    return dayjs().format('YYYY-MM');
  },
  set: (newValue) => {
    inputMonth(newValue);
  }
});

let filtersOpen = ref(false)
let filters = ref({
    "dashboard": ["accounts", "periodRange", "grossNet", "positions", "timeFrame", "ratio", "tags"],
    "calendar": ["month", "grossNet", "plSatisfaction"],
    "daily": ["accounts", "month", "grossNet", "positions", "tags"],
    "screenshots": ["accounts", "grossNet", "positions", "tags"],
})



/*if (selectedDateRange.value) {
    console.log(" -> Filtering date range")
    let tempFilter = periodRange.filter(element => element.start == selectedDateRange.value.start && element.end == selectedDateRange.value.end)
    if (tempFilter.length > 0) {
        selectedPeriodRange.value = tempFilter[0]
    } else {
        console.log(" -> Custom range in vue")
        selectedPeriodRange.value = periodRange.filter(element => element.start == -1)[0]
    }
}*/
//console.log(" -> Selected date range "+JSON.stringify(selectedPeriodRange))


//IMPORTANT : when exists in localstorage but is empty, then == ''. When does not exist in localstorage then == null. As it may be empty, we take the case of null



/*============================================
    LIFECYCLE
============================================*/
onBeforeMount(async () => {
})

onMounted(() => {
    // Initialize Bootstrap dropdowns programmatically ONLY for Daily page
    setTimeout(() => {
        if (pageId.value === 'daily') {
            initializeDropdowns();
        }
    }, 500);

    // Add page identifier class when on daily page
    if (pageId.value === 'daily') {
        document.body.setAttribute('data-page', 'daily');
        const step10El = document.getElementById('step10');
        if (step10El) {
            step10El.setAttribute('data-page', 'daily');
            step10El.classList.add('daily-page');
        }
    }
})

/*============================================
    FUNCTIONS
============================================*/
function initializeDropdowns() {
    // Check if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        // Get all dropdown elements ONLY in the daily page context
        const dropdownElements = document.querySelectorAll('#step10 [data-bs-toggle="dropdown"]');
        
        // Initialize each dropdown
        dropdownElements.forEach(el => {
            try {
                // Create new dropdown instance
                new bootstrap.Dropdown(el, {
                    autoClose: 'outside',
                    display: 'static'
                });
                
                // Add click event listener to ensure dropdown shows
                el.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const dropdownInstance = bootstrap.Dropdown.getInstance(el);
                    if (dropdownInstance) {
                        dropdownInstance.toggle();
                    }
                });
            } catch (error) {
                console.error('Error initializing dropdown:', error);
            }
        });
        
        console.log("Daily page dropdowns initialized");
    } else {
        console.warn("Bootstrap JS not available");
    }
}

function filtersClick() {
    filtersOpen.value = !filtersOpen.value
    checkAllTagsSelected()
    //console.log(" -> Filters click: Selected Period Range " + JSON.stringify(selectedPeriodRange))
    //console.log(" -> Filters click: Selected Date Range Cal " + JSON.stringify(selectedDateRange))

    if (!filtersOpen.value) { //It's like clicking cancel of not saving so we remove data / go back to old data 

        // Restore Selected Date range cal
        const storedDateRange = localStorage.getItem('selectedDateRange');
        if (storedDateRange) {
            selectedDateRange.value = JSON.parse(storedDateRange);
        } else {
            selectedDateRange.value = {
                start: dayjs().startOf('month').unix(),
                end: dayjs().endOf('month').unix()
            };
        }
        //console.log(" -> Filters click (close): Selected Date Range Cal " + JSON.stringify(selectedDateRange))
        //console.log(" periodRange "+JSON.stringify(periodRange))
        // Restore Selected Period range
        //console.log(" selectedDateRange "+JSON.stringify(selectedDateRange.value))
        let tempFilter = periodRange.filter(element => element.start == selectedDateRange.value.start && element.end == selectedDateRange.value.end)

        if (tempFilter.length > 0) {
            selectedPeriodRange.value = tempFilter[0]
        } else {
            //console.log(" -> Custom range in trades mixin")
            //console.log(" periodRange 2 " + JSON.stringify(periodRange))
            selectedPeriodRange.value = periodRange.filter(element => element.start == -1)[0]
        }

        //console.log(" -> Filters click (on close): Selected Period Range " + JSON.stringify(selectedPeriodRange))

        // Restore temp selected accounts
        if (localStorage.getItem('selectedAccounts')) {
            if (localStorage.getItem('selectedAccounts').includes(",")) {
                selectedAccounts.value = localStorage.getItem('selectedAccounts').split(",")
            } else {
                selectedAccounts.value = []
                selectedAccounts.value.push(localStorage.getItem('selectedAccounts'))
            }
        } else {
            selectedAccounts.value = []
        }


        //console.log(" Selected accounts " + selectedAccounts)

        //Restore gross net
        selectedGrossNet.value = localStorage.getItem('selectedGrossNet')
        //console.log(" Selected accounts " + selectedAccounts)

        // Restore temp selected positions
        if (localStorage.getItem('selectedPositions')) {
            if (localStorage.getItem('selectedPositions').includes(",")) {
                selectedPositions.value = localStorage.getItem('selectedPositions').split(",")
            } else {
                selectedPositions.value = []
                selectedPositions.value.push(localStorage.getItem('selectedPositions'))
            }
        } else {
            selectedPositions.value = []
        }

        selectedTimeFrame.value = localStorage.getItem('selectedTimeFrame')
        //console.log(" Selected timeframe " + selectedTimeFrame)

        selectedRatio.value = localStorage.getItem('selectedRatio')
        //console.log(" Selected ratio " + selectedRatio)

        const storedMonth = localStorage.getItem('selectedMonth');
        if (storedMonth) {
            selectedMonth.value = JSON.parse(storedMonth);
        } else {
            selectedMonth.value = {
                start: dayjs().startOf('month').unix(),
                end: dayjs().endOf('month').unix()
            };
        }
        //console.log(" Selected Month " + JSON.stringify(selectedMonth))

        if (localStorage.getItem('selectedTags')) {
            if (localStorage.getItem('selectedTags').includes(",")) {
                selectedTags.value = localStorage.getItem('selectedTags').split(",")
            } else {
                selectedTags.value = []
                selectedTags.value.push(localStorage.getItem('selectedTags'))
            }
        } else {
            selectedTags.value = []
        }
    }
}

//Date : periode
function inputDateRange(param) {
    console.log(" -> Input Date Range - Param: " + param)
    //Filter to find the value of date range
    var filterJson = periodRange.filter(element => element.value == param)[0]
    selectedPeriodRange.value = filterJson
    //console.log(" -> Input range: Selected Date Range " + JSON.stringify(selectedPeriodRange.value))

    //Created selected Date range calendar mode
    let temp = {}
    temp.start = selectedPeriodRange.value.start
    temp.end = selectedPeriodRange.value.end
    selectedDateRange.value = temp
    //console.log(" -> Input range : Selected Date Range Cal " + JSON.stringify(selectedDateRange.value))

}
//Date : calendar
function inputDateRangeCal(param1, param2) {
    console.log(" -> Input Date Range Cal - type '" + param1 + "' and date " + param2)
    //console.log(" -> Initial selectedDateRange " + JSON.stringify(selectedDateRange.value))

    // Initialize selectedDateRange.value if it's null
    if (!selectedDateRange.value) {
        selectedDateRange.value = {
            start: dayjs().startOf('month').unix(),
            end: dayjs().endOf('month').unix()
        };
    }

    if (param1 == "start") {
        selectedDateRange.value.start = dayjs.tz(param2, timeZoneTrade.value).unix()
    }
    if (param1 == "end") {
        selectedDateRange.value.end = dayjs.tz(param2, timeZoneTrade.value).endOf("day").unix() // it must be tz(...). It cannot be dayjs().t
    }


    //console.log("selectedDateRange " + JSON.stringify(selectedDateRange.value))

    /* Update selectedPeriodRange */
    //console.log(" periodRange "+JSON.stringify(periodRange))
    //console.log(" selectedDateRange.value.start "+selectedDateRange.value.start)
    //console.log(" selectedDateRange.value.end "+selectedDateRange.value.end)
    let tempFilter = periodRange.filter(element => element.start == selectedDateRange.value.start && element.end == selectedDateRange.value.end)
    if (tempFilter.length > 0) {
        selectedPeriodRange.value = tempFilter[0]
    } else {
        //console.log(" -> Custom range in trades mixin")
        selectedPeriodRange.value = periodRange.filter(element => element.start == -1)[0]
    }
}

function inputMonth(param1) {
    //console.log(" param1 " + param1)
    let temp = {}
    temp.start = dayjs.tz(param1, timeZoneTrade.value).unix()
    temp.end = dayjs.tz(param1, timeZoneTrade.value).endOf("month").unix()
    
    // Validate dates before setting
    const validatedDates = validateDateTimestamp(temp);
    selectedMonth.value = validatedDates;
    
    //console.log(" -> Selected Month "+JSON.stringify(selectedMonth.value))
}

async function saveFilter() {
    console.log(" -> Save filters: Selected Date Range Cal " + JSON.stringify(selectedDateRange.value))
    console.log(" -> Save filters: Selected Period Range " + JSON.stringify(selectedPeriodRange.value))
    //console.log(" -> Selected accounts "+selectedAccounts.value)
    // Check if start date before end date and vice versa
    if (selectedDateRange.value.end < selectedDateRange.value.start) {
        alert("End date cannot be before start date")
        return
    } else {
        // Validate dates
        const validatedDateRange = validateDateTimestamp(selectedDateRange.value);
        selectedDateRange.value = validatedDateRange;
        localStorage.setItem('selectedDateRange', JSON.stringify(validatedDateRange));
    }


    if (pageId.value == "dashboard" && selectedDateRange.value.end >= selectedDateRange.value.start && hasData.value) {
        useECharts("clear")
    }

    localStorage.setItem('selectedPeriodRange', JSON.stringify(selectedPeriodRange.value))
    localStorage.setItem('selectedAccounts', selectedAccounts.value)

    localStorage.setItem('selectedGrossNet', selectedGrossNet.value)
    amountCase.value = selectedGrossNet.value
    amountCapital.value = selectedGrossNet.value.charAt(0).toUpperCase() + selectedGrossNet.value.slice(1)
    //console.log("filter amountCapital " + amountCapital.value)

    localStorage.setItem('selectedPositions', selectedPositions.value)

    localStorage.setItem('selectedTimeFrame', selectedTimeFrame.value)

    localStorage.setItem('selectedRatio', selectedRatio.value)

    if (pageId.value == "daily" || pageId.value == "calendar") {
        // Validate month dates
        const validatedMonth = validateDateTimestamp(selectedMonth.value);
        selectedMonth.value = validatedMonth;
        localStorage.setItem('selectedMonth', JSON.stringify(validatedMonth));
    }

    localStorage.setItem('selectedTags', selectedTags.value)
    checkAllTagsSelected()

    if (tempSelectedPlSatisfaction.value != null) {
        selectedPlSatisfaction.value = tempSelectedPlSatisfaction.value
        localStorage.setItem('selectedPlSatisfaction', selectedPlSatisfaction.value)
        tempSelectedPlSatisfaction.value = null
    }

    if (pageId.value == "dashboard") {
        useMountDashboard()
    }

    if (pageId.value == "daily") {
        await useMountDaily()
        useCheckVisibleScreen()
    }

    if (pageId.value == "screenshots") {
        await useRefreshScreenshot()
        useCheckVisibleScreen()
    }
    if (pageId.value == "calendar") {
        useMountCalendar(true)
    }
}

let allTagsSelected = ref(false)

const checkAllTagsSelected = () => {
    let temp = []
    for (let index = 0; index < availableTags.length; index++) {
        const element = availableTags[index];
        for (let index = 0; index < element.tags.length; index++) {
            const el = element.tags[index];
            temp.push(el.id)
        }
    }

    if ((temp.length + 1) == selectedTags.value.length) {
        allTagsSelected.value = true
    } else {
        allTagsSelected.value = false
    }

}
const selectAllTags = () => {

    selectedTags.value = []
    if (allTagsSelected.value) {
        allTagsSelected.value = !allTagsSelected.value
    } else {
        selectedTags.value.push("t000t")
        for (let index = 0; index < availableTags.length; index++) {
            const element = availableTags[index];
            for (let index = 0; index < element.tags.length; index++) {
                const el = element.tags[index];
                selectedTags.value.push(el.id)
            }
        }
        allTagsSelected.value = !allTagsSelected.value
    }

}
</script>

<template>
    <!-- ============ LINE 1: DATE FILTERS ============ -->
    <div id="step10" class="col-12 mb-3">
        <div class="dailyCard">
            <div>
                <span v-if="!filtersOpen" v-on:click="filtersClick" class="pointerClass">Filters <i
                        class="uil uil-angle-up"></i>
                </span>
                <span v-if="!filtersOpen" class="dashInfoTitle ms-3">
                    <span v-show="filters[pageId].includes('accounts')">
                        <span
                            v-if="currentUser.hasOwnProperty('accounts') && currentUser.accounts.length == selectedAccounts.length">All
                            accounts |</span>
                        <span v-else>Selected accounts |</span>
                    </span>

                    <span v-show="filters[pageId].includes('periodRange')">
                        {{ selectedPeriodRange && selectedPeriodRange.label ? selectedPeriodRange.label : 'All Time' }} |
                        <span v-show="selectedPeriodRange && selectedPeriodRange.value == 'custom'"> Range |</span>
                    </span>

                    <span v-show="filters[pageId].includes('month')">
                        {{ selectedMonthForInput ? dayjs(selectedMonthForInput).format("MMMM YYYY") : 'Current Month' }} |
                    </span>

                    <span v-show="filters[pageId].includes('grossNet')">{{ selectedGrossNet && selectedGrossNet.charAt ? selectedGrossNet.charAt(0).toUpperCase() +
                        selectedGrossNet.slice(1) : 'Gross' }} data |
                    </span>

                    <span v-show="filters[pageId].includes('positions')">
                        <span v-if="positions.length == selectedPositions.length">All positions |</span>
                        <span v-else>{{ selectedPositions && selectedPositions.toString && selectedPositions.toString().charAt ? selectedPositions.toString().charAt(0).toUpperCase() +
                            selectedPositions.toString().slice(1) : 'Selected positions' }} |</span>
                    </span>

                    <span v-show="filters[pageId].includes('timeFrame')">
                        {{ selectedTimeFrame && selectedTimeFrame.charAt ? selectedTimeFrame.charAt(0).toUpperCase() + selectedTimeFrame.slice(1) : 'Day' }} timeframe |
                    </span>

                    <span v-show="filters[pageId].includes('ratio')">
                        <span v-if="selectedRatio && selectedRatio !== 'profitFactor'">{{ selectedRatio && selectedRatio.toUpperCase ? selectedRatio.toUpperCase() : 'WIN RATE' }}</span><span
                            v-else>Profit Factor</span> |
                    </span>

                    <span v-show="filters[pageId].includes('tags')">
                        <span v-if="tags.length == selectedTags.length">All
                            tags</span>
                        <span v-else>Selected tags</span>
                    </span>

                    <span v-show="filters[pageId].includes('plSatisfaction')">
                        {{ selectedPlSatisfaction == 'satisfaction' ? 'Satisfaction' : "P&L" }} calendar
                    </span>

                </span>

                <span v-else v-on:click="filtersClick" class="pointerClass mb-3">Filters<i
                        class="uil uil-angle-down"></i>
                </span>
            </div>

            <div v-show="filtersOpen" class="row text-center align-items-center">
                <!-- Date : periode -->
                <div class="col-12 col-lg-4 mt-1 mt-lg-0 mb-lg-1" v-show="pageId == 'dashboard'">
                    <select v-on:input="inputDateRange($event.target.value)" class="form-select">
                        <option v-for="item in periodRange" :key="item.value" :value="item.value"
                            :selected="item.value == selectedPeriodRange.value">{{ item.label }}</option>
                    </select>
                </div>

                <!-- Date : calendar -->
                <div class="col-12 col-lg-8 mt-1 mt-lg-0 mb-1" v-show="pageId == 'dashboard'">
                    <div class="row">
                        <div class="col-5">
                            <input type="date" class="form-control" 
                                :value="selectedDateRange && selectedDateRange.start ? useDateCalFormat(selectedDateRange.start) : useDateCalFormat(dayjs().startOf('month').unix())"
                                :selected="selectedDateRange && selectedDateRange.start ? selectedDateRange.start : dayjs().startOf('month').unix()"
                                v-on:input="inputDateRangeCal('start', $event.target.value)" />
                        </div>
                        <div class="col-2">
                            <i class="uil uil-angle-right-b"></i>
                        </div>
                        <div class="col-5">
                            <input type="date" class="form-control" 
                                :value="selectedDateRange && selectedDateRange.end ? useDateCalFormat(selectedDateRange.end) : useDateCalFormat(dayjs().endOf('month').unix())"
                                :selected="selectedDateRange && selectedDateRange.end ? selectedDateRange.end : dayjs().endOf('month').unix()"
                                v-on:input="inputDateRangeCal('end', $event.target.value)">
                            <div class="row"></div>
                        </div>
                    </div>
                </div>

                <!-- Accounts -->
                <div class="col-6 dropdown" v-show="pageId != 'screenshots' && pageId != 'calendar'">
                    <button class="btn btn-secondary dropdown-toggle" type="button" id="accountsDropdown" data-bs-toggle="dropdown" data-bs-auto-close="outside" data-bs-display="static" aria-expanded="false">Accounts <span class="dashInfoTitle">({{ selectedAccounts.length
                            }})</span></button>
                    <ul class="dropdown-menu dropdownCheck" aria-labelledby="accountsDropdown">
                        <div v-for="item in currentUser.accounts" :key="item.value" class="form-check">
                            <input class="form-check-input" type="checkbox" :value="item.value"
                                v-model="selectedAccounts">
                            {{ item.label }}
                        </div>
                    </ul>
                </div>

                <!-- Month -->
                <div class="col-12 col-lg-6 mt-1 mt-lg-0 mb-lg-1" v-show="pageId == 'daily' || pageId == 'calendar'">
                    <input type="month" class="form-control" v-model="selectedMonthForInput">
                </div>

                <!-- Tags -->
                <div :class="[pageId == 'screenshots' ? 'col-12' : 'col-6', 'dropdown mt-1 mt-lg-1']"
                    v-show="pageId != 'calendar'">

                    <button class="btn btn-secondary dropdown-toggle" type="button" id="tagsDropdown" data-bs-toggle="dropdown" data-bs-auto-close="outside" data-bs-display="static" aria-expanded="false">Tags <span class="dashInfoTitle">({{ selectedTags.length
                            }})</span></button>

                    <ul class="dropdown-menu dropdownCheck" aria-labelledby="tagsDropdown">
                        <div>
                            <a class="pointerClass nav-link" v-on:click="selectAllTags"><span
                                    v-if="!allTagsSelected">Select All</span><span v-else>Unselect All</span></a>
                        </div>
                        <hr>
                        <input class="form-check-input mt-1" type="checkbox" value="t000t"
                            v-model="selectedTags">&nbsp;&nbsp;No Tag
                        <hr>
                        <span v-for="group in availableTags">
                            <h6 class="p-1 mb-0" :style="'background-color: ' + group.color + ';'">
                                {{ group.name }}</h6>
                            <div v-for="item in group.tags" class="form-check">
                                <input class="form-check-input" type="checkbox" :value="item.id" v-model="selectedTags">
                                {{ item.name }}
                            </div>
                        </span>

                    </ul>
                </div>

                <!-- Gross/Net -->
                <div class="col-6 col-lg-3" v-show="pageId != 'screenshots'">
                    <select v-on:input="selectedGrossNet = $event.target.value" class="form-select">
                        <option v-for="item in grossNet" :key="item.value" :value="item.value"
                            :selected="item.value == selectedGrossNet">{{ item.label }}</option>
                    </select>
                </div>

                <!-- Positions -->
                <div class="col-6 col-lg-3 dropdown" v-show="pageId != 'screenshots' && pageId != 'calendar'">
                    <button class="btn btn-secondary dropdown-toggle" type="button" id="positionsDropdown" data-bs-toggle="dropdown" data-bs-auto-close="outside" data-bs-display="static" aria-expanded="false">Positions <span class="dashInfoTitle">({{ selectedPositions.length
                            }})</span></button>
                    <ul class="dropdown-menu dropdownCheck" aria-labelledby="positionsDropdown">
                        <div v-for="item in positions" :key="item.value" class="form-check">
                            <input class="form-check-input" type="checkbox" :value="item.value"
                                v-model="selectedPositions">
                            {{ item.label }}
                        </div>
                    </ul>
                </div>

                <!-- Timeframe -->
                <div class="col-6 col-lg-3 mt-1 mt-lg-1" v-show="pageId == 'dashboard'">
                    <select v-on:input="selectedTimeFrame = $event.target.value" class="form-select">
                        <option v-for="item in timeFrames" :key="item.value" :value="item.value"
                            :selected="item.value == selectedTimeFrame">{{ item.label }}</option>
                    </select>
                </div>

                <!-- Ratio -->
                <div class="col-6 col-lg-3 mt-1 mt-lg-1" v-show="pageId == 'dashboard'">
                    <select v-on:input="selectedRatio = $event.target.value" class="form-select">
                        <option v-for="item in ratios" :key="item.value" :value="item.value"
                            :selected="item.value == selectedRatio">{{ item.label }}</option>
                    </select>
                </div>

                <!-- P&L / Satisfaction  -->
                <div :class="[pageId == 'daily' ? 'col-4' : 'col-3']" v-show="pageId == 'calendar'">
                    <select v-on:input="tempSelectedPlSatisfaction = $event.target.value" class="form-select">
                        <option v-for="item in plSatisfaction" :key="item.value" :value="item.value"
                            :selected="item.value == selectedPlSatisfaction">{{ item.label }}</option>
                    </select>
                </div>

                <div class="col-12 text-center">
                    <button class="btn btn-success btn-sm mt-2" v-on:click="saveFilter">Filter</button>
                    <span v-if="pageId == 'dashboard'">
                        <button class="btn btn-secondary btn-sm mt-2 ms-4 dropdown-toggle" type="button"
                            data-bs-toggle="dropdown" aria-expanded="false">Export
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item"
                                    v-on:click="useExport('json', 
                                        selectedDateRange && selectedDateRange.start ? useDateCalFormat(selectedDateRange.start) : useDateCalFormat(dayjs().startOf('month').unix()), 
                                        selectedDateRange && selectedDateRange.end ? useDateCalFormat(selectedDateRange.end) : useDateCalFormat(dayjs().endOf('month').unix()), 
                                        filteredTradesTrades)">JSON</a>
                            </li>
                            <li><a class="dropdown-item"
                                    v-on:click="useExport('csv', 
                                        selectedDateRange && selectedDateRange.start ? useDateCalFormat(selectedDateRange.start) : useDateCalFormat(dayjs().startOf('month').unix()),
                                        selectedDateRange && selectedDateRange.end ? useDateCalFormat(selectedDateRange.end) : useDateCalFormat(dayjs().endOf('month').unix()),
                                        filteredTradesTrades)">CSV</a>
                            </li>
                        </ul>
                    </span>

                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.dailyCard {
    background-color: #1e1e2f;
    border-radius: 12px;
    padding: 25px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    color: #e0e0e0;
    position: relative;
    z-index: 1; /* Keep content below dropdowns */
}

.pointerClass {
    cursor: pointer;
}

.dashInfoTitle {
    font-size: 0.9rem;
    color: #a0a0a0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Update the select element styles */
.form-select {
    background-color: #2a2a4a;
    color: #e0e0e0;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 10px 15px;
    transition: all 0.3s ease;
    position: relative;
    z-index: 9999 !important; /* Very high z-index */
}

/* Fix select dropdown options display */
select.form-select option {
    background-color: #2a2a4a;
    color: #e0e0e0;
    padding: 10px;
    z-index: 9999 !important;
}

/* Apply special styling for the period range dropdown (by class and position) */
.col-12.col-lg-4 select.form-select {
    position: relative !important;
    z-index: 9999 !important;
}

/* Ensure dropdown list appears on top */
.col-12.col-lg-4 select.form-select option {
    position: relative !important;
    z-index: 9999 !important;
    background-color: #2a2a4a !important;
    color: #e0e0e0 !important;
}

.form-control {
    background-color: #2a2a4a; /* Darker input fields */
    color: #e0e0e0;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 10px 15px;
    transition: all 0.3s ease;
}

.form-select:focus,
.form-control:focus {
    border-color: #6a8dff;
    box-shadow: 0 0 0 0.25rem rgba(106, 141, 255, 0.25);
    background-color: #2a2a4a;
    color: #e0e0e0;
}

.form-control[type="date"]::-webkit-calendar-picker-indicator,
.form-control[type="month"]::-webkit-calendar-picker-indicator {
    filter: invert(1); /* Invert color for dark theme */
}

.btn-secondary {
    background-color: #3a3a5a; /* Darker secondary button */
    border-color: #3a3a5a;
    color: #fff;
    font-weight: 600;
    padding: 10px 15px;
    border-radius: 8px;
    transition: all 0.3s ease;
}

.btn-secondary:hover {
    background-color: #4a4a6a;
    border-color: #4a4a6a;
}

/* Main dropdown fix */
.dropdown-menu {
    background-color: #2a2a4a;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
    padding: 10px;
    z-index: 99999 !important;
    position: absolute !important;
}

/* Custom dropdown container */
.dropdown {
    position: relative !important;
    z-index: 10000 !important;
}

/* Position dropdowns correctly */
[data-bs-toggle="dropdown"] {
    position: relative !important;
    z-index: 10000 !important;
}

/* Ensure dropdown shows on top */
.dropdown-menu.show {
    display: block !important;
    z-index: 99999 !important;
    position: absolute !important;
    transform: none !important;
}

.dropdownCheck .form-check {
    padding: 8px 15px;
    color: #e0e0e0;
}

.dropdownCheck .form-check-input {
    margin-right: 10px;
    background-color: #3a3a5a;
    border-color: rgba(255, 255, 255, 0.3);
}

.dropdownCheck .form-check-input:checked {
    background-color: #6a8dff;
    border-color: #6a8dff;
}

.dropdownCheck .form-check-input:focus {
    box-shadow: 0 0 0 0.25rem rgba(106, 141, 255, 0.25);
}

.dropdown-menu hr {
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.dropdown-menu h6 {
    color: #fff;
    font-weight: 700;
    margin-top: 10px;
    margin-bottom: 5px;
}

.dropdown-item {
    color: #e0e0e0;
    padding: 8px 15px;
    transition: background-color 0.2s ease;
    border-radius: 5px;
}

.dropdown-item:hover {
    background-color: #3a3a5a;
    color: #fff;
}

.btn-success {
    background-color: #4caf50; /* Green for success/filter */
    border-color: #4caf50;
    color: #fff;
    font-weight: 600;
    padding: 10px 20px;
    border-radius: 8px;
    transition: all 0.3s ease;
}

.btn-success:hover {
    background-color: #429a46;
    border-color: #429a46;
}

.uil-angle-right-b {
    color: #6a8dff; /* Accent color for arrow icon */
    font-size: 1.5rem;
}

/* Fix specific row and col z-indices */
.row, .col-12, .col-6, .col-5, .col-4, .col-3, .col-2 {
    position: relative;
    z-index: 1;
}

/* Update the "This Year" select dropdown to ensure it appears on top */
.col-12.col-lg-4.mt-1.mt-lg-0.mb-lg-1 select.form-select {
    position: relative !important;
    z-index: 10000 !important; /* Extra high z-index */
}

/* Make sure the select options appear properly */
.col-12.col-lg-4.mt-1.mt-lg-0.mb-lg-1 select.form-select option {
    background-color: #2a2a4a !important;
    color: #e0e0e0 !important;
}

/* Force select dropdowns to stay on top using fixed positioning if needed */
select.form-select {
    position: relative !important;
    z-index: 10000 !important; /* Extremely high z-index */
}

/* Lower the z-index of cards and main dashboard content */
#step10 ~ div {
    position: relative !important;
    z-index: 1 !important;
}

/* Additional styles to fix dropdown visibility issues */
.form-select option {
    position: relative !important;
    z-index: 100000 !important;
}

/* Ensure dropdown content is visible and interactable */
.dailyCard {
    position: relative;
    z-index: auto !important;
}

/* Make sure dropdowns are always on top of other content */
body .dropdown-menu,
body .form-select,
body .dropdown {
    isolation: isolate;
}

/* Fix for Bootstrap dropdown menus */
.dropdown-menu.show {
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
}

/* Prevent other elements from covering dropdowns */
#step10 {
    isolation: isolate;
    position: relative;
    z-index: 10000 !important;
}

/* Fix for any parent elements that might be creating stacking contexts */
.dailyCard {
    transform: translateZ(0);
}

/* Handle any potential Bootstrap positioning overrides */
.dropdown .dropdown-menu {
    inset: auto !important;
    transform: none !important;
    top: 100% !important;
    left: 0 !important;
    margin-top: 0.125rem !important;
}

/* Targeted fix for Daily page dropdowns only */
body[data-page="daily"] .dropdown-toggle,
body[data-page="daily"] .dropdown button,
[data-v-page="daily"] .dropdown-toggle,
[data-v-page="daily"] .dropdown button,
.dropdown-toggle[aria-expanded="false"],
.dropdown button[aria-expanded="false"] {
    pointer-events: auto !important;
    cursor: pointer !important;
    position: relative !important;
    z-index: 10000 !important;
}

/* Fix for Daily page specific dropdown menus */
body[data-page="daily"] .dropdown-menu,
[data-v-page="daily"] .dropdown-menu,
#step10[data-daily="true"] .dropdown-menu {
    display: none;
    z-index: 99999 !important;
    position: absolute !important;
}

body[data-page="daily"] .dropdown-menu.show,
[data-v-page="daily"] .dropdown-menu.show,
#step10[data-daily="true"] .dropdown-menu.show {
    display: block !important;
}

/* Fix for all dropdowns regardless of page */
.dropdown-menu.show {
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
    z-index: 99999 !important;
}

/* Target the specific elements in your screenshot that aren't working */
#step10 .dropdown .btn-secondary {
    pointer-events: auto !important;
    cursor: pointer !important;
}

/* Ensure dropdown menus appear when buttons are clicked */
#step10 .dropdown.show .dropdown-menu {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    z-index: 99999 !important;
}

/* Fix for lighter colored buttons in the Daily page */
.btn-secondary {
    background-color: #3a3a5a !important; /* Force darker background */
    border-color: #3a3a5a !important;
    color: #fff !important;
    font-weight: 600 !important;
    padding: 10px 15px !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    position: relative !important;
    z-index: 10000 !important;
}

/* Ensure all dropdowns work, regardless of their background color */
.dropdown-toggle {
    position: relative !important;
    z-index: 10000 !important;
    cursor: pointer !important;
    pointer-events: auto !important;
}

/* Fix for Daily page specific issues */
#step10 .dropdown {
    position: relative !important;
    z-index: 10000 !important;
    pointer-events: auto !important;
}

/* Ensure all form-select elements are consistent */
.form-select, 
.form-control {
    position: relative !important;
    z-index: 10000 !important;
    pointer-events: auto !important;
}

/* Fix for buttons with custom styling */
button[data-bs-toggle="dropdown"] {
    position: relative !important;
    z-index: 10000 !important;
    pointer-events: auto !important;
}

/* Dropdown containers - ensure proper positioning context */
.dropdown {
    position: static !important; /* Change to static to break out of parent stacking context */
}

/* Main dropdown fix - extreme z-index and forced positioning */
.dropdown-menu {
    position: fixed !important; /* Use fixed positioning to escape all stacking contexts */
    z-index: 999999 !important; /* Extremely high z-index */
    background-color: #2a2a4a;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.5);
    padding: 10px;
    min-width: 200px !important;
}

/* Override Bootstrap's dropdown positioning */
.dropdown-menu.show {
    display: block !important;
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
}

/* Force all dropdown toggles to have pointer events */
.dropdown-toggle, [data-bs-toggle="dropdown"] {
    cursor: pointer !important;
    pointer-events: auto !important;
}

/* Make the light blue buttons in Daily page work properly */
#step10 .btn-secondary {
    pointer-events: auto !important;
    cursor: pointer !important;
    position: relative !important;
}

/* Ensure proper positioning of dropdown menus relative to their buttons */
.dropdown .dropdown-menu.show {
    margin-top: 45px !important; /* Add space below the button */
    left: auto !important;
    right: auto !important;
    transform: none !important;
}

/* Adjust dropdown positioning based on its parent */
.col-6 .dropdown .dropdown-menu.show {
    left: 15px !important;
    width: calc(100% - 30px) !important;
}

/* Ensure no page elements can cover dropdowns */
body .dailyCard {
    overflow: visible !important;
}

/* Reset dropdown menu position to default for specific dropdowns */
#step10 .dropdown .dropdown-menu {
    position: absolute !important;
    top: 100% !important;
    left: 0 !important;
    margin-top: 0.5rem !important;
}

/* Force visibility for dropdown menus */
.dropdown-menu.show {
    visibility: visible !important;
    display: block !important;
    opacity: 1 !important;
}

/* Remove any max-height constraints that might clip dropdowns */
.dropdown-menu {
    max-height: none !important;
    overflow: visible !important;
}

/* Daily page specific dropdown styles - will not affect dashboard */
body[data-page="daily"] .dropdown-menu,
#step10[data-page="daily"] .dropdown-menu,
.daily-page .dropdown-menu {
    position: absolute !important;
    z-index: 999999 !important;
    background-color: #2a2a4a;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.5);
    padding: 10px;
    display: none; /* Hidden by default */
}

/* Daily page dropdown show state */
body[data-page="daily"] .dropdown-menu.show,
#step10[data-page="daily"] .dropdown-menu.show,
.daily-page .dropdown-menu.show {
    display: block !important;
    opacity: 1 !important;
    visibility: visible !important;
    pointer-events: auto !important;
}

/* Daily page dropdown button styles */
body[data-page="daily"] .btn-secondary,
#step10[data-page="daily"] .btn-secondary,
.daily-page .btn-secondary {
    cursor: pointer !important;
    pointer-events: auto !important;
    position: relative !important;
}
</style>