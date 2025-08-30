<script setup>
import { computed, onBeforeMount, onMounted, onBeforeUnmount, ref, watch, reactive } from 'vue'
import SpinnerLoadingPage from '../components/SpinnerLoadingPage.vue';
import Filters from '../components/Filters.vue'
import { selectedDashTab, spinnerLoadingPage, dashboardIdMounted, totals, amountCase, amountCapital, profitAnalysis, renderData, selectedRatio, dashboardChartsMounted, hasData, satisfactionArray, availableTags, groups, barChartNegativeTagGroups, periodRange, selectedDateRange, selectedPeriodRange, filteredTrades, currentUser } from '../stores/globals';
import { useThousandCurrencyFormat, useTwoDecCurrencyFormat, useXDecCurrencyFormat, useMountDashboard, useThousandFormat, useXDecFormat } from '../utils/utils';
import NoData from '../components/NoData.vue';
import { useReturnAnalysis } from '../utils/analyzer';
import ReturnDistributionChart from '../components/ReturnDistributionChart.vue';

// Add a function to check and handle page navigation
function handlePageNavigation() {
    // Check if we're coming from the imports page
    const fromImports = localStorage.getItem('from_imports') === 'true';
    const forceRefresh = localStorage.getItem('force_dashboard_refresh') === 'true';

    if (fromImports || forceRefresh) {
        console.log("Navigation from imports page detected, will ensure fresh data load");
        localStorage.removeItem('from_imports');
        // The refresh logic will be handled by useMountDashboard
    }
}

// Set default filter to "This Year"
function setDefaultYearFilter() {
    // Only set if no previous selection exists
    if (!localStorage.getItem('selectedPeriodRange') || localStorage.getItem('force_dashboard_refresh') === 'true') {
        // Find the "This Year" option from periodRange and set it as default
        const thisYearFilter = periodRange.find(period => period.value === 'thisYear');

        if (thisYearFilter) {
            // Set the period range
            localStorage.setItem('selectedPeriodRange', JSON.stringify(thisYearFilter));
            selectedPeriodRange.value = thisYearFilter;

            // Set the date range to match
            const dateRange = {
                start: thisYearFilter.start,
                end: thisYearFilter.end
            };
            localStorage.setItem('selectedDateRange', JSON.stringify(dateRange));
            selectedDateRange.value = dateRange;
        }
    }
}

// Import the organizeTradesToDayBuckets utility 
import { organizeTradesToDayBuckets } from '../utils/timeZoneUtils';

// Function to calculate summary data for the day of week table
function getDayOfWeekSummary() {
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    
    // Create new day buckets with correct timezone assignment
    let allTrades = [];
    
    // Flatten all trades into a single array
    if (filteredTrades && filteredTrades.length > 0) {
        filteredTrades.forEach(day => {
            if (day && day.trades) {
                allTrades = [...allTrades, ...day.trades];
            }
        });
    }
    
    // Organize trades into day buckets based on user's timezone
    const dayTrades = organizeTradesToDayBuckets(allTrades);
    
    const summary = [];

    for (let i = 0; i < 7; i++) {
        let netProfit = 0;
        let totalProfit = 0;
        let totalLoss = 0;
        let volume = 0;
        let winCount = 0;
        let lossCount = 0;

        // Calculate statistics for this day using our timezone-corrected buckets
        dayTrades[i].forEach(trade => {
            const proceeds = trade[amountCase.value + 'Proceeds'] || 0;
            netProfit += proceeds;

            if (proceeds > 0) {
                totalProfit += proceeds;
                winCount++;
            } else if (proceeds < 0) {
                totalLoss += proceeds;
                lossCount++;
            }
            // Note: trades with exactly $0 proceeds are not counted as wins or losses

            // Add up volume (using buyQuantity as an approximation)
            volume += trade.buyQuantity || 0;
        });

        // Calculate win and loss percentages based on win and loss counts
        const totalTrades = winCount + lossCount;
        // Calculate win/loss percentages only from actual winning or losing trades
        const winPercentage = totalTrades > 0 ? (winCount / totalTrades) * 100 : 0;
        const lossPercentage = totalTrades > 0 ? (lossCount / totalTrades) * 100 : 0;
        
        // Calculate trade counts including trades with zero proceeds
        const allTradesCount = dayTrades[i].length;

        summary.push({
            name: dayNames[i],
            netProfit: netProfit,
            winPercentage: winPercentage,
            lossPercentage: lossPercentage,
            winCount: winCount,
            lossCount: lossCount,
            totalProfit: totalProfit,
            totalLoss: totalLoss,
            trades: dayTrades[i].length,
            volume: volume
        });
    }

    return summary;
}

// Dashboard mounting flag to prevent duplicate mounting
let isDashboardMounted = false;

const dashTabs = [{
    id: "overviewTab",
    label: "Overview",
    target: "#overviewNav"
},
{
    id: "timeTab",
    label: "Time&Date",
    target: "#timeNav"
},
{
    id: "tradesTab",
    label: "Trades&Executions",
    target: "#tradesNav"
},
{
    id: "setupsTab",
    label: "Setups",
    target: "#setupsNav"
},
{
    id: "financialsTab",
    label: "Financials",
    target: "#financialsNav"
}
]
amountCapital.value = amountCase.value ? amountCase.value.charAt(0).toUpperCase() + amountCase.value.slice(1) : ''

