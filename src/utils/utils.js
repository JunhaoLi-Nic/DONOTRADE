import { useRoute } from "vue-router";
import { pageId, timeZoneTrade, currentUser, periodRange, selectedDashTab, renderData, selectedPeriodRange, selectedPositions, selectedTimeFrame, selectedRatio, selectedAccount, selectedGrossNet, selectedPlSatisfaction, selectedBroker, selectedDateRange, selectedMonth, selectedAccounts, amountCase, screenshotsPagination, diaryUpdate, diaryButton, selectedItem, playbookUpdate, playbookButton, sideMenuMobileOut, spinnerLoadingPage, dashboardChartsMounted, dashboardIdMounted, hasData, renderingCharts, screenType, selectedRange, dailyQueryLimit, dailyPagination, endOfList, spinnerLoadMore, windowIsScrolled, legacy, selectedTags, tags, filteredTrades, idCurrent, idPrevious, idCurrentType, idCurrentNumber, idPreviousType, idPreviousNumber, screenshots, screenshotsInfos, tabGettingScreenshots, apis, layoutStyle, countdownInterval, countdownSeconds, barChartNegativeTagGroups, availableTags, groups, deviceTimeZone, dailyPageMounted, calendarData, miniCalendarsData } from "../stores/globals.js"
import { useECharts, useRenderDoubleLineChart, useRenderPieChart } from './charts.js';
import { useDeleteDiary, useGetDiaries, useUploadDiary } from "./diary.js";
import { useDeleteScreenshot, useGetScreenshots, useGetScreenshotsPagination } from '../utils/screenshots.js'
import { useDeletePlaybook } from "./playbooks.js";
import { useCalculateProfitAnalysis, useGetFilteredTrades, useGetFilteredTradesForDaily, useGroupTrades, useTotalTrades, useDeleteTrade, useDeleteExcursions } from "./trades.js";
import { useLoadCalendar } from "./calendar.js";
import { useGetAvailableTags, useGetExcursions, useGetSatisfactions, useGetTags, useGetNotes } from "./daily.js";
import { AuthService } from '../services/auth.js';
import { nextTick } from 'vue';

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
import Shepherd from 'shepherd.js'

/**************************************
* INITS
**************************************/

export function useInitTab(param) {
    console.log("\nINIT TAB for " + param)

    let hideCurrentTab = false
    let htmlIdCurrent
    let htmlIdPrevious
    let firstTimeClick
    idCurrent.value = undefined // we set (back) to undefined because when click on modal on daily, we hide the tabs so we need to reinitiate them
    idPrevious.value = undefined

    var triggerTabList = [].slice.call(document.querySelectorAll('#nav-tab button'))
    //console.log("trigger tab list "+triggerTabList)
    var self = // is.value needed or else could not call function inside eventlistener


        triggerTabList.forEach((triggerEl) => {
            //console.log("triggerEl "+triggerEl.getAttribute('id'))
            /*var tabTrigger = new bootstrap.Tab(triggerEl)
            triggerEl.addEventListener('click', function(event) {
                console.log("clicking")
                //event.preventDefault()
                //tabTrigger.show()
            })*/
            if (param == "dashboard") {
                // GET TAB ID THAT IS CLICKED
                //console.log(" -> triggerTabList Dashboard")
                triggerEl.addEventListener('shown.bs.tab', async (event) => {
                    //console.log("target " + event.target.getAttribute('id')) // newly activated tab
                    selectedDashTab.value = event.target.getAttribute('id')
                    console.log("selected tab " + selectedDashTab.value)
                    localStorage.setItem('selectedDashTab', event.target.getAttribute('id'))
                    await (renderData.value += 1)
                    await useECharts("init")
                    //console.log("related" + event.relatedTarget) // previous active tab
                })
            }

            if (param == "daily") {
                // GET TAB ID THAT IS CLICKED

                //console.log(" -> triggerTabList Daily")
                let idClicked
                triggerEl.addEventListener('click', async (event) => {
                    /*if (idClicked == event.target.getAttribute('id')) {
                        console.log(" already clicked")
                    } else {
                        console.log(" first time clicked")
                        idClicked = event.target.getAttribute('id')
                    }
                    console.log(" -> Click on " + event.target.getAttribute('id'))
                    */
                    if (idCurrent.value != undefined) idPrevious.value = idCurrent.value // in case it's not on page load and we already are clicking on tabs, then inform that the previsous clicked tab (wich is for the moment current) should now become previous

                    idCurrent.value = event.target.getAttribute('id')


                    if (idPrevious.value == undefined) {
                        firstTimeClick = true
                        idPrevious.value = idCurrent.value //on page load, first time we click
                        hideCurrentTab = !hideCurrentTab // is.value counter intuitive but because further down we toggle hidCurrentTab, i need to toggle here if its first time click on load or else down there it would be hide true the first time. So here we set true so that further down, on first time click on page load it becomes false

                    }

                    //console.log(" -> id Current: " + idCurrent.value + " and previous: " + idPrevious.value)

                    idCurrentType.value = idCurrent.value.split('-')[0]
                    idCurrentNumber.value = idCurrent.value.split('-')[1]
                    idPreviousType.value = idPrevious.value.split('-')[0]
                    idPreviousNumber.value = idPrevious.value.split('-')[1]
                    htmlIdCurrent = "#" + idCurrentType.value + "Nav-" + idCurrentNumber.value
                    htmlIdPrevious = "#" + idPreviousType.value + "Nav-" + idPreviousNumber.value

                    //console.log(" -> Daily tab click on "+idCurrentType.value + " - index "+idCurrentNumber.value)
                    //console.log(" -> filtered trades "+JSON.stringify(filteredTrades[idCurrentNumber.value]))

                    if (idCurrentType.value === "screenshots") {
                        let screenshotsDate = filteredTrades[idCurrentNumber.value].dateUnix
                        //console.log(" -> Clicked on screenshots tab in Daily so getting screensots for "+screenshotsDate)
                        //console.log(" screenshots infos " + JSON.stringify(screenshotsInfos))
                        let index = screenshotsInfos.findIndex(obj => obj.dateUnixDay == screenshotsDate)
                        //console.log(" index " + index)
                        if (index != -1) {

                            if (screenshots.length == 0 || (screenshots.length > 0 && screenshots[0].dateUnixDay != screenshotsDate)) {
                                console.log("  --> getting Screenshots")
                                await (tabGettingScreenshots.value = true)
                                await useGetScreenshots(true, screenshotsDate)
                                await (tabGettingScreenshots.value = false)
                            } else {
                                console.log("  --> Screenshots already stored")
                            }
                        } else {
                            console.log("  --> No screenshots")
                        }
                        //console.log(" screenshots "+JSON.stringify(screenshots[0]))
                    }

                    if (idCurrent.value == idPrevious.value) {
                        hideCurrentTab = !hideCurrentTab;

                        if (hideCurrentTab) { // hide content
                            document.querySelector(htmlIdCurrent).classList.remove('show');
                            document.querySelector(htmlIdCurrent).classList.remove('active');
                            document.getElementById(idCurrent.value).classList.remove('active');
                        } else { // show content
                            document.querySelector(htmlIdCurrent).classList.add('show');
                            document.querySelector(htmlIdCurrent).classList.add('active');
                            document.getElementById(idCurrent.value).classList.add('active');
                        }
                    } else {
                        hideCurrentTab = false;

                        // In case of a different tab click, reset the previous tab
                        document.querySelector(htmlIdPrevious).classList.remove('show');
                        document.querySelector(htmlIdPrevious).classList.remove('active');
                        document.getElementById(idPrevious.value).classList.remove('active');
                    }

                })
            }
        })


}

// No longer needed since we're not using Parse

// Connect to FastAPI instead of Parse
export function useInitParse() {
    return new Promise(async (resolve, reject) => {
        console.log("\nINITIATING API CONNECTION")
        // Check if user is logged in via token
        const token = localStorage.getItem('auth_token');
        if (token) {
            console.log("User is authenticated via token");
        }
        let path = window.location.pathname
        
        try {
            // Check for auth redirection
            const isAuthenticated = AuthService.isAuthenticated();
            
            if ((!isAuthenticated) && path != "/" && path != "/register") {
                window.location.replace("/");
            } else if (isAuthenticated) {
                await useCheckCurrentUser();
            }
            
            resolve();
        } catch (error) {
            console.error(" -> Error initializing API:", error);
            reject(error);
        }
    })
}

