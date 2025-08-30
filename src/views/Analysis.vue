<script setup>
import { ref } from 'vue'
import AnalysisMarket from '../components/analysis/AnalysisMarket.vue';
import AnalysisStock from '../components/analysis/AnalysisStock.vue';
import AnalysisOverview from '../components/analysis/AnalysisOverview.vue';
import AnalysisOption from '../components/analysis/AnalysisOption.vue';
import { spinnerLoadingPage } from '../stores/globals';

const currentTab = ref('overview')


// Pseudocode for Analysis page with 3 sectors
const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'market', label: 'Market Analysis' },
    { id: 'stocks', label: 'Stock Analysis' },
    { id: 'options', label: 'Option Analysis' },
]

function switchTab(tabId) {
    currentTab.value = tabId;
}

</script>

<template>
    <spinnerLoadingPage/>
    <header class="section-name">
        Analysis / {{tabs.find(tabs => currentTab === tabs.id)?.label || "nothing in here"}}
    </header>
    <div class="analysis-container">
        <ul class="nav nav-tabs">
            <li class="nav-item" v-for="tab in tabs" :key="tab.id">
                <button class="nav-link" :class="{ active: currentTab === tab.id }" @click="switchTab(tab.id)">
                    {{ tab.label }}
                </button>
            </li>
        </ul>
    </div>
    <!-- Tab Content-->
    <div class="tab-content">
        <div v-if="currentTab === 'overview'" class="tab-pane active">
            <AnalysisOverview/>
        </div>

        <div v-if="currentTab === 'market'" class="tab-pane active">
            <AnalysisMarket/>
        </div>

        <div v-if="currentTab === 'stocks'" class="tab-pane active">
            <AnalysisStock/>
        </div>

        <div v-if="currentTab === 'options'" class="tab-pane active">
            <AnalysisOption/>
        </div>
    </div>

</template>

<style scoped>
.section-name {
    font-size: small;
    padding: 0% 0% 0% 0%;
    color: #b5abab;
}

.analysis-container {
    display: flex;
    flex-direction: column;
    gap: 2rem;
    padding-top: 20px;
}

.analysis-sector {
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.nav-tabs {
    border-bottom: 1px solid #333;
}

.nav-item {
    list-style: none;
}

.nav-link {
    border: none;
    border-bottom: 2px solid transparent;
    padding: 0.5rem 1rem;
    cursor: pointer;
    transition: border-color 0.3s ease;
}

.nav-link:hover {
    border-color: #007bff;
}

.nav-link.active {
    border-color: #007bff;
}


/* Specific styling for each sector would go here */
</style>