const ratioCompute = computed(() => {
    let ratio = {}
    if (localStorage.getItem('selectedRatio') == 'appt') {
        ratio.shortName = "APPT"
        ratio.name = "Average Profit Factor per Trade"
        ratio.value = useTwoDecCurrencyFormat(totals[amountCase.value + 'Proceeds'] / totals.trades)
        ratio.tooltipTitle = '<div>Average Profit Per Trade</div><div> APPT = Proceeds &divide; Number of Trades</div><div>Proceeds: ' + useThousandCurrencyFormat(totals[amountCase.value + 'Proceeds']) + '</div><div>Trades: ' + useThousandFormat(totals.trades) + '</div>'
    }
    if (localStorage.getItem('selectedRatio') == 'apps') {
        ratio.name = "Average Profit Factor per Security"
        ratio.shortName = "APPS"
        ratio.value = useXDecCurrencyFormat(totals[amountCase.value + 'Proceeds'] / (totals.quantity / 2), 4)
        ratio.tooltipTitle = '<div>Average Profit Per Security</div><div> APPS = Proceeds &divide; Number of Securities Acquired</div><div>Proceeds: ' + useThousandCurrencyFormat(totals[amountCase.value + 'Proceeds']) + '</div><div>Securities Acquired: ' + useThousandFormat(totals.quantity / 2) + '</div>'
    }
    if (localStorage.getItem('selectedRatio') == 'profitFactor') {
        ratio.shortName = "Profit Factor"
        ratio.name = "Profit Factor"
        let wins = parseFloat(totals[amountCase.value + 'Wins']).toFixed(2)
        let loss = parseFloat(-totals[amountCase.value + 'Loss']).toFixed(2)
        let profitFactor = 0
        //console.log("wins " + wins + " and loss " + loss)
        if (loss != 0) {
            profitFactor = wins / loss
            //console.log(" -> profitFactor "+profitFactor)
        }
        ratio.value = useXDecFormat(profitFactor, 2)
        ratio.tooltipTitle = '<div> Profit Factor = Wins &divide; Losses</div><div>Wins: ' + useThousandCurrencyFormat(totals[amountCase.value + 'Wins']) + '</div><div>Losses: ' + useThousandCurrencyFormat(totals[amountCase.value + 'Loss']) + '</div>'
    }
    return ratio
})

const holdingTimeStats = computed(() => {
    let totalHoldingTime = 0;
    let tradeCount = 0;

    const buckets = {
        '0-1 Day': { trades: 0, totalPnl: 0, holdingSeconds: [] },
        '1-3 Days': { trades: 0, totalPnl: 0, holdingSeconds: [] },
        '3-7 Days': { trades: 0, totalPnl: 0, holdingSeconds: [] },
        '7-14 Days': { trades: 0, totalPnl: 0, holdingSeconds: [] },
        '14+ Days': { trades: 0, totalPnl: 0, holdingSeconds: [] }
    };

    if (filteredTrades && filteredTrades.length > 0) {
        filteredTrades.forEach(day => {
            if (day && day.trades) {
                day.trades.forEach(trade => {
                    if (trade && trade.exitTime && trade.entryTime && trade.exitTime >= trade.entryTime) {
                        const holdingTimeSeconds = trade.exitTime - trade.entryTime;
                        const holdingTimeDays = holdingTimeSeconds / (60 * 60 * 24);
                        const pnl = trade[amountCase.value + 'Proceeds'];

                        totalHoldingTime += holdingTimeSeconds;
                        tradeCount++;

                        let bucket;
                        if (holdingTimeDays <= 1) bucket = '0-1 Day';
                        else if (holdingTimeDays <= 3) bucket = '1-3 Days';
                        else if (holdingTimeDays <= 7) bucket = '3-7 Days';
                        else if (holdingTimeDays <= 14) bucket = '7-14 Days';
                        else bucket = '14+ Days';

                        buckets[bucket].trades++;
                        buckets[bucket].totalPnl += pnl;
                        buckets[bucket].holdingSeconds.push(holdingTimeSeconds);
                    }
                });
            }
        });
    }

    const averageHoldingTime = tradeCount > 0 ? totalHoldingTime / tradeCount : 0;
    const formatDuration = (seconds) => {
        const days = seconds / (60 * 60 * 24);
        return `${days.toFixed(2)} days`;
    };

    let optimalBucketName = '-';
    let maxAveragePnl = -Infinity;

    const processedBuckets = Object.entries(buckets).map(([name, data]) => {
        const avgPnl = data.trades > 0 ? data.totalPnl / data.trades : 0;
        if (data.trades > 0 && avgPnl > maxAveragePnl) {
            maxAveragePnl = avgPnl;
            optimalBucketName = name;
        }
        return {
            name,
            trades: data.trades,
            totalPnl: useTwoDecCurrencyFormat(data.totalPnl),
            avgPnl: useTwoDecCurrencyFormat(avgPnl),
        };
    });

    return {
        average: formatDuration(averageHoldingTime),
        optimalBucketName: optimalBucketName,
        maxAveragePnl: useTwoDecCurrencyFormat(maxAveragePnl),
        buckets: processedBuckets,
        hasTrades: tradeCount > 0
    };
});

// State for expandable rows and pagination
const expandedDays = reactive({});
const dayTradesByName = reactive({});
const dayTradesPagination = reactive({});
const dayTradesPages = reactive({});
const tradesPerPage = 5;

// Function to toggle day details expansion
function toggleDayDetails(dayName) {
    if (!expandedDays[dayName]) {
        // First time expanding this day, fetch the trades
        fetchDayTrades(dayName);
    }
    
    expandedDays[dayName] = !expandedDays[dayName];
}

// Import the getTradesForDay utility
import { getTradesForDay } from '../utils/timeZoneUtils';

// Function to fetch trades for a specific day of the week
function fetchDayTrades(dayName) {
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const dayIndex = dayNames.indexOf(dayName);
    
    if (dayIndex !== -1) {
        // Get all trades for this day using timezone-aware utility
        let allTrades = [];
        
        // Flatten the trades array
        if (filteredTrades && filteredTrades.length > 0) {
            filteredTrades.forEach(day => {
                if (day && day.trades) {
                    allTrades = [...allTrades, ...day.trades];
                }
            });
        }
        
        // Get trades for this day
        const dayTrades = getTradesForDay(dayName, allTrades);
        
        const trades = dayTrades.map(trade => {
            // Create date object with timestamp, ensuring timezone is accounted for
            const tradeDate = new Date(trade.entryTime * 1000);
            
            return {
                date: tradeDate,
                symbol: trade.symbol,
                side: trade.side || (trade.buyQuantity > 0 ? 'buy' : 'sell'),
                quantity: trade.buyQuantity || trade.quantity || 0,
                price: trade.buyPrice || trade.price || 0,
                profit: trade[amountCase.value + 'Proceeds'] || 0,
                id: trade.id || `${trade.entryTime}-${trade.symbol}`
            };
        });
        
        dayTradesByName[dayName] = trades;
        dayTradesPagination[dayName] = 1;
        dayTradesPages[dayName] = Math.ceil(trades.length / tradesPerPage);
    } else {
        dayTradesByName[dayName] = [];
        dayTradesPagination[dayName] = 1;
        dayTradesPages[dayName] = 1;
    }
}