// Using AuthService to get current user
export function useCheckCurrentUser() {
    console.log("\nCHECKING CURRENT USER")
    return new Promise((resolve, reject) => {
        var path = window.location.pathname
        
        // Get current user from AuthService
        currentUser.value = AuthService.getCurrentUser();
        
        if (path != "/" && path != "/register") {
            if (currentUser.value) {
                console.log("User is authenticated:", currentUser.value.email || currentUser.value.username)
            } else {
                console.log("Not authenticated, redirecting to login page")
                window.location.replace("/");
            }
        }
        if (path == "/" || path == "/register") {
            if (currentUser.value) {
                console.log("Already authenticated, redirecting to dashboard")
                window.location.replace("/dashboard");
            } else {
                console.log("Not logged in - showing login form")
            }
        }
        resolve()
    })
}

// Modified to use AuthService instead of Parse
export const useGetCurrentUser = () => {
    try {
        // Mark that we're accessing user data to prevent logout loops
        sessionStorage.setItem('last_user_access', Date.now().toString());
        
    // Use the AuthService to manage user state
    currentUser.value = AuthService.getCurrentUser();
    
    // If we have a token but no current user data, refresh from server
    if (AuthService.isAuthenticated() && !currentUser.value) {
            console.log("We have a token but no user data - refreshing user data");
            
            // Don't wait for the promise to avoid blocking
        AuthService.refreshUser()
            .then(user => {
                if (user) {
                    currentUser.value = user;
                }
            })
            .catch(error => {
                console.error("Error refreshing user:", error);
            });
    }
    
    return currentUser.value;
    } catch (error) {
        console.error("Error in useGetCurrentUser:", error);
        return null;
    }
}

export function useGetTimeZone() {
    console.log("Getting timezone. Current user:", currentUser.value);
    if (!currentUser.value) return;
    
    // Check if the user has explicitly set useDeviceTimeZone to true
    const useDeviceTz = currentUser.value.hasOwnProperty("useDeviceTimeZone") && 
                       currentUser.value.useDeviceTimeZone === true;
                       
    // Determine which timezone to use
    if (useDeviceTz) {
        timeZoneTrade.value = deviceTimeZone.value;
        console.log(" -> Using device timezone: " + timeZoneTrade.value);
    } else if (currentUser.value.hasOwnProperty("timeZone")) {
        timeZoneTrade.value = currentUser.value.timeZone;
        console.log(" -> Using selected timezone: " + timeZoneTrade.value);
    } else {
        timeZoneTrade.value = 'America/New_York';
        console.log(" -> Using default timezone: " + timeZoneTrade.value);
    }
}

export async function useGetPeriods() {
    //console.log(" -> Getting periods")
    return new Promise((resolve, reject) => {
        let temp = [{
            value: "all",
            label: "All",
            start: 0,
            end: 0
        }, {
            value: "thisWeek",
            label: "This Week",
            start: Number(dayjs().tz(timeZoneTrade.value).startOf('week').add(1, 'day').unix()), // we need to transform as number because later it's stringified and this becomes date format and note unix format
            end: Number(dayjs().tz(timeZoneTrade.value).endOf('week').add(1, 'day').unix())
        }, {
            value: "lastWeek",
            label: "Last Week",
            start: Number(dayjs().tz(timeZoneTrade.value).subtract(1, 'week').startOf('week').add(1, 'day').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).subtract(1, 'week').endOf('week').add(1, 'day').unix())
        }, {
            value: "lastWeekTilNow",
            label: "Last Week Until Now",
            start: Number(dayjs().tz(timeZoneTrade.value).subtract(1, 'week').startOf('week').add(1, 'day').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).endOf('week').add(1, 'day').unix())
        }, {
            value: "lastTwoWeeks",
            label: "Last Two Weeks",
            start: Number(dayjs().tz(timeZoneTrade.value).subtract(2, 'week').startOf('week').add(1, 'day').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).subtract(1, 'week').endOf('week').add(1, 'day').unix())
        }, {
            value: "lastTwoWeeksTilNow",
            label: "Last Two Weeks Until Now",
            start: Number(dayjs().tz(timeZoneTrade.value).subtract(2, 'week').startOf('week').add(1, 'day').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).endOf('week').add(1, 'day').unix())
        }, {
            value: "thisMonth",
            label: "This Month",
            start: Number(dayjs().tz(timeZoneTrade.value).startOf('month').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).endOf('month').unix())
        }, {
            value: "lastMonth",
            label: "Last Month",
            start: Number(dayjs().tz(timeZoneTrade.value).subtract(1, 'month').startOf('month').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).subtract(1, 'month').endOf('month').unix())
        }, {
            value: "lastMonthTilNow",
            label: "Last Month Until Now",
            start: Number(dayjs().tz(timeZoneTrade.value).subtract(1, 'month').startOf('month').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).endOf('month').unix())
        }, {
            value: "lastTwoMonths",
            label: "Last Two Months",
            start: Number(dayjs().tz(timeZoneTrade.value).subtract(2, 'month').startOf('month').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).subtract(1, 'month').endOf('month').unix())
        }, {
            value: "lastTwoMonthsTilNow",
            label: "Last Two Months Until Now",
            start: Number(dayjs().tz(timeZoneTrade.value).subtract(2, 'month').startOf('month').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).endOf('month').unix())
        }, {
            value: "lastThreeMonths",
            label: "Last Three Months",
            start: Number(dayjs().tz(timeZoneTrade.value).subtract(3, 'month').startOf('month').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).subtract(1, 'month').endOf('month').unix())
        }, {
            value: "lastThreeMonthsTilNow",
            label: "Last Three Months Until Now",
            start: Number(dayjs().tz(timeZoneTrade.value).subtract(3, 'month').startOf('month').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).endOf('month').unix())
        }, {
            value: "thisYear",
            label: "This Year",
            start: Number(dayjs().tz(timeZoneTrade.value).startOf('year').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).endOf('year').unix())
        }, {
            value: "lastYear",

            label: "Last Year",
            start: Number(dayjs().tz(timeZoneTrade.value).subtract(1, 'year').startOf('year').unix()),
            end: Number(dayjs().tz(timeZoneTrade.value).subtract(1, 'year').endOf('year').unix())
        }, {
            value: "custom",
            label: "Custom",
            start: -1,
            end: -1
        }]
        periodRange.length = 0
        temp.forEach(element => {
            periodRange.push(element)
        });
        resolve()
    });
}

