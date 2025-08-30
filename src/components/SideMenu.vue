<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { pageId, screenType } from "../stores/globals"
import { useToggleMobileMenu } from "../utils/utils";

const router = useRouter();

const isCollapsed = ref(false);

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value;
  
  // Add a small delay to allow Vue to update the DOM before resizing content
  setTimeout(() => {
    // Dispatch a custom event that the main layout can listen for
    window.dispatchEvent(new CustomEvent('sidebar-toggle', { 
      detail: { collapsed: isCollapsed.value } 
    }));
  }, 10);
};
</script>

<template>
    <div :class="['sidebar-container', { 'collapsed': isCollapsed }]">
        <div class="logo-container">
            <!-- Logo only shown when expanded -->
            <div v-if="!isCollapsed" class="logo-wrapper">
                <img src="../assets/sun_full_blue.png" class="logo" />
            </div>
            
            <!-- Text only shown when expanded -->
            <div v-if="!isCollapsed" class="logo-text-wrapper">
                <span class="logo-text">TradeNote</span>
            </div>
            
            <!-- Hamburger button (always visible) -->
            <button class="hamburger-btn" @click="toggleSidebar">
                <i :class="isCollapsed ? 'uil uil-bars' : 'uil uil-times'"></i>
            </button>
        </div>
        
        <div id="step2" :class="{ 'hidden': isCollapsed }" class="sidebar-content">
            <div class="sideMenuDiv">
                <div class="sideMenuDivContent">
                    <label class="fw-lighter">ANALYZE</label>
                    <a id="step3" v-bind:class="[pageId === 'dashboard' ? 'activeNavCss' : '', 'nav-link', 'mb-2']"
                        href="/dashboard">
                        <i class="uil uil-apps me-2"></i>Dashboard</a>
                    <a id="step4" v-bind:class="[pageId === 'daily' ? 'activeNavCss' : '', 'nav-link', 'mb-2']" href="/daily">
                        <i class="uil uil-signal-alt-3 me-2"></i>Daily
                    </a>
                    <a id="step5" v-bind:class="[pageId === 'calendar' ? 'activeNavCss' : '', 'nav-link', 'mb-2']"
                        href="/calendar">
                        <i class="uil uil-calendar-alt me-2"></i>Calendar</a>

                    <a v-bind:class="[pageId === 'catalysts' ? 'activeNavCss' : '', 'nav-link', 'mb-2']"
                        href="/catalysts">
                        <i class="uil uil-chart-growth me-2"></i>Market Catalysts</a>
                    <a v-bind:class="[pageId === 'analysis' ? 'activeNavCss' : '', 'nav-link', 'mb-2']"
                        href="/analysis">
                        <i class="uil uil-chart-pie me-2"></i>Analysis</a>
                    <a v-bind:class="[pageId === 'market-watchlist' ? 'activeNavCss' : '', 'nav-link', 'mb-2']"
                        href="/market-watchlist">
                        <i class="uil uil-eye me-2"></i>Market Watchlist</a>
                </div>
            </div>

            <div class="sideMenuDiv">
                <div class="sideMenuDivContent">
                    <label class="fw-lighter mt-3">REFLECT</label>
                    <a id="step6" v-bind:class="[pageId === 'diary' ? 'activeNavCss' : '', 'nav-link', 'mb-2']" href="/diary">
                        <i class="uil uil-diary me-2"></i>Diary
                    </a>
                    <a id="step7" v-bind:class="[pageId === 'screenshots' ? 'activeNavCss' : '', 'nav-link', 'mb-2']"
                        href="/screenshots">
                        <i class="uil uil-image-v me-2"></i>Screenshots
                    </a>
                    <a id="step8" v-bind:class="[pageId === 'playbook' ? 'activeNavCss' : '', 'nav-link', 'mb-2']"
                        href="/playbook">
                        <i class="uil uil-compass me-2"></i>Playbook
                    </a>
                </div>
            </div>
            
            <div class="sideMenuDiv">
                <div class="sideMenuDivContent">
                    <label class="fw-lighter mt-3">RISK</label>
                    <a v-bind:class="[pageId === 'riskmanagement' ? 'activeNavCss' : '', 'nav-link', 'mb-2']"
                        href="/riskmanagement">
                        <i class="uil uil-chart-line me-2"></i>Risk Management</a>
                </div>
            </div>

            <div class="sideMenuDiv">
                <div class="sideMenuDivContent">
                    <label class="fw-lighter mt-3">Backtest</label>
                    <a v-bind:class="[pageId === 'strategy-backtest' ? 'activeNavCss' : '', 'nav-link', 'mb-2']"
                        href="/strategy-backtest">
                        <i class="uil uil-chart-line me-2"></i>Strategy Backtest</a>
                </div>
            </div>
        </div>
        
        <!-- Mini sidebar when collapsed -->
        <div v-if="isCollapsed" class="mini-sidebar">
            <div class="mini-item" title="Dashboard" @click="() => router.push('/dashboard')">
                <i class="uil uil-apps"></i>
            </div>
            <div class="mini-item" title="Daily" @click="() => router.push('/daily')">
                <i class="uil uil-signal-alt-3"></i>
            </div>
            <div class="mini-item" title="Calendar" @click="() => router.push('/calendar')">
                <i class="uil uil-calendar-alt"></i>
            </div>
            <div class="mini-item" title="Market Catalysts" @click="() => router.push('/catalysts')">
                <i class="uil uil-chart-growth"></i>
            </div>
            <div class="mini-item" title="Analysis" @click="() => router.push('/analysis')">
                <i class="uil uil-chart-pie"></i>
            </div>
            <div class="mini-item" title="Market Watchlist" @click="() => router.push('/market-watchlist')">
                <i class="uil uil-eye"></i>
            </div>
            <div class="mini-item" title="Diary" @click="() => router.push('/diary')">
                <i class="uil uil-diary"></i>
            </div>
            <div class="mini-item" title="Screenshots" @click="() => router.push('/screenshots')">
                <i class="uil uil-image-v"></i>
            </div>
            <div class="mini-item" title="Playbook" @click="() => router.push('/playbook')">
                <i class="uil uil-compass"></i>
            </div>
            <div class="mini-item" title="Risk Management" @click="() => router.push('/riskmanagement')">
                <i class="uil uil-chart-line"></i>
            </div>
        </div>
    </div>
