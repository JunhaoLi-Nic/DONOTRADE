<script setup>
import { onMounted, ref, computed, onBeforeUnmount } from 'vue';
import { useCheckCloudPayment, useGetCurrentUser, useToggleMobileMenu, useGetTimeZoneOnLoad } from '../utils/utils.js'
import { useInitShepherd, useInitTooltip } from "../utils/utils.js";
import { pageId, currentUser, renderProfile, screenType, latestVersion, deviceTimeZone, timeZoneTrade, renderData } from "../stores/globals"
import { version } from '../../package.json';
import dayjs from 'dayjs';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';

// Extend dayjs with timezone and utc plugins
dayjs.extend(utc);
dayjs.extend(timezone);

// Create reactive references for the time
const localTime = ref('');
const selectedTime = ref('');

// Timer reference for cleanup
let timeInterval = null;

// Add dropdown state
const showAddDropdown = ref(false);
const showProfileDropdown = ref(false);

// Function to toggle dropdown visibility
function toggleAddDropdown() {
  showAddDropdown.value = !showAddDropdown.value;
  if (showAddDropdown.value) {
    // Close other dropdown
    showProfileDropdown.value = false;
  }
}

function toggleProfileDropdown() {
  showProfileDropdown.value = !showProfileDropdown.value;
  if (showProfileDropdown.value) {
    // Close other dropdown
    showAddDropdown.value = false;
  }
}

// Function to close dropdowns when clicking outside
function closeDropdowns(event) {
  // Check if click is outside of the dropdown areas
  const addDropdown = document.getElementById('add-dropdown');
  const profileDropdown = document.getElementById('profile-dropdown');
  const addButton = document.getElementById('add-button');
  const profileButton = document.getElementById('profile-button');
  
  if (addDropdown && !addDropdown.contains(event.target) && !addButton.contains(event.target)) {
    showAddDropdown.value = false;
  }
  
  if (profileDropdown && !profileDropdown.contains(event.target) && !profileButton.contains(event.target)) {
    showProfileDropdown.value = false;
  }
}

// Update the time every second
const updateTime = () => {
  if (!deviceTimeZone.value || !timeZoneTrade.value) return;
  
  localTime.value = dayjs().tz(deviceTimeZone.value).format('HH:mm:ss');
  selectedTime.value = dayjs().tz(timeZoneTrade.value).format('HH:mm:ss');
};

// Computed property for timezone labels
const timezoneLabel = computed(() => {
  return timeZoneTrade.value ? timeZoneTrade.value.split('/').pop().replace('_', ' ') : '';
});

const localTimezoneLabel = computed(() => {
  return deviceTimeZone.value ? deviceTimeZone.value.split('/').pop().replace('_', ' ') : '';
});

// Check if we should show both timezones
const showBothTimezones = computed(() => {
  // Return true if they're different timezones (considering the full timezone path)
  return deviceTimeZone.value && timeZoneTrade.value && deviceTimeZone.value !== timeZoneTrade.value;
});

/* MODULES */
import axios from 'axios'
import { AuthService } from '../services/auth.js'

const pages = [{
    id: "registerSignup",
    name: "Login",
    icon: "uil uil-apps"
},
{
    id: "dashboard",
    name: "Dashboard",
    icon: "uil uil-apps"
},
{
    id: "daily",
    name: "Daily",
    icon: "uil uil-signal-alt-3"
},
{
    id: "calendar",
    name: "Calendar",
    icon: "uil uil-calendar-alt"
},
{
    id: "screenshots",
    name: "Screenshots",
    icon: "uil uil-image-v"
},
{
    id: "videos",
    name: "Videos",
    icon: "uil uil-clapper-board"
},
{
    id: "diary",
    name: "Diary",
    icon: "uil uil-diary"
},
{
    id: "notes",
    name: "Notes",
    icon: "uil uil-diary"
},
{
    id: "playbook",
    name: "Playbook",
    icon: "uil uil-compass"
},
{
    id: "addPlaybook",
    name: "Add Playbook",
    icon: "uil uil-compass"
},
{
    id: "addTrades",
    name: "Add Trades",
    icon: "uil uil-plus-circle"
},
{
    id: "addEntry",
    name: "Add Entry",
    icon: "uil uil-signin"
},
{
    id: "addDiary",
    name: "Add Diary",
    icon: "uil uil-plus-circle"
},
{
    id: "settings",
    name: "Settings",
    icon: "uil uil-sliders-v-alt"
},
{
    id: "addScreenshot",
    name: "Add Screenshot",
    icon: "uil uil-image-v"
},
{
    id: "addExcursions",
    name: "Add Excursions",
    icon: "uil uil-refresh"
},
{
    id: "entries",
    name: "Entries",
    icon: "uil uil-signin"
},
{
    id: "forecast",
    name: "Forecast",
    icon: "uil uil-cloud-sun"
},
{
    id: "imports",
    name: "Imports",
    icon: "uil uil-import"
},
{
    id: "checkout",
    name: "Checkout",
    icon: "uil uil-shopping-cart"
},
{
    id: "checkoutSuccess",
    name: "Checkout Success",
    icon: "uil uil-shopping-cart"
},
{
    id: "riskmanagement",
    name: "Risk Management",
    icon: "uil uil-chart-line"
},
{
    id: "catalysts",
    name: "Market Catalysts",
    icon: "uil uil-chart-growth"
}
]
//console.log(" user "+useCheckCurrentUser())
onMounted(async () => {
    await getDockerVersion()
    await useInitTooltip()
    
    // Make sure user data is loaded
    await useGetCurrentUser();
    
    // Refresh timezone settings based on user preferences
    useGetTimeZoneOnLoad();
    
    // Initialize time display
    updateTime();
    
    // Set up interval to update time every second
    timeInterval = setInterval(updateTime, 1000);
    
    // Add global click listener to close dropdowns
    document.addEventListener('click', closeDropdowns);
})