// Import the timezone utilities
import { formatDateInUserTimeZone, formatTimeInUserTimeZone } from '../utils/timeZoneUtils';

// Function to format date using the user's timezone
function formatDate(date) {
    return formatDateInUserTimeZone(date);
}

// Function to format time using the user's timezone
function formatTime(date) {
    return formatTimeInUserTimeZone(date);
}

// Function to change page
function changePage(dayName, page) {
    if (page >= 1 && page <= dayTradesPages[dayName]) {
        dayTradesPagination[dayName] = page;
    }
}

// Function to get paginated trades for a day
function getPaginatedDayTrades(dayName) {
    if (!dayTradesByName[dayName]) return [];
    
    const startIndex = (dayTradesPagination[dayName] - 1) * tradesPerPage;
    const endIndex = startIndex + tradesPerPage;
    
    return dayTradesByName[dayName].slice(startIndex, endIndex);
}

const { returnStats } = useReturnAnalysis();

// Replace onBeforeMount with onMounted to ensure DOM is ready
onMounted(async () => {
    try {
        // Log timezone information for debugging
        console.log("Dashboard mounted with timezone settings:", {
            timeZone: currentUser?.value?.timeZone || 'America/New_York',
            useDeviceTimeZone: currentUser?.value?.useDeviceTimeZone || false,
            deviceTimeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
        });

        // Set default year filter
        setDefaultYearFilter();

        // Handle navigation first to determine if we need a full refresh
        handlePageNavigation();

        // Only mount if not already mounted
        if (!isDashboardMounted) {
            barChartNegativeTagGroups.length = 0;
            isDashboardMounted = true;
            await useMountDashboard();
        }
    } catch (error) {
        console.error("Error mounting Dashboard:", error);
        // Set loading state to false to prevent UI freeze
        spinnerLoadingPage.value = false;
        // Set a flag to show error message to user if needed
        hasData.value = false;
    }
});

// Add cleanup
onBeforeUnmount(() => {
    isDashboardMounted = false;
});

</script>