</template>

<style scoped>
.sidebar-container {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    transition: all 0.3s ease;
    width: 250px;
    background-color: #1a1a2e; /* Darker, modern background */
    color: #e0e0e0; /* Lighter text for contrast */
    z-index: 1000;
    box-shadow: 2px 0 5px rgba(0, 0, 0, 0.2); /* Subtle shadow for depth */
    display: flex;
    flex-direction: column;
    overflow: hidden; /* Hide overflow initially */
}

.sidebar-container.collapsed {
    width: 60px;
}

.logo-container {
    position: relative;
    height: 60px;
    display: flex;
    align-items: center;
    padding: 0 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1); /* Separator */
}

.logo-wrapper {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 30px;
}

.logo {
    width: 100%;
    height: auto;
    max-height: 30px;
}

.logo-text-wrapper {
    flex: 1;
    overflow: hidden;
    padding-left: 10px;
}

.logo-text {
    font-size: 1.2rem; /* Slightly larger */
    font-weight: 700; /* Bolder */
    white-space: nowrap;
    color: #fff; /* White for prominence */
}

.sidebar-content {
    flex: 1;
    overflow-y: auto; /* Make content scrollable */
    padding-bottom: 20px; /* Add some bottom padding */
    scrollbar-width: thin; /* Firefox */
    scrollbar-color: #3a3a5a #1a1a2e; /* Firefox */
}

/* Custom scrollbar for webkit browsers */
.sidebar-content::-webkit-scrollbar {
    width: 4px;
}