// Use proper Vue lifecycle hook for cleanup
onBeforeUnmount(() => {
  if (timeInterval) {
    clearInterval(timeInterval);
    timeInterval = null;
  }
  // Remove click listener
  document.removeEventListener('click', closeDropdowns);
});

function logout() {
    // Use async/await for better readability
    (async () => {
        try {
            // Use AuthService directly
            await AuthService.logout();
            console.log("Logging out");
            window.location.replace("/");
        } catch (error) {
            console.error("Error during logout:", error);
            // Fallback: manually clear storage and redirect
            localStorage.clear();
            window.location.replace("/");
        }
    })();
}

function getDockerVersion() {
    return new Promise(async (resolve, reject) => {
        try {
            // Get version from Docker endpoint
            const dockerResponse = await axios.get("/api/dockerVersion");
            if (dockerResponse.data && dockerResponse.data.version) {
                latestVersion.value.docker = dockerResponse.data.version;
            }
            
            resolve();
        } catch (error) {
            console.error("Error fetching Docker version:", error);
            resolve(); // Resolve anyway to not block the UI
        }
    });
}

const navAdd = async (param) => {
    await useGetCurrentUser();
    try {
        await useCheckCloudPayment(currentUser.value);
        // Redirect only if no error occurs
        window.location.href = "/" + param;
    } catch (error) {
        //console.log("-> useCheckCloudPayment error: " + error);
        // Redirect to checkout page on error
        window.location.href = "/checkout";
    }
};


</script>

<template>
    <div class="navbar">
        <div class="col-4">
            <span v-if="screenType == 'mobile'">
                <a v-on:click="useToggleMobileMenu">
                    <i v-bind:class="pages.filter(item => item.id == pageId)[0]?.icon || 'uil uil-apps'" class="me-1"></i>{{
                        pages.filter(item => item.id == pageId)[0]?.name || pageId }}</a>
            </span>
            <span v-else>
                <i v-bind:class="pages.filter(item => item.id == pageId)[0]?.icon || 'uil uil-apps'" class="me-1"></i>{{
                    pages.filter(item => item.id == pageId)[0]?.name || pageId }}</span>
        </div>
        <div class="col-8 d-flex justify-content-end align-items-center">
            <!-- Time display section -->
            <div class="time-display me-3">
                <span class="time-wrapper">
                    <i class="uil uil-clock me-1"></i>
                    <span class="time-block">
                        <span class="time">{{ localTime }}</span>
                        <span class="timezone">{{ localTimezoneLabel }}</span>
                    </span>
                    <span v-if="showBothTimezones" class="time-separator">|</span>
                    <span v-if="showBothTimezones" class="time-block">
                        <span class="time">{{ selectedTime }}</span>
                        <span class="timezone">{{ timezoneLabel }}</span>
                    </span>
                </span>
            </div>
            
            <!-- Custom Add Dropdown -->
            <div id="step11" class="me-3 custom-dropdown">
                <button id="add-button" class="btn blueBtn btn-sm" @click.stop="toggleAddDropdown">
                    <i class="uil uil-plus me-2"></i>Add
                </button>
                <div id="add-dropdown" class="custom-dropdown-menu" :class="{'show': showAddDropdown}">
                    <div class="dropdown-item" @click="$router.push('/addTrades')">Trades</div>
                    <div class="dropdown-item" @click="$router.push('/addDiary')">Diary Entry</div>
                    <div class="dropdown-item" @click="$router.push('/addScreenshot')">Screenshot</div>
                    <div class="dropdown-item" @click="$router.push('/addPlaybook')">Playbook</div>
                    <div class="dropdown-item" @click="$router.push('/addExcursions')">Excursions</div>
                </div>
            </div>
            
            <!-- Custom Profile Dropdown -->
            <div id="step12" v-bind:key="renderProfile" class="custom-dropdown">
                <div id="profile-button" class="profile-button" @click.stop="toggleProfileDropdown">
                    <span v-if="currentUser.hasOwnProperty('avatar')">
                        <img class="profileImg" v-bind:src="currentUser.avatar.url" />
                    </span>
                    <span v-else>
                        <img class="profileImg" src="../assets/astronaut.png" />
                    </span>
                </div>
                
                <div id="profile-dropdown" class="custom-dropdown-menu profile-menu" :class="{'show': showProfileDropdown}">
                    <div class="dropdown-item" @click="$router.push('/settings')">
                        <i class="uil uil-sliders-v-alt me-2"></i>Settings
                    </div>
                    <div class="dropdown-item" @click="$router.push('/imports')">
                        <i class="uil uil-import me-2"></i>Imports
                    </div>
                    <div class="dropdown-item" @click="useInitShepherd()">
                        <i class="uil uil-question-circle me-2"></i>Tutorial
                    </div>
                    <div class="dropdown-item" @click="logout()">
                        <i class="uil uil-signout me-2"></i>Logout
                    </div>
                    <div class="dropdown-divider"></div>
                    <div class="text-center">
                        <span class="txt-small">v{{ version }}</span>
                        <div>
                            <span class="txt-x-small">DockerHub: v{{ latestVersion.docker }}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.navbar {
    background-color: #2a2a4a; 
    padding: 10px 40px; 
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
    color: #e0e0e0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 1.1rem; 
    height: 80px;
    position: relative;
    z-index: 1000; 
}