export function useInitShepherd() {
    const tour = new Shepherd.Tour({
        useModalOverlay: true,
        defaultStepOptions: {
            classes: 'tour-guide',
            scrollTo: false,
            useModalOverlay: true,
        }
    });
    if (pageId.value != "dashboard") {
        alert("Please go to the dashboard page and launch the tutorial.")
        return
    }
    tour.addSteps([{
        id: 'step1',
        text: 'Welcome onboard. This guided tutorial will show you how TradeNote works.',
        buttons: [{
            text: 'Exit',
            action: tour.complete,
            classes: 'exitButton'
        }, {
            text: 'Next',
            action: tour.next
        }]
    }, {
        id: 'step2',
        text: "In the side menu, you can navigate all TradeNote pages.",
        attachTo: {
            element: '#step2',
            on: 'right-start'
        },
        buttons: [{
            text: 'Exit',
            action: tour.complete,
            classes: 'exitButton'
        },
        {
            text: 'Back',
            action: tour.back
        },
        {
            text: 'Next',
            action: tour.next
        }
        ],
        popperOptions: {
            modifiers: [{ name: 'offset', options: { offset: [0, 15] } }]
        }
    },
    {
        id: 'step3',
        text: 'The dashboard shows all your main metrics.',
        attachTo: {
            element: '#step3',
            on: 'right'
        },
        buttons: [{
            text: 'Exit',
            action: tour.complete,
            classes: 'exitButton'
        }, {
            text: 'Back',
            action: tour.back
        },
        {
            text: 'Next',
            action: tour.next
        }
        ]
    },
    {
        id: 'step4',
        text: '<p>Daily shows a detailed view of trades per day.</p><p>For each day, there is a 4 tabs for a given day:<ul><li>Trades: list of your trades</li><li>Blotter: your trades grouped by symbol</li><li>Screenshots: your annotated screenshots</li><li>Diary: your diary entries</li></ul></p><p>In the trades tab you can click on the table row to add additional information (note, tags, etc.).</p>',
        attachTo: {
            element: '#step4',
            on: 'right'
        },
        buttons: [{
            text: 'Exit',
            action: tour.complete,
            classes: 'exitButton'
        }, {
            text: 'Back',
            action: tour.back
        },
        {
            text: 'Next',
            action: tour.next
        }
        ]
    },
    {
        id: 'step5',
        text: 'Calendar displays a calendar view of your daily trades.',
        attachTo: {
            element: '#step5',
            on: 'right'
        },
        buttons: [{
            text: 'Exit',
            action: tour.complete,
            classes: 'exitButton'
        }, {
            text: 'Back',
            action: tour.back
        },
        {
            text: 'Next',
            action: tour.next
        }
        ]
    },

    {
        id: 'step6',
        text: 'Diary is where you can see and edit your diary entries.',
        attachTo: {
            element: '#step6',
            on: 'right'
        },
        buttons: [{
            text: 'Exit',
            action: tour.complete,
            classes: 'exitButton'
        }, {
            text: 'Back',
            action: tour.back
        },
        {
            text: 'Next',
            action: tour.next
        }
        ],
        popperOptions: {
            modifiers: [{ name: 'offset', options: { offset: [0, 15] } }]
        }
    },
    {
        id: 'step7',
        text: 'Screenshots is where you can see all your screenshots.',
        attachTo: {
            element: '#step7',
            on: 'right'
        },
        buttons: [{
            text: 'Exit',
            action: tour.complete,
            classes: 'exitButton'
        }, {
            text: 'Back',
            action: tour.back
        },
        {
            text: 'Next',
            action: tour.next
        }
        ]
    },
    {
        id: 'step8',
        text: 'Playbook is where you can see and edit your (yearly) playbook.',
        attachTo: {
            element: '#step8',
            on: 'right'
        },
        buttons: [{
            text: 'Exit',
            action: tour.complete,
            classes: 'exitButton'
        }, {
            text: 'Back',
            action: tour.back
        },
        {
            text: 'Next',
            action: tour.next
        }
        ]
    },
    {
        id: 'step10',
        text: "<p>You can filter your trades per date, account, gross vs net (excluding or including fees and commissions) and position (long and/or short).</p><p>You can also decide to aggregate data per day, week or year.</p><p>On certain graphs, you can decide to see data as Average Profit Per Trade (APPT), Average Profit Per Security (APPS) or as profit factor.</p><p><b>In order to see you trades, please make sure you have chosen the right date range and that you have chosen at least one account and position type.</b></p>",
        attachTo: {
            element: '#step10',
            on: 'bottom'
        },
        buttons: [{
            text: 'Exit',
            action: tour.complete,
            classes: 'exitButton'
        }, {
            text: 'Back',
            action: tour.back
        },
        {
            text: 'Next',
            action: tour.next
        }
        ],
        popperOptions: {
            modifiers: [{ name: 'offset', options: { offset: [0, 15] } }]
        }
    },
    {
        id: 'step11',
        text: "<p>Click here to add trades, diary entries, screenshots or playbooks.</p><ul><li>Trades is used for importing trades from your Broker's csv or excel file.</li><li>Diary is where you can write your daily thoughts and progress.</li><li>Screenshots is where you can add the screenshots of your charts. You can annotate the screenshot with drawings, notes and more. You can add 2 types of screenshots:<ul><li>General Setup: a general interesting screenshot, not related to any particular trade (you made).</li><li>Trade Entry: screenshot related to a particular trade you made, in which case you need to add the exact entry time of your execution to match your trade.</li></ul></li><li>Playbook is where you can write your (yearly) trading playbook.</li></ul>",
        attachTo: {
            element: '#step11',
            on: 'bottom'
        },
        buttons: [{
            text: 'Exit',
            action: tour.complete,
            classes: 'exitButton'
        }, {
            text: 'Back',
            action: tour.back
        },
        {
            text: 'Next',
            action: tour.next
        }
        ],
        popperOptions: {
            modifiers: [{ name: 'offset', options: { offset: [0, 15] } }]
        }
    },
    {
        id: 'step12',
        text: "In the sub-menu you can navigate to your settings, where you can amongst other add a profile picture, add API Keys and edit your tags. You can also see the version you are using as well as come back to this tutorial at any time as well as logout of your account (recommended when you update TradeNote version).",
        attachTo: {
            element: '#step12',
            on: 'bottom'
        },
        buttons: [{
            text: 'Back',
            action: tour.back
        },
        {
            text: 'Next',
            action: tour.next
        }
        ]
    },
    {
        id: 'step13',
        text: "That's it. You are now ready to use TradeNote. You can come back to this tutorial at any time by clicking 'Tutorial' in the sub-menu.",
        buttons: [{
            text: 'Back',
            action: tour.back
        },
        {
            text: 'Done',
            action: tour.complete
        }]
    },

    ])

    tour.start();

    Shepherd.on("complete", async () => {
        console.log("Tour complete")
        const parseObject = Parse.Object.extend("User");
        const query = new Parse.Query(parseObject);
        query.equalTo("objectId", currentUser.value.objectId);
        const results = await query.first();
        if (results) {
            await results.set("guidedTour", true)
            results.save().then(() => {
                console.log(" -> Updated user")
            })
        } else {
            console.log("  --> Could not find user. is.value a problem")
        }

    })

}

export async function useInitQuill(param) {
    return new Promise((resolve, reject) => {
        //console.log("param " + param)
        let quillEditor
        if (param != undefined) {
            quillEditor = '#quillEditor' + param
        } else {
            quillEditor = '#quillEditor'
        }
        //console.log("quilEditor " + quillEditor)
        let quill = new Quill(quillEditor, {
            modules: {
                toolbar: [
                    [{ header: [1, 2, 3, false] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    [{ 'list': 'ordered' }, { 'list': 'bullet' }],
                    [{ 'indent': '-1' }, { 'indent': '+1' }],
                    ['image'],
                ]
            },
            theme: 'snow'
        });
        quill.root.setAttribute('spellcheck', true)
        //console.log("quill " + quill)

        quill.on('text-change', () => {
            if (pageId.value == "addScreenshot") {
                setupUpdate.value.checkList = document.querySelector(".ql-editor").innerHTML
                //console.log("setup " + JSON.stringify(setupUpdate.value))
            }

            if (pageId.value == "addDiary") {
                diaryUpdate.diary = document.querySelector(".ql-editor").innerHTML
                diaryButton.value = true

                clearTimeout(countdownInterval.value);
                countdownSeconds.value = 5; // reset countdown
                countdownInterval.value = setInterval(function () {
                    //console.log(`Countdown: ${countdownSeconds.value}`);
                    countdownSeconds.value--;
                    if (countdownSeconds.value === 0) {
                        clearTimeout(countdownInterval.value);
                        useUploadDiary("autoSave")
                    }
                }, 1000); // 1 second interval
            }

            if (pageId.value == "addPlaybook") {
                playbookUpdate.playbook = document.querySelector(".ql-editor").innerHTML
                playbookButton.value = true
            }
        });
        resolve()
    })
}


export function useInitPopover() {
    console.log(" -> Init Popover");

    var popoverTriggerList

    const getTriggerList = () => {
        popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
        popoverTriggerList.forEach(function (popoverTriggerEl) {

            new bootstrap.Popover(popoverTriggerEl);
        });
    }

    getTriggerList()

    var popDel;

    document.addEventListener('click', async function (e) {
        if (e.target.classList.contains('popoverDelete')) {
            popDel = e.target;
            document.querySelectorAll('.popoverDelete').forEach(function (popDelete) {
                if (popDelete !== popDel) {
                    const popoverInstance = bootstrap.Popover.getInstance(popDelete);
                    if (popoverInstance) {
                        popoverInstance.hide();
                    }
                }
            });
        }

        if (e.target.classList.contains('popoverYes')) {
            document.querySelectorAll('.popoverDelete').forEach(function (popDelete) {
                if (popDelete === popDel) {
                    bootstrap.Popover.getInstance(popDelete).hide();
                }
            });
            if (pageId.value == "notes") {
                deleteNote.value();
            }
            if (pageId.value == "screenshots" || pageId.value == "daily") {
                useDeleteScreenshot();
            }
            if (pageId.value == "diary") {
                useDeleteDiary(true);
            }
            if (pageId.value == "playbook") {
                useDeletePlaybook();
            }

            if (pageId.value === "imports") {
                await useDeleteTrade()
                await useDeleteExcursions()
            }
        }

        if (e.target.classList.contains('popoverNo')) {
            document.querySelectorAll('.popoverDelete').forEach(function (popDelete) {
                if (popDelete === popDel) {
                    //console.log(" popDelete " + popDelete.classList)
                    //console.log(" popDel " + popDel.classList)
                    bootstrap.Popover.getInstance(popDelete).hide();
                }
            });
            selectedItem.value = null;
        }
    });
}

// Initialize Bootstrap tooltips
export const useInitTooltip = () => {
  // Enable tooltips
  const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
  const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))
  
  // Fix dropdown positioning
  const dropdownMenus = document.querySelectorAll('.dropdown-menu');
  dropdownMenus.forEach(menu => {
    menu.style.zIndex = '9999';
    menu.style.position = 'absolute';
  });

  // Ensure dropdown containers have proper z-index
  const dropdowns = document.querySelectorAll('.dropdown');
  dropdowns.forEach(dropdown => {
    dropdown.style.zIndex = '9999';
    dropdown.style.position = 'relative';
  });
}