.sidebar-content::-webkit-scrollbar-track {
    background: #1a1a2e;
}

.sidebar-content::-webkit-scrollbar-thumb {
    background-color: #3a3a5a;
    border-radius: 6px;
}

.hamburger-btn {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    background: transparent;
    border: none;
    color: #6a8dff; /* A modern blue */
    font-size: 1.5rem; /* Larger icon */
    cursor: pointer;
    padding: 5px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    width: 35px; /* Slightly larger button */
    height: 35px;
    z-index: 2;
    transition: background-color 0.3s ease;
}

.hamburger-btn:hover {
    background-color: rgba(106, 141, 255, 0.2); /* Subtle hover effect */
}

.hidden {
    display: none;
}

.sideMenuDiv {
    padding: 10px 0;
}

.sideMenuDivContent {
    padding: 0 15px;
}

.sideMenuDivContent label {
    color: #a0a0a0; /* Muted color for labels */
    font-size: 0.85rem;
    margin-bottom: 10px;
    display: block;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.nav-link {
    display: flex;
    align-items: center;
    padding: 10px 15px;
    color: #e0e0e0;
    text-decoration: none;
    border-radius: 8px; /* Slightly rounded corners */
    margin-bottom: 5px;
    transition: background-color 0.3s ease, color 0.3s ease;
}

.nav-link i {
    font-size: 1.1rem;
    margin-right: 10px;
}

.nav-link:hover {
    background-color: #2a2a4a; /* Darker hover background */
    color: #fff;
}

.nav-link.activeNavCss {
    background-color: #607ee3; /* Active state with modern blue */
    color: #fff !important; /* Force text to be white */
    font-weight: 600;
    box-shadow: 0 2px 5px rgba(106, 141, 255, 0.3); /* Subtle shadow for active item */
}

.nav-link.activeNavCss i {
    color: #fff !important; /* Force icon to be white */
}

.mini-sidebar {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 20px;
    padding-bottom: 20px;
    flex-grow: 1; /* Allow it to take available space */
    overflow-y: auto; /* Enable scrolling if many items */
    scrollbar-width: thin; /* Firefox */
    scrollbar-color: #3a3a5a #1a1a2e; /* Firefox */
}

/* Custom scrollbar for webkit browsers */
.mini-sidebar::-webkit-scrollbar {
    width: 4px;
}

.mini-sidebar::-webkit-scrollbar-track {
    background: #1a1a2e;
}

.mini-sidebar::-webkit-scrollbar-thumb {
    background-color: #3a3a5a;
    border-radius: 6px;
}

.mini-item {
    width: 45px; /* Slightly larger for better touch target */
    height: 45px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 10px;
    border-radius: 10px; /* More rounded than 50% for a modern look */
    cursor: pointer;
    font-size: 1.3rem; /* Larger icon */
    color: #a0a0a0; /* Muted color */
    transition: background-color 0.3s ease, color 0.3s ease;
}

.mini-item:hover {
    background-color: #2a2a4a;
    color: #6a8dff;
}

/* Add these for proper content area adjustment */
:deep(body) {
    margin-left: var(--sidebar-width, 250px);
    transition: margin-left 0.3s ease;
}

:deep(body.sidebar-collapsed) {
    --sidebar-width: 60px;
}

/* Update logo container height for collapsed state */
.sidebar-container.collapsed .logo-container {
    height: 60px; /* Keep consistent height */
    justify-content: center; /* Center content */
    padding-right: 0;
}

/* Center the hamburger button when collapsed */
.sidebar-container.collapsed .hamburger-btn {
    position: relative;
    right: auto;
    transform: none;
    margin: 0 auto; /* Center horizontally */
}

.sidebar-container.collapsed .logo-wrapper {
    width: auto; /* Allow logo to shrink */
}

.sidebar-container.collapsed .logo {
    max-height: 25px; /* Smaller logo when collapsed */
}
</style>