<template>
    <SpinnerLoadingPage />
    <div class="row mt-2">

        <div v-show="!spinnerLoadingPage">
            <Filters />
            <div v-if="!hasData">
                <NoData />
            </div>
            <div v-else>
                <nav>
                    <div class="nav nav-tabs mb-2" id="nav-tab" role="tablist">
                        <button v-for="dashTab in dashTabs" :key="dashTab.id"
                            :class="'nav-link ' + (selectedDashTab == dashTab.id ? 'active show' : '')" :id="dashTab.id"
                            data-bs-toggle="tab" :data-bs-target="dashTab.target" type="button" role="tab"
                            aria-controls="nav-overview" aria-selected="true">{{ dashTab.label }}</button>
                    </div>
                </nav>

                <div class="tab-content" id="nav-tabContent">

                    <!-- ============ OVERVIEW ============ -->
                    <div v-bind:class="'tab-pane fade ' + (selectedDashTab == 'overviewTab' ? 'active show' : '')"
                        id="overviewNav" role="tabpanel" aria-labelledby="nav-overview-tab">
                        <!-- ============ LINE 2: ID CARDS ============ -->
                        <div class="col-12 text-center ">
                            <div class="row">

                                <div v-if="dashboardIdMounted">
                                    <!-- FIRST LINE -->
                                    <div class="col-12 mb-3">
                                        <div class="row">
                                            <div class="col-6 mb-2 mb-lg-0 col-lg-3">
                                                <div class="dailyCard">
                                                    <h4 class="titleWithDesc">
                                                        {{
                                                            useThousandCurrencyFormat(totals[amountCase
                                                                +
                                                                'Proceeds']) }}
                                                    </h4>
                                                    <span class="dashInfoTitle">Cumulated P&L</span>

                                                </div>
                                            </div>
                                            <div class="col-6 mb-2 mb-lg-0 col-lg-3">
                                                <div class="dailyCard">
                                                    <h4 class="titleWithDesc">
                                                        {{ ratioCompute.value }}
                                                    </h4>
                                                    <span class="dashInfoTitle">{{ ratioCompute.shortName }}<i
                                                            class="ps-1 uil uil-info-circle"
                                                            data-bs-custom-class="tooltipLargeLeft"
                                                            data-bs-toggle="tooltip" data-bs-html="true"
                                                            :data-bs-title="ratioCompute.tooltipTitle"></i></span>
                                                </div>
                                            </div>

                                            <!-- Profit Factor indicator -->
                                            <div class="col-6 col-lg-3">
                                                <div class="dailyCard">
                                                    <h4 class="titleWithDesc">
                                                        <span v-if="!isNaN(profitAnalysis[amountCase + 'ProfitFactor'])"
                                                            :class="profitAnalysis[amountCase + 'ProfitFactor'] >= 1 ? 'text-success' : 'text-danger'">{{
                                                                (profitAnalysis[amountCase +
                                                                    'ProfitFactor']).toFixed(2)
                                                            }}</span>
                                                        <span v-else>-</span>
                                                    </h4>
                                                    <span class="dashInfoTitle">Profit Factor (Wins $ ÷ Losses $)</span>
                                                    <small v-if="!isNaN(profitAnalysis[amountCase + 'ProfitFactor'])"
                                                        class="d-block mt-1">
                                                        {{ profitAnalysis[amountCase + 'ProfitFactor'] >= 1 ?
                                                            'Profitable' : 'Unprofitable' }}
                                                    </small>
                                                </div>
                                            </div>

                                            <div class="col-6 col-lg-3">
                                                <div class="dailyCard">
                                                    <h4 class="titleWithDesc">
                                                        <span v-if="!isNaN(profitAnalysis[amountCase + 'R'])"
                                                            :class="profitAnalysis[amountCase + 'R'] >= 1 ? 'text-success' : 'text-danger'">{{
                                                                (profitAnalysis[amountCase +
                                                                    'R']).toFixed(2)
                                                            }}</span>
                                                        <span v-else>-</span>
                                                    </h4>
                                                    <span class="dashInfoTitle">Win/Loss Ratio</span>
                                                    <small v-if="!isNaN(profitAnalysis[amountCase + 'R'])"
                                                        class="d-block mt-1">
                                                        Per share (Avg Win ÷ Avg Loss)
                                                    </small>
                                                </div>
                                            </div>

                                            <div v-show="profitAnalysis[amountCase + 'MfeR'] != null"
                                                class="col-6 col-lg-3">
                                                <div class="dailyCard">
                                                    <h4 class="titleWithDesc">
                                                        <span v-if="profitAnalysis[amountCase + 'MfeR'] != null">{{
                                                            (profitAnalysis[amountCase +
                                                                'MfeR']).toFixed(2)
                                                        }}</span>
                                                        <span v-else>-</span>
                                                    </h4>
                                                    <span class="dashInfoTitle">MFE P/L Ratio</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- SECOND LINE -->
                                    <div class="col-12">
                                        <div class="row">
                                            <!-- Left square -->
                                            <div class="col-12 order-lg-2 col-lg-6">
                                                <!-- first line -->
                                                <div class="row mb-2">
                                                    <div class="col-6">
                                                        <div class="dailyCard">
                                                            <h5 class="titleWithDesc">
                                                                <span v-if="profitAnalysis[amountCase + 'AvWinPerShare'] !== undefined &&
                                                                    profitAnalysis[amountCase + 'AvWinPerShare'] !== null &&
                                                                    !isNaN(profitAnalysis[amountCase + 'AvWinPerShare']) &&
                                                                    profitAnalysis[amountCase + 'AvWinPerShare'] > 0">
                                                                    {{ useTwoDecCurrencyFormat(profitAnalysis[amountCase
                                                                        + 'AvWinPerShare']) }}
                                                                </span>
                                                                <span v-else>-</span>
                                                            </h5>
                                                            <span class="dashInfoTitle">Win Per Share (avg.)</span>
                                                        </div>
                                                    </div>
                                                    <div class="col-6">
                                                        <div class="dailyCard">
                                                            <h5 class="titleWithDesc">
                                                                <span v-if="profitAnalysis[amountCase + 'AvLossPerShare'] !== undefined &&
                                                                    profitAnalysis[amountCase + 'AvLossPerShare'] !== null &&
                                                                    !isNaN(profitAnalysis[amountCase + 'AvLossPerShare']) &&
                                                                    profitAnalysis[amountCase + 'AvLossPerShare'] > 0">
                                                                    {{ useTwoDecCurrencyFormat(profitAnalysis[amountCase
                                                                        + 'AvLossPerShare']) }}
                                                                </span>
                                                                <span v-else>-</span>
                                                            </h5>
                                                            <span class="dashInfoTitle">Loss Per Share (avg.)</span>
                                                        </div>
                                                    </div>
                                                </div>

                                                <!-- second line -->
                                                <div class="row mb-2 mb-lg-0">
                                                    <div class="col-6">
                                                        <div class="dailyCard">
                                                            <h5 class="titleWithDesc">
                                                                <span
                                                                    v-if="profitAnalysis[amountCase + 'HighWinPerShare'] > 0">{{
                                                                        useTwoDecCurrencyFormat(profitAnalysis[amountCase +
                                                                            'HighWinPerShare'])
                                                                    }}</span>
                                                                <span v-else>-</span>
                                                            </h5>
                                                            <span class="dashInfoTitle">Win Per Share (high)</span>
                                                        </div>
                                                    </div>
                                                    <div class="col-6">
                                                        <div class="dailyCard">
                                                            <h5 class="titleWithDesc">
                                                                <span
                                                                    v-if="profitAnalysis[amountCase + 'HighLossPerShare'] > 0">{{
                                                                        useTwoDecCurrencyFormat(profitAnalysis[amountCase +
                                                                            'HighLossPerShare']) }}</span>
                                                                <span v-else>-</span>
                                                            </h5>
                                                            <span class="dashInfoTitle">Loss Per Share (high)</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>


                                            <!-- Right square -->
                                            <div class="col-12 order-lg-1 col-lg-6">
                                                <div class="row text-center mb-3">
                                                    <div
                                                        v-bind:class="[satisfactionArray.length > 0 ? 'col-6' : 'col-12']">
                                                        <div class="dailyCard h-100 chart-equal-height">
                                                            <div v-if="dashboardIdMounted">
                                                                <div v-bind:key="renderData" id="pieChart1"
                                                                    class="chartIdCardClass">
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    <div v-show="satisfactionArray.length > 0" class="col-6">
                                                        <div class="dailyCard h-100 chart-equal-height">
                                                            <div v-if="dashboardIdMounted">
                                                                <div v-bind:key="renderData" id="pieChart2"
                                                                    class="chartIdCardClass">
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- ============ LINE 3 : TOTAL CHARTS ============ -->
                        <div class="col-12">
                            <div class="row">
                                <!-- CUMULATIVE P&L -->
                                <div class="col-12 mb-3">
                                    <div class="dailyCard">
                                        <h6>Cumulated P&L</h6>
                                        <!--<div class="text-center" v-if="!dashboardChartsMounted">
                                    <div class="spinner-border text-blue" role="status"></div>
                                </div>-->
                                        <div v-bind:key="renderData" id="lineBarChart1" class="chartClass"></div>
                                    </div>
                                </div>

                                <!-- APPT/APPS/PROFIT FACTOR CHART -->
                                <div class="col-12 col-xl-6 mb-3">
                                    <div class="dailyCard">
                                        <h6>{{ ratioCompute.name }} <span
                                                v-if="ratioCompute.name != 'Profit Factor'">({{ ratioCompute.shortName
                                                }})</span></h6>
                                        <div v-bind:key="renderData" id="barChart1" class="chartClass"></div>
                                    </div>
                                </div>

                                <!-- WIN LOSS CHART -->
                                <div class="col-12 col-xl-6 mb-3">
                                    <div class="dailyCard">
                                        <h6>Win Rate</h6>
                                        <!--<div class="text-center" v-if="!dashboardChartsMounted">
                                    <div class="spinner-border text-blue" role="status"></div>
                                </div>-->
                                        <div v-bind:key="renderData" id="barChart2" class="chartClass"></div>
                                    </div>
                                </div>

                            </div>
                        </div>



                    </div>

                    <!-- ============ TIME ============ -->
                    <div v-bind:class="'tab-pane fade ' + (selectedDashTab == 'timeTab' ? 'active show' : '')"
                        id="timeNav" role="tabpanel" aria-labelledby="nav-time-tab">
                        <div class="col-12">
                            <div class="row">
                                <!-- GROUP BY DAY OF WEEK -->
                                <div class="col-12 col-xl-4 mb-3">
                                    <div class="dailyCard">
                                        <h6>Group by Day of Week ({{ ratioCompute.shortName }})
                                        </h6>
                                        <!--<div class="text-center" v-if="!dashboardChartsMounted">
                                    <div class="spinner-border text-blue" role="status"></div>
                                </div>-->
                                        <div v-bind:key="renderData" id="barChartNegative3" class="chartClass"></div>
                                    </div>
                                </div>

                                <!-- GROUP BY TIMEFRAME -->
                                <div class="col-12 col-xl-4 mb-3">
                                    <div class="dailyCard">
                                        <h6>Group by Timeframe ({{ ratioCompute.shortName }})
                                        </h6>
                                        <!--<div class="text-center" v-if="!dashboardChartsMounted">
                                    <div class="spinner-border text-blue" role="status"></div>
                                </div>-->
                                        <div v-bind:key="renderData" id="barChartNegative1" class="chartClass"></div>
                                    </div>
                                </div>

                                <!-- GROUP BY DURATION -->
                                <div class="col-12 col-xl-4 mb-3">
                                    <div class="dailyCard">
                                        <h6>Group by Duration ({{ ratioCompute.shortName }})
                                        </h6>
                                        <!--<div class="text-center" v-if="!dashboardChartsMounted">
                                    <div class="spinner-border text-blue" role="status"></div>
                                </div>-->
                                        <div v-bind:key="renderData" id="barChartNegative2" class="chartClass"></div>
                                    </div>
                                </div>


                                <!-- SCATTER WINS
                                <div class="col-12">
                                    <div class="dailyCard">
                                        <h6>Scatter Wins</h6>
                                        <div v-bind:key="renderData" id="scatterChart1" class="chartClass"></div>
                                    </div>
                                </div>

                                SCATTER LOSSES 
                                <div class="col-12">
                                    <div class="dailyCard">
                                        <h6>Scatter Losses</h6>
                                        <div v-bind:key="renderData" id="scatterChart2" class="chartClass"></div>
                                    </div>
                                </div>-->
                                <!-- ============ LINE 4: TRADE DISTRIBUTION & PERFORMANCE BY DAY ============ -->
                                <div class="col-12">
                                    <div class="row">
                                        <!-- TRADE DISTRIBUTION BY DAY OF THE WEEK -->
                                        <div class="col-12 col-xl-6 mb-3">
                                            <div class="dailyCard">
                                                <h6>Trade Distribution by Day of the Week</h6>
                                                <div v-bind:key="renderData" id="tradeDistributionChart"
                                                    class="chartClass"></div>
                                            </div>
                                        </div>

                                        <!-- PERFORMANCE BY DAY OF THE WEEK -->
                                        <div class="col-12 col-xl-6 mb-3">
                                            <div class="dailyCard">
                                                <h6>Performance by Day of the Week</h6>
                                                <div v-bind:key="renderData" id="performanceByDayChart"
                                                    class="chartClass"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- ============ LINE 5: DAY OF WEEK SUMMARY TABLE ============ -->
                                <div class="col-12 mb-3">
                                    <div class="dailyCard">
                                        <h6>Summary</h6>
                                        <div class="table-responsive">
                                            <!-- added .stats-table, colgroup to lock in the Winning % width -->
                                            <table class="stats-table">
                                                <colgroup>
                                                    <col class="col-digit"/> <!-- Day -->
                                                    <col class="col-digit"/> <!-- Net Profit -->
                                                    <col class="col-winning" /> <!-- Winning % -->
                                                    <col class="col-digit"/> <!-- Total Profit -->
                                                    <col class="col-digit"/> <!-- Total Loss -->
                                                    <col class="col-digit"/> <!-- Trades -->
                                                    <col class="col-digit"/> <!-- Volume -->
                                                </colgroup>
                                                <thead>
                                                    <tr>
                                                        <th>Day</th>
                                                        <th>Net Profit</th>
                                                        <th >Winning %</th>
                                                        <th>Total Profit</th>
                                                        <th>Total Loss</th>
                                                        <th>Trades</th>
                                                        <th>Volume</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <template v-for="(dayData, index) in getDayOfWeekSummary()" :key="index">
                                                        <tr @click="toggleDayDetails(dayData.name)" :class="{'active-row': expandedDays[dayData.name]}">
                                                            <td>
                                                                <div class="d-flex align-items-center">
                                                                    <i :class="expandedDays[dayData.name] ? 'fa fa-caret-down' : 'fa fa-caret-right'" class="mr-2"></i>
                                                                    {{ dayData.name }}
                                                                </div>
                                                            </td>
                                                            <td
                                                                :class="dayData.netProfit >= 0 ? 'text-success' : 'text-danger'">
                                                                {{ useTwoDecCurrencyFormat(dayData.netProfit) }}
                                                            </td>
                                                            <td>
                                                                <div class="dual-progress">
                                                                    <div class="dual-progress__loss"
                                                                        :style="{ width: (dayData.lossPercentage / 2) + '%' }">
                                                                    </div>
                                                                    <div class="dual-progress__win"
                                                                        :style="{ width: (dayData.winPercentage / 2) + '%' }">
                                                                    </div>
                                                                </div>
                                                                <small>{{ dayData.winPercentage.toFixed(2) }}%</small>
                                                                <small v-if="dayData.winCount + dayData.lossCount < dayData.trades" class="d-block text-secondary">
                                                                  ({{ dayData.winCount }}/{{ dayData.winCount + dayData.lossCount }})
                                                                </small>
                                                                <small v-else class="d-block text-secondary">
                                                                  ({{ dayData.winCount }}/{{ dayData.trades }})
                                                                </small>
                                                            </td>

                                                            <td class="text-success">
                                                                {{ useTwoDecCurrencyFormat(dayData.totalProfit) }}
                                                            </td>
                                                            <td class="text-danger">
                                                                {{ useTwoDecCurrencyFormat(dayData.totalLoss) }}
                                                            </td>
                                                            <td>{{ dayData.trades }}</td>
                                                            <td>{{ useThousandFormat(dayData.volume) }}</td>
                                                        </tr>
                                                        <!-- Expanded row with day details -->
                                                        <tr v-if="expandedDays[dayData.name]" class="expanded-details">
                                                            <td colspan="7">
                                                                <div class="day-trades-container">
                                                                    <div class="day-trades-header">
                                                                        <h6>{{ dayData.name }} Trades</h6>
                                                                        <div class="pagination-controls" v-if="dayTradesPages[dayData.name] > 1">
                                                                            <button 
                                                                                class="btn btn-sm" 
                                                                                :disabled="dayTradesPagination[dayData.name] === 1"
                                                                                @click="changePage(dayData.name, dayTradesPagination[dayData.name] - 1)">
                                                                                Previous
                                                                            </button>
                                                                            <span>Page {{ dayTradesPagination[dayData.name] }} of {{ dayTradesPages[dayData.name] }}</span>
                                                                            <button 
                                                                                class="btn btn-sm" 
                                                                                :disabled="dayTradesPagination[dayData.name] === dayTradesPages[dayData.name]"
                                                                                @click="changePage(dayData.name, dayTradesPagination[dayData.name] + 1)">
                                                                                Next
                                                                            </button>
                                                                        </div>
                                                                    </div>
                                                                    <table class="day-trades-table">
                                                                        <thead>
                                                                            <tr>
                                                                                <th>Date</th>
                                                                                <th>Time</th>
                                                                                <th>Symbol</th>
                                                                                <th>Side</th>
                                                                                <th>Qty</th>
                                                                                <th>Price</th>
                                                                                <th>P/L</th>
                                                                            </tr>
                                                                        </thead>
                                                                        <tbody>
                                                                            <tr v-for="(trade, tradeIndex) in getPaginatedDayTrades(dayData.name)" :key="`${dayData.name}-${tradeIndex}`">
                                                                                <td>{{ formatDate(trade.date) }}</td>
                                                                                <td>{{ formatTime(trade.date) }}</td>
                                                                                <td>{{ trade.symbol }}</td>
                                                                                <td :class="trade.side === 'buy' ? 'text-success' : 'text-danger'">{{ trade.side }}</td>
                                                                                <td>{{ trade.quantity }}</td>
                                                                                <td>{{ useTwoDecCurrencyFormat(trade.price) }}</td>
                                                                                <td :class="trade.profit >= 0 ? 'text-success' : 'text-danger'">
                                                                                    {{ useTwoDecCurrencyFormat(trade.profit) }}
                                                                                </td>
                                                                            </tr>
                                                                            <tr v-if="getPaginatedDayTrades(dayData.name).length === 0">
                                                                                <td colspan="7" class="text-center">No trades to display</td>
                                                                            </tr>
                                                                        </tbody>
                                                                    </table>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    </template>
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>


                            </div>
                        </div>
                    </div>

                    <!-- ============ TRADES ============ -->
                    <div v-bind:class="'tab-pane fade ' + (selectedDashTab == 'tradesTab' ? 'active show' : '')"
                        id="tradesNav" role="tabpanel" aria-labelledby="nav-trades-tab">
                        <div class="col-12">
                            <div class="row">

                                <!-- Return vs Holding Time Chart -->
                                <div class="col-12 mb-3">
                                    <div class="dailyCard">
                                        <h6>Return vs. Holding Time (Days)</h6>
                                        <div v-bind:key="renderData" id="returnVsDaysChart" class="chartClass"></div>
                                        <div class="mt-3">
                                            <div v-if="holdingTimeStats.hasTrades">
                                                <div class="row text-center mb-3">
                                                    <div class="col-6">
                                                        <h5 class="titleWithDesc">{{ holdingTimeStats.average }}</h5>
                                                        <span class="dashInfoTitle">Average Holding Time</span>
                                                    </div>
                                                    <div class="col-6">
                                                        <h5 class="titleWithDesc">{{ holdingTimeStats.optimalBucketName
                                                            }}</h5>
                                                        <span class="dashInfoTitle">Optimal Holding Time <small>(Avg P&L:
                                                                {{ holdingTimeStats.maxAveragePnl }})</small></span>
                                                    </div>
                                                </div>

                                                <h6>Holding Time Analysis</h6>
                                                <div class="table-responsive">
                                                    <table class="stats-table">
                                                        <thead>
                                                            <tr>
                                                                <th>Holding Period</th>
                                                                <th>Trades</th>
                                                                <th>Total P&L</th>
                                                                <th>Avg P&L / Trade</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            <tr v-for="bucket in holdingTimeStats.buckets"
                                                                :key="bucket.name">
                                                                <td>{{ bucket.name }}</td>
                                                                <td>{{ bucket.trades }}</td>
                                                                <td
                                                                    :class="{ 'text-success': bucket.totalPnl > 0, 'text-danger': bucket.totalPnl < 0 }">
                                                                    {{ bucket.totalPnl }}</td>
                                                                <td
                                                                    :class="{ 'text-success': bucket.avgPnl > 0, 'text-danger': bucket.avgPnl < 0 }">
                                                                    {{ bucket.avgPnl }}</td>
                                                            </tr>
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                            <div v-else class="text-center">
                                                <p>No trade data available for holding time analysis.</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- GROUP BY TRADES -->
                                <div class="col-12 col-xl-6 mb-3">
                                    <div class="dailyCard">
                                        <h6>Group by Trades ({{ ratioCompute.shortName }})</h6>
                                        <!--<div class="text-center" v-if="!dashboardChartsMounted">
                                    <div class="spinner-border text-blue" role="status"></div>
                                </div>-->
                                        <div v-bind:key="renderData" id="barChartNegative4" class="chartClass"></div>
                                    </div>
                                </div>

                                <!-- GROUP BY EXECUTIONS -->
                                <div class="col-12 col-xl-6 mb-3">
                                    <div class="dailyCard">
                                        <h6>Group by Executions ({{ ratioCompute.shortName }})</h6>
                                        <!--<div class="text-center" v-if="!dashboardChartsMounted">
                                    <div class="spinner-border text-blue" role="status"></div>
                                </div>-->
                                        <div v-bind:key="renderData" id="barChartNegative7" class="chartClass"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- ============ SETUPS ============ -->
                    <div v-bind:class="'tab-pane fade ' + (selectedDashTab == 'setupsTab' ? 'active show' : '')"
                        id="setupsNav" role="tabpanel" aria-labelledby="nav-setups-tab">
                        <div class="col-12">
                            <div class="row">

                                <!-- GROUP BY POSITION -->
                                <div class="col-12 col-xl-6 mb-3">
                                    <div class="dailyCard">
                                        <h6>Group by Position ({{ ratioCompute.shortName }})</h6>
                                        <div class="text-center" v-if="!dashboardChartsMounted">
                                            <div class="spinner-border text-blue" role="status"></div>
                                        </div>
                                        <div v-bind:key="renderData" id="barChartNegative17" class="chartClass"></div>
                                    </div>
                                </div>

                                <!-- GROUP BY TAGS -->
                                <div class="col-12 col-xl-6 mb-3">
                                    <div class="dailyCard">
                                        <h6>Group by Tag ({{ ratioCompute.shortName }})</h6>
                                        <div class="text-center" v-if="!dashboardChartsMounted">
                                            <div class="spinner-border text-blue" role="status"></div>
                                        </div>
                                        <div v-bind:key="renderData" id="barChartNegative18" class="chartClass"></div>
                                    </div>
                                </div>

                                <!-- GROUP BY TAG COMBINATION -->
                                <div class="col-12 col-xl-6 mb-3" v-for="obj in barChartNegativeTagGroups">
                                    <div class="dailyCard">
                                        <h6>Group by Tag Group - {{ obj.name }} ({{ ratioCompute.shortName }})</h6>
                                        <div class="text-center" v-if="!dashboardChartsMounted">
                                            <div class="spinner-border text-blue" role="status"></div>
                                        </div>
                                        <div v-bind:key="renderData" :id="'barChartNegative' + obj.id"
                                            class="chartClass">
                                        </div>
                                    </div>
                                </div>

                            </div>
                        </div>
                    </div>

                    <!-- ============ FINANCIALS ============ -->
                    <div v-bind:class="'tab-pane fade ' + (selectedDashTab == 'financialsTab' ? 'active show' : '')"
                        id="financialsNav" role="tabpanel" aria-labelledby="nav-financials-tab">
                        <div class="col-12">
                            <div class="row">

                                <!-- GROUP BY SYMBOL -->
                                <div class="col-12 col-xl-6 mb-3">
                                    <div class="dailyCard">
                                        <h6>Group by Symbol ({{ ratioCompute.shortName }})</h6>
                                        <!--<div class="text-center" v-if="!dashboardChartsMounted">
                                    <div class="spinner-border text-blue" role="status"></div>
                                </div>-->
                                        <div v-bind:key="renderData" id="barChartNegative16" class="chartClass"></div>
                                    </div>
                                </div>

                                <!-- GROUP BY FLOAT
                        <div class="col-12 col-xl-4 mb-3">
                            <div class="dailyCard">
                                <h6>Group by Share Float</h6>
                                <div class="text-center" v-if="!dashboardChartsMounted">
                                    <div class="spinner-border text-blue" role="status"></div>
                                </div>
                                <div v-bind:key="renderData" id="barChartNegative12" class="chartClass"></div>
                            </div>
                        </div>-->

                                <!-- GROUP BY MARKET CAP
                        <div class="col-12 col-xl-4 mb-3">
                            <div class="dailyCard">
                                <h6>Group by Market Cap</h6>
                                <div class="text-center" v-if="!dashboardChartsMounted">
                                    <div class="spinner-border text-blue" role="status"></div>
                                </div>
                                <div v-bind:key="renderData" id="barChartNegative14" class="chartClass"></div>
                            </div>
                        </div>-->

                                <!-- GROUP BY ENTRYPRICE -->
                                <div class="col-12 col-xl-6 mb-3">
                                    <div class="dailyCard">
                                        <h6>Group by Entry Price ({{ ratioCompute.shortName }})</h6>
                                        <!--<div class="text-center" v-if="!dashboardChartsMounted">
                                    <div class="spinner-border text-blue" role="status"></div>
                                </div>-->
                                        <div v-bind:key="renderData" id="barChartNegative13" class="chartClass"></div>
                                    </div>
                                </div>

                                <!-- Return Distribution Chart -->
                                <div class="col-12 mb-3">
                                    <div class="dailyCard">
                                        <h6>Number of Trades vs. Return, gain sum (%)</h6>
                                        <ReturnDistributionChart :trades="filteredTrades"/>
                                        
                                        <!-- Return Stats -->
                                        <div class="mt-3" v-if="returnStats.hasTrades">
                                            <div class="row text-center">
                                                <div class="col-6 col-lg-3 mb-2">
                                                    <div class="dailyCard p-2 h-100">
                                                        <h5 class="titleWithDesc mb-1">{{ returnStats.avgReturn }}</h5>
                                                        <span class="dashInfoTitle">Avg Return (%)</span>
                                                    </div>
                                                </div>
                                                <div class="col-6 col-lg-3 mb-2">
                                                    <div class="dailyCard p-2 h-100">
                                                        <h5 class="titleWithDesc mb-1">{{ returnStats.totalReturn }}</h5>
                                                        <span class="dashInfoTitle">Total Return (%)</span>
                                                    </div>
                                                </div>
                                                <div class="col-6 col-lg-3 mb-2">
                                                    <div class="dailyCard p-2 h-100">
                                                        <h5 class="titleWithDesc mb-1">{{ returnStats.avgWinnerReturn }}</h5>
                                                        <span class="dashInfoTitle">Avg Return (%) Winner</span>
                                                    </div>
                                                </div>
                                                <div class="col-6 col-lg-3 mb-2">
                                                    <div class="dailyCard p-2 h-100">
                                                        <h5 class="titleWithDesc mb-1">{{ returnStats.avgLoserReturn }}</h5>
                                                        <span class="dashInfoTitle">Avg Return (%) Loser</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    </div>