export async function useInitPostHog() {
    return new Promise((resolve, reject) => {
        axios.post('/api/posthog')
            .then((response) => {
                //console.log(response);
                if (response.data && response.data.api_key && response.data.api_key !== "off") {
                    try {
                        window.posthog = window.posthog || {};
                        posthog.init(response.data.api_key, { 
                            api_host: response.data.host || 'https://eu.posthog.com',
                            loaded: function(posthog) {
                                console.log(" -> PostHog initialized successfully");
                            }
                        });
                    } catch (e) {
                        console.error(" -> PostHog initialization error:", e);
                        // Continue app operation even if analytics fails
                    }
                } else {
                    console.log(" -> Analytics Off");
                }
                resolve();
            })
            .catch((error) => {
                console.log(" -> Error PostHog id:", error);
                // Don't reject, just resolve and continue without analytics
                resolve();
            });
    });
}

/**
 * MOUNT
 * 
 * This section contains functions responsible for mounting and initializing
 * the main dashboard and related data. The mounting process typically involves:
 *   - Setting loading states and flags
 *   - Handling forced refreshes or data resets (e.g., after imports or deletions)
 *   - Fetching and preparing all necessary data (trades, tags, accounts, etc.)
 *   - Populating global stores and computed values for dashboard rendering
 *   - Ensuring the dashboard is ready for user interaction
 * 
 * The main entry point is `useMountDashboard`, which orchestrates the full
 * initialization sequence for the dashboard view.
 */
export async function useMountDashboard() {
    console.log("\MOUNTING DASHBOARD")
    await console.time("  --> Duration mount dashboard");
    spinnerLoadingPage.value = true
    dashboardChartsMounted.value = false
    dashboardIdMounted.value = false
    barChartNegativeTagGroups.value = []
    
    // Check if we need to force refresh due to deleted imports
    const forceRefresh = localStorage.getItem('force_dashboard_refresh') === 'true';
    const allImportsDeleted = localStorage.getItem('all_imports_deleted') === 'true';
    
    if (forceRefresh) {
        console.log("Forcing complete dashboard refresh due to data changes");
        localStorage.removeItem('force_dashboard_refresh');
        
        // Clear any cached data
        filteredTrades.length = 0;
        filteredTradesDaily.length = 0;
        filteredTradesTrades.length = 0;
        Object.keys(totals).forEach(key => delete totals[key]);
    }
    
    // If all imports were deleted, we'll need to create a default account structure
    if (allImportsDeleted) {
        console.log("All imports were deleted, resetting accounts");
        localStorage.removeItem('all_imports_deleted');
        
        // Clear account settings to force regeneration
        if (currentUser.value && currentUser.value.accounts) {
            currentUser.value.accounts.length = 0;
        }
        if (selectedAccounts.value) {
            selectedAccounts.value.length = 0;
        }
        localStorage.removeItem('selectedAccounts');
        
        // Reset hasData flag since there's no data
        hasData.value = false;
    }
    
    await useGetSelectedRange()
    await Promise.all([useGetExcursions(), useGetSatisfactions(), useGetTags(), useGetAvailableTags()])
    // Promise.all is used above to run multiple asynchronous data-fetching functions in parallel:
    // await Promise.all([useGetExcursions(), useGetSatisfactions(), useGetTags(), useGetAvailableTags()])
    // This means all four functions are started at the same time, and the code waits until all of them finish before continuing.
    // Here, we then fetch and filter trades after those parallel requests complete:
    await useGetFilteredTrades();
    
    // Extract accounts from trades if needed
    await extractAccountsFromTrades()
    
    await useTotalTrades()
    await useGroupTrades()
    await useCalculateProfitAnalysis()
    spinnerLoadingPage.value = false
    dashboardIdMounted.value = true
    useInitTab("dashboard")
    useInitTooltip()
    await availableTags.forEach(element => {
        let index = Object.keys(groups).indexOf(element.id);
        if (index != -1) {
            let temp = {}
            temp.id = element.id
            temp.name = element.name
            barChartNegativeTagGroups.value.push(temp)
        }
    });
    await console.timeEnd("  --> Duration mount dashboard");
    if (hasData.value) {
        console.log("\nBUILDING CHARTS")
        dashboardChartsMounted.value = true
        renderData.value += 1
        
        // Add a small delay to ensure DOM elements are ready before initializing charts
        await new Promise(resolve => {
            setTimeout(async () => {
                try {
                    await useECharts("init");
                } catch (err) {
                    console.error("Error initializing charts:", err);
                }
                resolve();
            }, 50); // 50ms delay gives the browser time to render the chart containers
        });
    } else {
        console.log("\nNO DATA AVAILABLE FOR CHARTS")
        // Ensure the UI shows "No Data" instead of blank charts
        dashboardChartsMounted.value = false;
    }
}