/* Custom dropdown implementation */
.custom-dropdown {
    position: relative;
    display: inline-block;
}

.profile-button {
    cursor: pointer;
}

.custom-dropdown-menu {
    position: absolute;
    right: 0;
    top: 100%;
    margin-top: 10px;
    background-color: #2a2a4a;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    width: 200px;
    display: none;
    z-index: 10000;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
    overflow: hidden;
}

.custom-dropdown-menu.show {
    display: block;
}

.profile-menu {
    width: 220px;
}

.dropdown-item {
    padding: 12px 16px;
    cursor: pointer;
    color: #e0e0e0;
    transition: background-color 0.2s;
}

.dropdown-item:hover {
    background-color: #3a3a5a;
    color: #fff;
}

.dropdown-divider {
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    margin: 8px 0;
}

.text-center {
    padding: 10px 15px;
    text-align: center;
}

/* Rest of your existing styles */
.navbar .col-4 {
    display: flex;
    align-items: center;
}

.navbar .col-4 a {
    color: #e0e0e0;
    text-decoration: none;
    font-weight: 500;
    display: flex;
    align-items: center;
    font-size: 1.2rem;
}

.navbar .col-4 a i {
    font-size: 1.4rem;
    margin-right: 10px;
}

.time-display {
    font-size: 1rem;
    display: flex;
    align-items: center;
}

.time-wrapper {
    display: inline-flex;
    align-items: center;
    background-color: rgba(255, 255, 255, 0.1);
    padding: 8px 14px;
    border-radius: 22px;
    color: #fff;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.3);
}

.time-wrapper i {
    font-size: 1.2rem;
    margin-right: 6px;
    color: #6a8dff;
}

.time-block {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    margin: 0 6px;
}

.time {
    font-weight: 600;
    line-height: 1.2;
    font-size: 1.1rem;
}

.timezone {
    font-size: 0.7rem;
    opacity: 0.7;
    line-height: 1;
    text-transform: uppercase;
}

.time-separator {
    margin: 0 10px;
    opacity: 0.4;
    color: #fff;
    font-size: 1.1rem;
}

.blueBtn {
    background-color: #6a8dff;
    border-color: #6a8dff;
    color: #fff;
    font-weight: 600;
    padding: 9px 18px;
    border-radius: 8px;
    font-size: 1rem;
    transition: background-color 0.3s ease, transform 0.2s ease;
}

.blueBtn:hover {
    background-color: #5a7ce0;
    transform: translateY(-1px);
}

.profileImg {
    width: 46px;
    height: 46px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid #6a8dff;
    cursor: pointer;
    transition: border-color 0.3s ease;
}

.profileImg:hover {
    border-color: #5a7ce0;
}

.txt-small {
    font-size: 0.8rem;
    color: #a0a0a0;
}

.txt-x-small {
    font-size: 0.7rem;
    color: #808080;
}
</style>