</template>


<style scoped>
/* General Dashboard Styling */
.row.mt-2 {
    padding: 0 15px; /* Add some horizontal padding to the main content area */
    position: relative;
    z-index: 1; /* Keep content below dropdowns */
}

/* Chart Container Sizing */
.chart-equal-height {
    min-height: 230px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

/* Ensure dropdowns in dashboard appear on top */
select, .form-select {
    position: relative !important;
    z-index: 9999 !important;
}

select option {
    background-color: #2a2a4a !important;
    color: #e0e0e0 !important;
    z-index: 9999 !important;
}

/* Modern Card Styling */
.dailyCard {
    background-color: #1e1e2f; /* Darker background for cards */
    border-radius: 12px; /* More rounded corners */
    padding: 25px; /* Increased padding */
    margin-bottom: 20px; /* Spacing between cards */
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2); /* More pronounced shadow */
    color: #e0e0e0; /* Light text color */
    transition: transform 0.2s ease, box-shadow 0.2s ease; /* Smooth transitions */
    position: relative;
    z-index: 1; /* Keep below dropdowns */
}

.dailyCard:hover {
    transform: translateY(-3px); /* Subtle lift effect on hover */
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3); /* Enhanced shadow on hover */
}

.titleWithDesc {
    font-size: 1.8rem; /* Larger, more prominent titles */
    font-weight: 700;
    color: #6a8dff; /* Accent color for key numbers */
    margin-bottom: 5px;
}