// Function to extract accounts from trades when accounts aren't available in user profile
async function extractAccountsFromTrades() {
    console.log("\nEXTRACTING ACCOUNTS FROM TRADES");
    try {
        // Check if we have any accounts in the user profile
        if (!currentUser.value) {
            console.log("No current user found, cannot extract accounts");
            return;
        }
        
        console.log(`Current user has accounts?: ${currentUser.value.hasOwnProperty('accounts')} (${currentUser.value.accounts ? currentUser.value.accounts.length : 'undefined'} accounts)`);
        
        if (currentUser.value && 
            (!currentUser.value.hasOwnProperty('accounts') || 
            !currentUser.value.accounts || 
            currentUser.value.accounts.length === 0)) {
            
            console.log("No accounts found in user profile, extracting from trades");
            const accountsFromTrades = new Set();
            
            // Log the filtered trades data structure 
            console.log(`Filtered trades array length: ${filteredTrades?.length || 0}`);
            console.log(`First filtered trade (if exists): ${JSON.stringify(filteredTrades?.[0] || 'none')}`);
            
            // Check if we have raw trades available from the trades.js module
            const rawTrades = await getRawTradesFromAPI();
            if (rawTrades && rawTrades.length > 0) {
                console.log(`Found ${rawTrades.length} trades in direct API call`);
                rawTrades.forEach(trade => {
                    if (trade && trade.account) {
                        console.log(`Found account: ${trade.account}`);
                        accountsFromTrades.add(trade.account);
                    }
                });
            }
            
            // Since filteredTradesTrades might be empty on first load, look for account info in both global collections
            if (filteredTrades && filteredTrades.length > 0) {
                console.log("Checking for accounts in filteredTrades...");
                // First try to extract from filteredTrades (array of day objects)
                filteredTrades.forEach(day => {
                    if (day && day.trades && Array.isArray(day.trades)) {
                        day.trades.forEach(trade => {
                            if (trade && trade.account) {
                                console.log(`Found account: ${trade.account}`);
                                accountsFromTrades.add(trade.account);
                            }
                        });
                    }
                });
            }
            
            // If we found accounts, set them
            if (accountsFromTrades.size > 0) {
                const accountsArray = Array.from(accountsFromTrades);
                console.log(`Found ${accountsArray.length} accounts in trades: ${accountsArray.join(', ')}`);
                
                // Create accounts object in current user
                if (!currentUser.value.accounts) {
                    currentUser.value.accounts = [];
                }
                
                // Add accounts to current user
                accountsArray.forEach(accountName => {
                    currentUser.value.accounts.push({
                        value: accountName,
                        label: accountName
                    });
                });
                
                // Set selected accounts if not already set
                if (!selectedAccounts.value || selectedAccounts.value.length === 0) {
                    selectedAccounts.value = accountsArray;
                    localStorage.setItem('selectedAccounts', accountsArray.join(','));
                    console.log("Set selectedAccounts to:", selectedAccounts.value);
                }
            } else {
                // If no accounts found in trades, create a placeholder account based on the current user
                let username = currentUser.value.email || currentUser.value.username || "Default";
                username = username.split('@')[0]; // Get the part before @ if it's an email
                
                const defaultAccount = username.toUpperCase() + '_ACCOUNT';
                console.log(`No accounts found in trades, creating default account: ${defaultAccount}`);
                
                // Add default account to currentUser
                if (!currentUser.value.accounts) {
                    currentUser.value.accounts = [];
                }
                
                currentUser.value.accounts.push({
                    value: defaultAccount,
                    label: defaultAccount
                });
                
                // Set selected account
                selectedAccounts.value = [defaultAccount];
                localStorage.setItem('selectedAccounts', defaultAccount);
                console.log("Set selectedAccounts to default:", selectedAccounts.value);
            }
        } else {
            console.log(`User already has accounts configured: ${JSON.stringify(currentUser.value.accounts)}`);
        }
    } catch (error) {
        console.error("Error extracting accounts from trades:", error);
        
        // Failsafe: If there's an error, ensure at least a default account exists
        if (currentUser.value && (!currentUser.value.accounts || currentUser.value.accounts.length === 0)) {
            const defaultAccount = "DEFAULT_ACCOUNT";
            
            // Add default account to currentUser
            currentUser.value.accounts = [{
                value: defaultAccount,
                label: defaultAccount
            }];
            
            // Set selected account
            selectedAccounts.value = [defaultAccount];
            localStorage.setItem('selectedAccounts', defaultAccount);
            console.log("Set selectedAccounts to fallback default:", selectedAccounts.value);
        }
    }
}

// Helper function to get trades directly from API
async function getRawTradesFromAPI() {
    try {
        const currentUser = AuthService.getCurrentUser();
        if (!currentUser) {
            return [];
        }
        
        // Add auth token to headers
        const headers = {
            'Authorization': `Bearer ${AuthService.token}`
        };
        
        const response = await axios.get('/api/trades', { 
            headers,
            params: {
                limit: 1000 // Get a reasonable number of trades
            }
        });
        
        if (response.data && Array.isArray(response.data)) {
            return response.data;
        }
        return [];
    } catch (error) {
        console.error("Error getting raw trades:", error);
        return [];
    }
}

export async function useMountDaily() {
    console.log("\nMOUNTING DAILY")
    console.time("  --> Duration mount daily");
    dailyPagination.value = 0
    dailyQueryLimit.value = 3
    endOfList.value = false
    spinnerLoadingPage.value = true

    // Mark that we're actively navigating to prevent auth loops
    sessionStorage.setItem('last_navigation', Date.now().toString());
    
    // Check authentication first
    if (!AuthService.isAuthenticated()) {
        console.error("User is not authenticated - redirecting to login");
        spinnerLoadingPage.value = false;
        window.location.replace("/");
        return;
    }
    
    try {
        await useGetSelectedRange();
        
        // Synchronize dates between selectedPeriodRange and selectedMonth
        // This ensures that calendar shows the same month as the daily view
        let shouldUpdateMonth = false;
        let targetMonth;
        
        if (selectedPeriodRange.value && selectedPeriodRange.value.end) {
            // Use the most recent date from the period range to determine the target month
            const currentPeriodEnd = dayjs.unix(selectedPeriodRange.value.end).tz(timeZoneTrade.value);
            targetMonth = currentPeriodEnd.startOf('month');
            
            // Check if selectedMonth matches this month
            const selectedMonthStart = dayjs.unix(selectedMonth.value.start).tz(timeZoneTrade.value).startOf('month');
            
            // If they don't match, update selectedMonth
            if (!selectedMonthStart.isSame(targetMonth, 'month')) {
                console.log(`Daily: Calendar month (${selectedMonthStart.format('MMMM YYYY')}) doesn't match period (${targetMonth.format('MMMM YYYY')})`);
                shouldUpdateMonth = true;
            }
        }
        
        // Update selectedMonth if needed
        if (shouldUpdateMonth && targetMonth) {
            selectedMonth.value = {
                start: targetMonth.unix(),
                end: targetMonth.endOf('month').unix()
            };
            
            console.log(`Daily: Synchronized calendar month to ${targetMonth.format('MMMM YYYY')}`);
            localStorage.setItem('selectedMonth', JSON.stringify(selectedMonth.value));
        }
        
        // Get data with Promise.all to parallelize requests
        await Promise.all([
            useGetExcursions().catch(e => console.error("Error getting excursions:", e)),
            useGetSatisfactions().catch(e => console.error("Error getting satisfactions:", e)),
            useGetTags().catch(e => console.error("Error getting tags:", e)),
            useGetAvailableTags().catch(e => console.error("Error getting available tags:", e)),
            useGetNotes().catch(e => console.error("Error getting notes:", e))
        ]);
        
        await useGetFilteredTrades().catch(e => console.error("Error getting filtered trades:", e));
        
        // Now load calendar since it depends on filtered trades
        await useLoadCalendar().catch(e => console.error("Error loading calendar:", e));
        
        // Added missing data processing steps
        await useTotalTrades();
        await useGroupTrades();
        await useCalculateProfitAnalysis();

        // Initialize page components before rendering charts
        await useInitTab("daily");
        
        // Set loading state to false to allow DOM to render
        spinnerLoadingPage.value = false;

        // Get diaries and screenshots data
        useGetDiaries(false).catch(e => console.error("Error getting diaries:", e));
        useGetScreenshots(true).catch(e => console.error("Error getting screenshots:", e));
        useInitPopover();
        
        await console.timeEnd("  --> Duration mount daily");
        dailyPageMounted.value = true;
    } catch (error) {
        console.error("Error in useMountDaily:", error);
        spinnerLoadingPage.value = false;
    }
}

export async function useMountCalendar(param) {
    const timestamp = Date.now();
    console.log("\nMOUNTING CALENDAR");
    console.time(`  --> Duration mount calendar ${timestamp}`);
    
    // Mark that we're actively navigating to prevent auth loops
    sessionStorage.setItem('last_navigation', Date.now().toString());
    
    // Check authentication first
    if (!AuthService.isAuthenticated()) {
        console.error("User is not authenticated - redirecting to login");
        spinnerLoadingPage.value = false;
        window.location.replace("/");
        return;
    }
    
    try {
        spinnerLoadingPage.value = true;
        
        // Initialize calendarData if it doesn't already exist
        if (!calendarData.value) {
            calendarData.value = {};
        }
        
        // Get date ranges
        await useGetSelectedRange();
        
        // If we're on the calendar page, ensure the selected range matches the month view
        if (pageId.value === "calendar" && selectedMonth.value) {
            console.log(`Calendar: Using month ${dayjs.unix(selectedMonth.value.start).format('MMMM YYYY')}`);
            
            // If we're also on the daily page, synchronize the period range
            if (selectedPeriodRange.value) {
                // Only update if different
                const periodStart = dayjs.unix(selectedPeriodRange.value.start).startOf('month');
                const monthStart = dayjs.unix(selectedMonth.value.start).startOf('month');
                
                if (!periodStart.isSame(monthStart, 'month')) {
                    console.log(`Calendar: Updating period range to match month: ${monthStart.format('MMMM YYYY')}`);
                    selectedPeriodRange.value.start = selectedMonth.value.start;
                    selectedPeriodRange.value.end = selectedMonth.value.end;
                    localStorage.setItem('selectedPeriodRange', JSON.stringify(selectedPeriodRange.value));
                }
            }
        }
        
        // Only fetch trades if they're not already loaded or we're explicitly refreshing
        if (filteredTrades.length === 0 || param === 'refresh') {
            console.log("Fetching trades for calendar");
            await useGetFilteredTrades().catch(e => console.error("Error getting filtered trades:", e));
        } else {
            console.log("Using existing filtered trades for calendar");
        }
        
        // Load the calendar with the trades
        await useLoadCalendar().catch(e => console.error("Error loading calendar:", e));
        
        // Ensure tooltips are initialized after calendar is loaded
        setTimeout(() => {
            useInitTooltip();
        }, 100);
        
        spinnerLoadingPage.value = false;
        console.timeEnd(`  --> Duration mount calendar ${timestamp}`);
    } catch (error) {
        console.error("Error in useMountCalendar:", error);
        spinnerLoadingPage.value = false;
    }
}

export async function useMountScreenshots() {
    console.log("\nMOUNTING SCREENSHOTS")
    await console.time("  --> Duration mount screenshots");
    
    // Mark that we're actively navigating to prevent auth loops
    sessionStorage.setItem('last_navigation', Date.now().toString());
    
    // Check authentication first
    if (!AuthService.isAuthenticated()) {
        console.error("User is not authenticated - redirecting to login");
        spinnerLoadingPage.value = false;
        window.location.replace("/");
        return;
    }
    
    try {
        spinnerLoadingPage.value = true;
        useGetScreenshotsPagination();
        await useGetSelectedRange();
        
        // Get data with Promise.all to parallelize requests
        await Promise.all([
            useGetTags().catch(e => console.error("Error getting tags:", e)),
            useGetAvailableTags().catch(e => console.error("Error getting available tags:", e))
        ]);
        
        await useGetScreenshots(false).catch(e => console.error("Error getting screenshots:", e));
        await console.timeEnd("  --> Duration mount screenshots");
        useInitPopover();
        
        spinnerLoadingPage.value = false;
    } catch (error) {
        console.error("Error in useMountScreenshots:", error);
        spinnerLoadingPage.value = false;
    }
}

export function useCheckVisibleScreen() {
    let visibleScreen = (window.innerHeight) // adding 200 so that loads before getting to bottom
    let documentHeight = document.documentElement.scrollHeight
    //console.log("visible screen " + visibleScreen)
    //console.log("documentHeight " + documentHeight)
    if (visibleScreen >= documentHeight) {
        useLoadMore()
    }
}

export async function useLoadMore() {
    console.log("  --> Loading more")
    spinnerLoadMore.value = true

    if (pageId.value == "daily") {
        await useGetFilteredTradesForDaily()
        await Promise.all([useRenderDoubleLineChart(), useRenderPieChart()])
        await useInitTab("daily")
        //await useGetDiaries(true)
        //await (renderingCharts.value = false)
    }

    if (pageId.value == "screenshots") {
        await useGetScreenshots(false)
    }

    if (pageId.value == "diary") {
        await useGetDiaries(true)
        await useGetSatisfactions()
    }

    spinnerLoadMore.value = false

}

export function useCheckIfWindowIsScrolled() {
    window.addEventListener('scroll', () => {
        windowIsScrolled.value = window.scrollY > 100;
    });
}

/**************************************
* MISC
**************************************/
export function usePageId() {
    const route = useRoute()
    pageId.value = route.name
    console.log("\n======== " + pageId.value.charAt(0).toUpperCase() + pageId.value.slice(1) + " Page/View ========\n")
    return pageId.value
}

export function useGetSelectedRange() {
    return new Promise(async (resolve, reject) => {
        if (pageId.value == "dashboard") {
            // Validate dashboard dates
            selectedDateRange.value = validateDateTimestamp(selectedDateRange.value);
            selectedRange.value = selectedDateRange.value;
        } else if (pageId.value == "calendar") {
            selectedRange.value = {};
            // Get start of current month for the calendar view
            selectedMonth.value = validateDateTimestamp(selectedMonth.value);
            
            // For calendar view, set the range to include the current month
            const currentMonthStart = dayjs().startOf('month').unix();
            const currentMonthEnd = dayjs().endOf('month').unix();
            
            // If selectedMonth is the current month, use it as is
            // Otherwise, include data from the beginning of the year through the end of the current month
            if (dayjs.unix(selectedMonth.value.start).isSame(dayjs().startOf('month'), 'month')) {
                selectedRange.value.start = selectedMonth.value.start;
            selectedRange.value.end = selectedMonth.value.end;
            } else {
                // Start from earlier of: beginning of year or selectedMonth start
                const yearStart = dayjs().startOf('year').unix();
                selectedRange.value.start = Math.min(yearStart, selectedMonth.value.start);
                
                // End at later of: end of current month or selectedMonth end
                selectedRange.value.end = Math.max(currentMonthEnd, selectedMonth.value.end);
            }
            
            console.log('Calendar range set to:', {
                start: dayjs.unix(selectedRange.value.start).format('YYYY-MM-DD'),
                end: dayjs.unix(selectedRange.value.end).format('YYYY-MM-DD')
            });
        }
        else {
            // Validate month dates
            selectedMonth.value = validateDateTimestamp(selectedMonth.value);
            selectedRange.value = selectedMonth.value;
        }
        
        // Ensure dates aren't identical (add 1 day if they are)
        if (selectedRange.value.start === selectedRange.value.end) {
            selectedRange.value.end = dayjs.unix(selectedRange.value.start).add(1, 'day').endOf('day').unix();
        }
        
        // Final validation to ensure no future dates
        selectedRange.value = validateDateTimestamp(selectedRange.value);
        
        // Update localStorage with validated values
        if (pageId.value == "dashboard") {
            localStorage.setItem('selectedDateRange', JSON.stringify(selectedRange.value));
        } else if (pageId.value != "calendar") {
            localStorage.setItem('selectedMonth', JSON.stringify(selectedRange.value));
        }
        
        resolve();
    });
}

export function useScreenType() {
    let screenWidth = (window.innerWidth > 0) ? window.innerWidth : screen.width
    screenType.value = (screenWidth >= 992) ? 'computer' : 'mobile'
}