.dashInfoTitle {
    font-size: 0.9rem;
    color: #a0a0a0; /* Muted color for descriptions */
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Tab Navigation Styling */
.nav-tabs {
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 20px;
}

.nav-link {
    color: #a0a0a0; /* Muted color for inactive tabs */
    border: none;
    border-radius: 8px 8px 0 0;
    padding: 12px 20px;
    transition: all 0.3s ease;
    font-weight: 600;
}

.nav-link:hover {
    background-color: #2a2a4a; /* Darker hover background */
    color: #fff;
}

.nav-link.active {
    background-color: #1e1e2f; /* Active tab background */
    color: #6a8dff; /* Accent color for active tab text */
    border-color: rgba(255, 255, 255, 0.1) rgba(255, 255, 255, 0.1) #1e1e2f; /* Match card background */
    border-bottom: 3px solid #6a8dff; /* Accent line for active tab */
}

/* Table Styling */
.stats-table {
    width: 100%;
    table-layout: fixed;
    border-collapse: separate; /* For rounded corners on cells */
    border-spacing: 0 8px; /* Space between rows */
}

.stats-table th,
.stats-table td {
    padding: 12px 15px;
    text-align: left;
    border: none; /* Remove default borders */
}

.stats-table thead th {
    background-color: #2a2a4a; /* Header background */
    color: #fff;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.85rem;
    letter-spacing: 0.5px;
}

.stats-table tbody tr {
    background-color: #25253a; /* Row background */
    border-radius: 8px; /* Rounded rows */
    transition: background-color 0.2s ease;
}

.stats-table tbody tr:hover {
    background-color: #2a2a4a; /* Darker row on hover */
}

.stats-table .col-digit {
    width: 80px;
}

.stats-table .col-winning {
    width: 150px;
}

.dual-progress {
    position: relative;
    height: 8px; /* Thicker progress bar */
    width: 80%; /* Wider progress bar */
    background-color: rgba(255, 255, 255, 0.1); /* Lighter background for progress bar */
    border-radius: 4px;
    overflow: hidden;
    margin: 0 auto 8px auto; /* Center and add more margin */
}

.dual-progress__loss {
    position: absolute;
    top: 0;
    right: 50%;
    height: 100%;
    background-color: #ff6b6b; /* Softer red for loss */
    transform-origin: right center;
}

.dual-progress__win {
    position: absolute;
    top: 0;
    left: 50%;
    height: 100%;
    background-color: #4caf50; /* Vibrant green for win */
    transform-origin: left center;
}

.chartIdCardClass {
    max-width: 250px; /* Slightly larger charts */
    height: 210px; /* Increased fixed height */
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Specific adjustments for text colors within cards */
.dailyCard .text-success {
    color: #4caf50 !important; /* Ensure vibrant green for success */
}

.dailyCard .text-danger {
    color: #ff6b6b !important; /* Ensure softer red for danger */
}

.dailyCard small {
    color: #a0a0a0;
}

/* Ensure dashboard content stays below dropdowns */
.overview-tab,
.time-tab,
.trades-tab,
.setups-tab,
.financials-tab {
    position: relative;
    z-index: 1 !important;
}

/* Fix tabs navigation to stay below select dropdowns */
.nav-tabs {
    position: relative;
    z-index: 1 !important;
}

/* Dashboard card styling */
.dailyCard {
    position: relative;
    z-index: 1 !important;
}

/* Expandable row styling */
.stats-table tbody tr {
    cursor: pointer;
    transition: background-color 0.2s ease;
}

.stats-table tbody tr.active-row {
    background-color: #323252; /* Highlight active/expanded row */
}

.expanded-details {
    background-color: #1e1e2f !important;
}

.day-trades-container {
    padding: 15px;
    background-color: #1e1e2f;
    border-radius: 8px;
}

.day-trades-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.pagination-controls {
    display: flex;
    align-items: center;
    gap: 10px;
}

.pagination-controls .btn {
    background-color: #2a2a4a;
    border: none;
    color: #e0e0e0;
    padding: 5px 10px;
    border-radius: 4px;
    font-size: 0.85rem;
    transition: background-color 0.2s ease;
}

.pagination-controls .btn:hover:not(:disabled) {
    background-color: #3a3a5a;
}

.pagination-controls .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.day-trades-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 5px;
}

.day-trades-table thead th {
    background-color: #2a2a4a;
    color: #e0e0e0;
    text-align: left;
    padding: 8px;
    font-size: 0.85rem;
}

.day-trades-table tbody td {
    padding: 8px;
    border-top: 1px solid #323252;
    color: #e0e0e0;
}

.day-trades-table tbody tr:hover {
    background-color: #262640;
}
</style>