export async function useSetValues() {
    return new Promise(async (resolve, reject) => {
        console.log(" -> Setting selected local storage")
        //console.log("Period Range "+JSON.stringify(periodRange))
        //console.log("now "+dayjs().tz(timeZoneTrade.value).startOf('month').unix())
        if (!localStorage.getItem('selectedDashTab')) localStorage.setItem('selectedDashTab', 'overviewTab')
        selectedDashTab.value = localStorage.getItem('selectedDashTab')

        if (Object.is(localStorage.getItem('selectedPositions'), null)) localStorage.setItem('selectedPositions', ["long", "short"])
        selectedPositions.value = localStorage.getItem('selectedPositions').split(",")

        if (!localStorage.getItem('selectedTimeFrame')) localStorage.setItem('selectedTimeFrame', "daily")
        selectedTimeFrame.value = localStorage.getItem('selectedTimeFrame')

        if (!localStorage.getItem('selectedRatio')) localStorage.setItem('selectedRatio', "appt")
        selectedRatio.value = localStorage.getItem('selectedRatio')

        if (!localStorage.getItem('selectedAccount')) localStorage.setItem('selectedAccount', "all")
        selectedAccount.value = localStorage.getItem('selectedAccount')

        if (!localStorage.getItem('selectedGrossNet')) localStorage.setItem('selectedGrossNet', "gross")
        selectedGrossNet.value = localStorage.getItem('selectedGrossNet')

        if (!localStorage.getItem('selectedPlSatisfaction')) localStorage.setItem('selectedPlSatisfaction', "pl")
        selectedPlSatisfaction.value = localStorage.getItem('selectedPlSatisfaction')

        if (!localStorage.getItem('selectedBroker')) localStorage.setItem('selectedBroker', "tradeZero")
        selectedBroker.value = localStorage.getItem('selectedBroker')

        if (!localStorage.getItem('selectedDateRange')) localStorage.setItem('selectedDateRange', JSON.stringify({ start: periodRange.filter(element => element.value == 'thisMonth')[0].start, end: periodRange.filter(element => element.value == 'thisMonth')[0].end }))
        selectedDateRange.value = JSON.parse(localStorage.getItem('selectedDateRange'))

        if (!localStorage.getItem('selectedPeriodRange')) {
            let tempFilter = periodRange.filter(element => element.start == selectedDateRange.value.start && element.end == selectedDateRange.value.end)
            //console.log("selectedDateRange.value "+JSON.stringify(selectedDateRange.value))
            //console.log("tempFilter  "+tempFilter)
            if (tempFilter.length > 0) {
                localStorage.setItem('selectedPeriodRange', JSON.stringify(tempFilter[0]))
            } else {
                console.log(" -> Custom range in vue")
                localStorage.setItem('selectedPeriodRange', JSON.stringify(periodRange.filter(element => element.start == -1)[0]))
            }
        }
        selectedPeriodRange.value = JSON.parse(localStorage.getItem('selectedPeriodRange'))

        if (!localStorage.getItem('selectedMonth')) {
            // Initialize with current month
            const thisMonth = { 
                start: periodRange.filter(element => element.value == 'thisMonth')[0].start, 
                end: periodRange.filter(element => element.value == 'thisMonth')[0].end 
            };
            localStorage.setItem('selectedMonth', JSON.stringify(thisMonth));
        }
        
        // Load and validate stored selectedMonth
        const storedMonth = JSON.parse(localStorage.getItem('selectedMonth'));
        selectedMonth.value = validateDateTimestamp(storedMonth);
        
        // Update localStorage if validation changed the value
        if (JSON.stringify(selectedMonth.value) !== JSON.stringify(storedMonth)) {
            localStorage.setItem('selectedMonth', JSON.stringify(selectedMonth.value));
        }

        if (Object.is(localStorage.getItem('selectedAccounts'), null) && currentUser.value && currentUser.value.hasOwnProperty("accounts") && currentUser.value.accounts.length > 0) {
            currentUser.value.accounts.forEach(element => {
                selectedAccounts.value.push(element.value)
            });
            //console.log("selected accounts " + JSON.stringify(selectedAccounts))
            localStorage.setItem('selectedAccounts', selectedAccounts.value)
            selectedAccounts.value = localStorage.getItem('selectedAccounts').split(",")
        }

        let selectedTagsNull = Object.is(localStorage.getItem('selectedTags'), null)
        console.log("selectedTagsNull " + selectedTagsNull)
        if (selectedTagsNull) {
            await useGetTags()
            if (selectedTagsNull) {
                console.log("selected tags is null ")
                selectedTags.value.push("t000t")

                tags.length = 0 // I'm already reseting in useGetPatterns but for some reason it would not be fast enough for this case
                localStorage.setItem('selectedTags', selectedTags.value)
                console.log("selectedTags " + JSON.stringify(selectedTags.value))
            }

        }


        amountCase.value = localStorage.getItem('selectedGrossNet')
        //console.log('amount case '+amountCase.value)
        resolve()
    })
}

export function useEditItem(param) {
    sessionStorage.setItem('editItemId', param);
    if (pageId.value == "daily" || pageId.value == "diary") {
        window.location.href = "/addDiary"
    }
    else if (pageId.value == "entries") {
        window.location.href = "/addEntry"
    }
    else if (pageId.value == "screenshots") {
        sessionStorage.setItem('screenshotsPagination', screenshotsPagination.value);
        sessionStorage.setItem('screenshotIdToEdit', param) //We use this to scroll to watched id on screenshots page. We erase it in scrollToScreenshot
        window.location.href = "/addScreenshot"
    }
    else if (pageId.value == "playbook") {
        window.location.href = "/addPlaybook"
    }
}

export function usePageRedirect(param) {
    if (param) {
        window.location.href = "/" + param
    }
    else if (pageId.value == "daily") {
        window.location.href = "/daily"
    }
    else if (pageId.value == "addDiary") {
        window.location.href = "/diary"
    }
    else if (pageId.value == "addPlaybook") {
        window.location.href = "/playbook"
    }
}

export function useToggleMobileMenu() {
    if (screenType.value === 'mobile') {
        let element = document.getElementById("sideMenu");
        element.classList.toggle("toggleSideMenu");
        sideMenuMobileOut.value = !sideMenuMobileOut.value
        console.log("sideMenuMobileOut " + sideMenuMobileOut.value)
    }
}

export function useCapitalizeFirstLetter(param) {
    return param.charAt(0).toUpperCase() + param.slice(1)
}

export function returnToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}


export const useGetLegacy = async () => {
    console.log(" -> Getting legacy information")
    legacy.length = 0
    return new Promise(async (resolve, reject) => {
        try {
            // Use the AuthService instead of Parse
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                resolve();
                return;
            }
            
            // Legacy data could be fetched from API if needed
            // For now, just resolve
            console.log("  --> Legacy functionality skipped")
            resolve();
            
        } catch (error) {
            console.error("Error getting legacy:", error);
            resolve(); // Just resolve to avoid blocking the app
        }
    })
}

export const useUpdateLegacy = async (param1) => {
    console.log("\n -> Updating legacy information")
    return new Promise(async (resolve, reject) => {
        try {
            // Use the AuthService instead of Parse
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                resolve();
                return;
            }
            
            // Legacy update would be implemented here if needed
            // For now, just log and resolve
            console.log("  --> Legacy update skipped for:", param1);
            resolve();
            
        } catch (error) {
            console.error("Error updating legacy:", error);
            resolve(); // Just resolve to avoid blocking the app
        }
    })
}

export const useGetLayoutStyle = async () => {
    console.log("\n -> Getting Layout Style")
    layoutStyle.length = 0
    return new Promise(async (resolve, reject) => {
        try {
            // Use the AuthService instead of Parse
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                resolve();
                return;
            }
            
            // Get layout style through API if needed
            // For now, just resolve
            resolve();
            
        } catch (error) {
            console.error("Error getting layout style:", error);
            resolve(); // Just resolve to avoid blocking the app
        }
    })
}

export const useExport = async (param1, param2, param3, param4) => {
    // Convert the JSON object to a string
    let blobData
    let exportName = param2 
    if (param3 != null){
        exportName = exportName + "_" + param3
    }
    
    let exportExt
    let csvSeparation = ";"

    if (param1 == "json") {
        const jsonData = JSON.stringify(param4, null, 2);

        // Create a blob from the JSON string
        blobData = new Blob([jsonData], { type: "application/json" });
        exportExt = ".json"

    }
    if (param1 == "csv") {
        // Extract the header row from the JSON object
        const headers = Object.keys(param4[0]);
        const csvRows = [headers.join(csvSeparation)];

        // Convert the JSON object to a CSV string
        param4.forEach(row => {
            const csvRow = headers.map(header => {
                return row[header];
            }).join(csvSeparation);
            csvRows.push(csvRow);
        });

        // Create a blob from the CSV string
        const csvString = csvRows.join("\n");
        blobData = new Blob([csvString], { type: "text/csv" });
        exportExt = ".csv"

    }

    // Create a link element to download the file
    const url = URL.createObjectURL(blobData);
    const a = document.createElement("a");
    a.href = url;
    a.download = exportName + "" + exportExt
    a.click();

    // Release the blob URL
    URL.revokeObjectURL(url);
}
/**************************************
* DATE FORMATS
**************************************/
export function useDateNumberFormat(param) {
    return Number(Math.trunc(param)) //we have to use /1000 and not unix because or else does not take into account tz
}

export function useDateCalFormat(param) {
    return dayjs.unix(param).tz(timeZoneTrade.value).format("YYYY-MM-DD")
}

export function useDateCalFormatMonth(param) {
    return dayjs.unix(param).tz(timeZoneTrade.value).format("YYYY-MM")
}

export function useTimeFormat(param) {
    return dayjs.unix(param).tz(timeZoneTrade.value).format("HH:mm:ss")
}

export function useTimeFormatFromDate(param) {
    return dayjs(param).tz(timeZoneTrade.value).format("HH:mm:ss")
}

export function useTimeDuration(param) {
    return dayjs.duration(param * 1000).format("HH:mm:ss")
}

export function useSwingDuration(param) {
    let duration = Number(dayjs.duration(param * 1000).format("D"))
    let period
    duration > 1 ? period = "days" : period = "day"
    return (duration + " " + period)
}

export function useHourMinuteFormat(param) {
    return dayjs.unix(param).tz(timeZoneTrade.value).format("HH:mm")
}

export function useDateTimeFormat(param) {
    return dayjs.unix(param).tz(timeZoneTrade.value).format("YYYY-MM-DD HH:mm:ss")
}

export function useChartFormat(param) {
    return dayjs.unix(param).tz(timeZoneTrade.value).format("l")
}

export function useMonthFormat(param) {
    return dayjs.unix(param).tz(timeZoneTrade.value).format("MMMM YYYY")
}

export function useMonthFormatShort(param) {
    return dayjs.unix(param).tz(timeZoneTrade.value).format("MMM YY")
}

// Yes, you can convert any valid date (as a Unix timestamp in seconds) to that format using this function.
// For example:
//   useCreatedDateFormat(1719878400)  // returns "Mon 01 July 2024" (if 1719878400 is July 1, 2024)
// The function expects the input to be a Unix timestamp (number of seconds since Jan 1, 1970).
// If you have a JavaScript Date object or an ISO string, you need to convert it to a Unix timestamp (in seconds) first:
//   const date = new Date("2024-07-01T00:00:00Z");
//   const unixSeconds = Math.floor(date.getTime() / 1000);
//   useCreatedDateFormat(unixSeconds);

// If you pass an invalid date or a timestamp in milliseconds (instead of seconds), the output may be incorrect.
// Always ensure the input is a Unix timestamp in seconds.

export function useCreatedDateFormat(param) {
    return dayjs.unix(param).tz(timeZoneTrade.value).format("ddd DD MMMM YYYY")
}

// this is the input format for the backend 2025-06-18T03:42:31.796+00:00
export function formatDate(isoTimestamp) {
    return new Date(isoTimestamp).toISOString().slice(0, 10);
}

export function useDatetimeLocalFormat(param) {
    return dayjs.tz(param * 1000, timeZoneTrade.value).format("YYYY-MM-DDTHH:mm:ss") //here we ne
}

export function useStartOfDay(param) {
    return dayjs(param * 1000).tz(timeZoneTrade.value).startOf("day").unix()
}
/**************************************
* NUMBER FORMATS
**************************************/
export function useThousandCurrencyFormat(param) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0, style: 'currency', currency: 'USD' }).format(param)
}

export function useThousandFormat(param) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(param)
}

export function useTwoDecCurrencyFormat(param) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2, style: 'currency', currency: 'USD' }).format(param)
}

export function useThreeDecCurrencyFormat(param) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 3, style: 'currency', currency: 'USD' }).format(param)
}

export function useXDecCurrencyFormat(param, param2) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: param2, style: 'currency', currency: 'USD' }).format(param)
}

export function useTwoDecFormat(param) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(param)
}

export function useXDecFormat(param, param2) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: param2 }).format(param)
}

export function useOneDecPercentFormat(param) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 1, style: 'percent' }).format(param)
}

export function useTwoDecPercentFormat(param) {
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2, style: 'percent' }).format(param)
}

export function useFormatBytes(param, decimals = 2) {
    if (param === 0) return '0 bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['param', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(param) / Math.log(k));
    return parseFloat((param / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export function useDecimalsArithmetic(param1, param2) {
    //https://flaviocopes.com/javascript-decimal-arithmetics/
    // Convert strings to numbers if needed
    const num1 = typeof param1 === 'string' ? parseFloat(param1) : param1;
    const num2 = typeof param2 === 'string' ? parseFloat(param2) : param2;
    
    // Handle null/undefined inputs
    const a = num1 || 0;
    const b = num2 || 0;
    
    // For debugging
    console.log(`useDecimalsArithmetic: ${a} + ${b}`);
    
    // Multiply by 100000000 to handle up to 8 decimal places reliably
    // Then add as integers and convert back
    return Math.round((a * 100000000) + (b * 100000000)) / 100000000;
}


/**************************************
* CLOUD
**************************************/

export const useCheckCloudPayment = (param1) => {
    return new Promise(async (resolve, reject) => {
        try {
            let currentUser = param1
            // Make the API call
            const response = await axios.post('/api/checkCloudPayment', {
                currentUser: currentUser,
            });

            //console.log('Response:', JSON.stringify(response));

            // Resolve or reject based on response
            if (response.status === 200) {
                resolve(response.data); // Resolve with response data
            } else {
                reject(new Error(' -> Payment check failed. Redirecting to payment page.'));
            }
        } catch (error) {
            console.error(' -> Error during validation:', error);
            reject(error); // Reject with the caught error
        }
    });
};

export const useGetStripePk = () => {
    return new Promise(async (resolve, reject) => {
        try {
            const response = await axios.get('/api/getStripePk', {
            });

            //console.log('Response:', JSON.stringify(response));

            // Resolve or reject based on response
            if (response.status === 200) {
                resolve(response.data); // Resolve with response data
            } else {
                reject(new Error(' -> Failed to get Stripe pk.'));
            }
        } catch (error) {
            console.error(' -> Error getting Stripe pk:', error);
            reject(error); // Reject with the caught error
        }
    });
};

/**
 * Validates timestamps to ensure they're not in the future
 * @param {Object} dateObj - Object with start and end timestamps
 * @returns {Object} - Validated date object
 */
export function validateDateTimestamp(dates) {
    // Safety check for null/undefined input
    if (!dates) {
        console.warn("validateDateTimestamp: Received null/undefined dates object");
        const now = dayjs().unix();
        return {
            start: dayjs().startOf('month').unix(),
            end: now
        };
    }
    
    const now = dayjs().unix();
    let { start, end } = dates;

    // Add debugging log
    console.log(`validateDateTimestamp - Original dates: start=${start} (${dayjs.unix(start).format('YYYY-MM-DD')}), end=${end} (${dayjs.unix(end).format('YYYY-MM-DD')})`);
    
    // Check if start is valid
    if (typeof start !== 'number' || isNaN(start) || start <= 0) {
        console.warn(`Invalid start timestamp ${start}, resetting to start of month`);
        start = dayjs().startOf('month').unix();
    }
    
    // Check if end is valid
    if (typeof end !== 'number' || isNaN(end) || end <= 0) {
        console.warn(`Invalid end timestamp ${end}, resetting to now`);
        end = now;
    }
    
    // Check if end is in the future
    if (end > now) {
        console.warn(`Invalid future timestamp detected in validateDateTimestamp, resetting end to current time`);
        end = now;
    }
    
    // Ensure start is before end
    if (start > end) {
        console.warn(`Start date ${start} is after end date ${end}, swapping values`);
        [start, end] = [end, start];
    }
    
    console.log(`validateDateTimestamp - Validated dates: start=${start} (${dayjs.unix(start).format('YYYY-MM-DD')}), end=${end} (${dayjs.unix(end).format('YYYY-MM-DD')})`);
    
    return { start, end };
}

/**
 * Helper function to validate API parameters and ensure dates are valid
 * @param {Object} params - The API parameters object
 * @returns {Object} - Validated parameters object
 */
export async function validateApiParams(params) {
  // Create a copy to avoid modifying the original
  const validParams = { ...params };
  
  // Validate dates if present
  if (validParams.startDate !== undefined) {
    const validatedDates = validateDateTimestamp({ 
      start: validParams.startDate, 
      end: validParams.endDate || (validParams.startDate + 86400) 
    });
    
    validParams.startDate = validatedDates.start;
    if (validParams.endDate !== undefined) {
      validParams.endDate = validatedDates.end;
    }
    
    console.log(`API request using validated date range: ${dayjs.unix(validatedDates.start).format('YYYY-MM-DD')} to ${dayjs.unix(validatedDates.end).format('YYYY-MM-DD')}`);
  }
  
  // Validate dates in dateUnix format if present
  if (validParams.dateUnix !== undefined && validParams.dateUnix > Math.floor(Date.now()/1000 + 86400)) {
    console.warn("Future dateUnix detected, resetting to current time");
    validParams.dateUnix = Math.floor(Date.now()/1000);
  }
  
  return validParams;
}

export function useGetTimeZoneOnLoad() {
    // This function is meant to be called after the app is mounted and user data is loaded
    console.log("Refreshing timezone settings");
    if (!currentUser.value) {
        console.warn("No current user when refreshing timezone");
        return;
    }
    
    // Call the main timezone function
    useGetTimeZone();
    
    // Force re-rendering if needed (will trigger computed properties)
    renderData.value += 1;
}

// Add stub for checkParseAppId function that was removed
export function checkParseAppId() {
  console.log("Parse App ID check stub - Parse is no longer used");
  return true;
}

