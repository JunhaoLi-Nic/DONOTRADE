<script setup>
import { ref, reactive, onBeforeMount, computed, onMounted } from 'vue'
import NoData from '../components/NoData.vue';
import SpinnerLoadingPage from '../components/SpinnerLoadingPage.vue';
import { formatDate, useEditItem } from '../utils/utils';
import { playbooks, queryLimit, selectedItem, spinnerLoadingPage, tags } from '../stores/globals';
import { useGetPlaybooks, useDeletePlaybook } from '../utils/playbooks';
import { useGetTagInfo, useGetAvailableTags, useGetTags } from '../utils/daily';
import axios from 'axios';
import { useRouter } from 'vue-router';
import TradeService from '../services/TradeService';
import PlaybookService from '../services/PlaybookService';
import AuthService from '../services/auth';

const router = useRouter();
const activeTab = ref('My Playbook');
const tabs = ['My Playbook', 'Shared Playbook'];
const showConfirmDialog = ref(false);
const playbookToDelete = ref(null);
const loadError = ref(false);
const errorMessage = ref('');
const allTrades = ref([]);

// Calculate real statistics based on trades filtered by playbook tags
const playbooksWithStats = computed(() => {
    return playbooks.map(playbook => {
        // Get trades for this playbook using tags
        const playbookTrades = playbook.tags && playbook.tags.length > 0 ? 
            PlaybookService.filterTradesByTags(allTrades.value, 
                playbook.tags.map(tagId => ({ id: tagId }))) : [];

        // Calculate stats based on these trades
        const stats = PlaybookService.calculatePlaybookStats(
            playbookTrades, 
            TradeService.calculateTradeProfit
        );

        return {
            ...playbook,
            name: playbook.name || 'Untitled Playbook',
            icon: playbook.icon || '📈',
            trades: stats.tradesCount || 0,
            netPnL: stats.netPnL || 0,
            winRate: stats.winRate || 0,
            missedTrades: playbook.missedTrades || 0,
            expectancy: stats.netPnL / (stats.tradesCount || 1) || 0,
            sharedUsers: playbook.sharedUsers || [],
            created_at: playbook.created_at || 'No date'
        };
    });
});

// Load trades for calculating stats
async function loadTrades() {
    try {
        // Get auth headers
        const headers = AuthService.getAuthHeaders();
        
        // Fetch trades from the API
        const response = await axios.get('/api/trades', { 
            params: { limit: 1000 },
            headers 
        });
        
        if (response.data && Array.isArray(response.data)) {
            // Process trades
            let processedTrades = TradeService.processTradeData(response.data);
            
            // Match tags from global store
            let taggedTrades = TradeService.matchTradeTagsFromGlobal(processedTrades, tags);
            
            // Filter out EVEN status trades
            allTrades.value = taggedTrades.filter(trade => trade.status !== 'EVEN');
            console.log(`Loaded ${allTrades.value.length} trades for playbook calculations`);
        } else {
            console.warn('API returned no trades or invalid format');
            allTrades.value = [];
        }
    } catch (error) {
        console.error('Error loading trades:', error);
        allTrades.value = [];
    }
}

onBeforeMount(async () => {
    loadError.value = false;
    errorMessage.value = '';
    
    try {
        spinnerLoadingPage.value = true;
        
        // Load in order: tags first, then trades, then playbooks
        await useGetAvailableTags();
        await useGetTags();
        await loadTrades();
        await useGetPlaybooks();
    } catch (error) {
        console.error("Error loading data:", error);
        loadError.value = true;
        errorMessage.value = error.message || "Failed to load data";
    } finally {
        spinnerLoadingPage.value = false;
    }
});

onMounted(() => {
    document.addEventListener('click', handleOutsideClick);
});

// For deleting items
const confirmDelete = (playbook) => {
    playbookToDelete.value = playbook;
    showConfirmDialog.value = true;
    event.stopPropagation(); // Prevent row click event
};

const handleOutsideClick = (event) => {
    if (showConfirmDialog.value) {
        const dialog = document.querySelector('.confirm-dialog');
        if (dialog && !dialog.contains(event.target) && 
            !event.target.closest('.delete-btn')) {
            showConfirmDialog.value = false;
        }
    }
};

const executeDelete = async () => {
    if (playbookToDelete.value) {
        selectedItem.value = playbookToDelete.value._id;
        await useDeletePlaybook();
        showConfirmDialog.value = false;
        playbookToDelete.value = null;
    }
};

const cancelDelete = () => {
    showConfirmDialog.value = false;
    playbookToDelete.value = null;
};

// Navigation to detail view
const navigateToDetail = (id) => {
    console.log('Navigating to playbook detail:', id);
    router.push(`/playbook/${id}`);
};

// Create new playbook
const createNewPlaybook = () => {
    router.push('/addPlaybook');
};
</script>

<template>
    <SpinnerLoadingPage />
    <div class="container" v-show="!spinnerLoadingPage">
        <div class="header-container">
            <div>
                <h1>Playbooks</h1>
                <p class="text-muted">Manage your trading strategies and track their performance</p>
            </div>
            <div>
                <button class="btn btn-primary" @click="createNewPlaybook">
                    <i class="uil uil-plus-circle"></i> New Playbook
                </button>
            </div>
        </div>

        <!-- Error Alert -->
        <div v-if="loadError" class="alert alert-danger mb-4">
            <i class="uil uil-exclamation-triangle me-2"></i>
            {{ errorMessage || "Failed to load playbooks. Using demo data instead." }}
        </div>

        <div class="tabs-container">
            <div class="nav-tabs">
                <button 
                    v-for="tab in tabs" 
                    :key="tab"
                    class="nav-link" 
                    :class="{ active: activeTab === tab }" 
                    @click="activeTab = tab"
                >
                    {{ tab }}
                </button>
            </div>
        </div>

        <div class="tab-content">
            <div class="tab-pane active">
                <div v-if="playbooks.length === 0" class="no-data-container">
                    <NoData 
                        messageText="No playbooks found" 
                        actionText="Create your first playbook"
                        actionLink="/addPlaybook" 
                    />
                </div>

                <div v-else class="table-responsive">
                    <table class="table table-playbooks">
                        <!-- 
                            <thead> is an HTML table element that defines the header section of a table.
                            It is used to group the header content in a table, typically containing column titles.

                            <tr> stands for "table row" and is used to define a row within a table.
                            Inside <thead>, a <tr> usually contains header cells.

                            <th> stands for "table header cell" and is used inside a <tr> to define a header cell.
                            Text inside <th> is typically bold and centered by default, and it describes the content of the column below it.
                        -->
                        <thead>
                            <tr>
                                <th>Playbook</th>
                                <th>Tags</th>
                                <th>Trades</th>
                                <th>Net P&L</th>
                                <th>Win %</th>
                                <th>Expectancy</th>
                                <th class="text-end">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <!-- 
                                v-for is a Vue.js directive used to render a list of elements by iterating over an array or object.
                                In the example below, v-for="pb in playbooksWithStats" means that for each item (pb) in the playbooksWithStats array,
                                a <tr> (table row) will be created. The :key="pb._id" helps Vue efficiently update the DOM by uniquely identifying each row.
                            -->
                            <tr v-for="pb in playbooksWithStats" :key="pb._id" @click="navigateToDetail(pb._id)"
                                class="playbook-row">
                                <td>
                                    <div class="playbook-title">
                                        <div class="playbook-icon">{{ pb.icon }}</div>
                                        <div>
                                            <div class="playbook-name">{{ pb.name }}</div>
                                            <div class="playbook-date">
                                                {{ formatDate(pb.created_at) }}
                                            </div>
                                        </div>
                                    </div>
                                </td>
                                <td>
                                    <!-- Playbook Tags -->
                                    <!-- 
                                        pb.tags comes from the playbook object in the playbooksWithStats array.
                                        playbooksWithStats is a computed property that maps over the playbooks array (from the global store).
                                        Each playbook object may have a 'tags' property, which is expected to be an array of tag IDs.
                                        Example: pb.tags = ['tagId1', 'tagId2', ...]
                                    -->
                                    <div class="tags-wrapper">
                                        <span v-if="pb.tags && pb.tags.length" 
                                              v-for="(tagId, index) in pb.tags.slice(0, 2)" 
                                              :key="tagId"
                                              class="tag txt-small"
                                              :style="{ 'background-color': useGetTagInfo(tagId).groupColor || '#555' }">
                                            {{ useGetTagInfo(tagId).tagName || 'Tag' }}
                                        </span>
                                        <span v-if="pb.tags && pb.tags.length > 2" class="tag-more txt-small">
                                            +{{ pb.tags.length - 2 }}
                                        </span>
                                        <span v-if="!pb.tags || pb.tags.length === 0" class="no-tags">
                                            —
                                        </span>
                                    </div>
                                </td>
                                <td>{{ pb.trades }}</td>
                                <td :class="pb.netPnL >= 0 ? 'text-success' : 'text-danger'">
                                    ${{ pb.netPnL.toLocaleString() }}
                                </td>
                                <td>{{ pb.winRate }}%</td>
                                <td>${{ pb.expectancy.toLocaleString() }}</td>
                                <td class="text-end">
                                    <div class="action-buttons">
                                        <button class="btn btn-outline-light"
                                            @click.stop="router.push(`/playbook/${pb._id}`)">
                                            <i class="uil uil-eye"></i>
                                        </button>
                                        <button class="btn btn-outline-light" @click.stop="useEditItem(pb)">
                                            <i class="uil uil-edit"></i>
                                        </button>
                                        <button class="btn btn-outline-danger delete-btn"
                                            @click.stop="confirmDelete(pb)">
                                            <i class="uil uil-trash-alt"></i>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Confirmation Dialog -->
    <div class="confirm-dialog-overlay" v-if="showConfirmDialog">
        <div class="confirm-dialog">
            <h3>Delete Playbook</h3>
            <p>Are you sure you want to delete "{{ playbookToDelete?.name }}"?</p>
            <p class="warning-text">This action cannot be undone.</p>
            <div class="dialog-actions">
                <button class="btn btn-outline-light" @click="cancelDelete">Cancel</button>
                <button class="btn btn-danger" @click="executeDelete">Delete</button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.container {
    padding: 1.5rem;
}

h1 {
    font-weight: 600;
    color: #fff;
    margin-bottom: 0.2rem;
}

.header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
}

.text-muted {
    color: #999;
}

.tabs-container {
    margin-bottom: 1rem;
}

.nav-tabs {
    display: flex;
    border-bottom: 1px solid #333;
}

.nav-link {
    background: none;
    border: none;
    color: #999;
    border-bottom: 2px solid transparent;
    padding: 0.75rem 1.25rem;
    transition: all 0.3s ease;
    cursor: pointer;
}

.nav-link.active {
    color: #fff;
    border-bottom: 2px solid #5e72e4;
    background-color: transparent;
}

.nav-link:hover:not(.active) {
    color: #fff;
    border-bottom: 2px solid #444;
}

.no-data-container {
    margin-top: 3rem;
}

.table-responsive {
    overflow-x: auto;
}

.table {
    width: 100%;
    margin-top: 1rem;
    color: inherit;
    border-collapse: separate;
    border-spacing: 0;
}

.table thead th {
    background-color: #1a1a1a;
    color: #999;
    border-bottom: none;
    font-weight: 500;
    font-size: 0.9rem;
    padding: 0.75rem 1rem;
    text-align: left;
}

.table tbody td {
    padding: 1rem;
    border-top: 1px solid #2c2c2c;
    background-color: #1e1e1e;
}

.playbook-row {
    cursor: pointer;
    transition: background-color 0.15s ease;
}

.playbook-row:hover td {
    background-color: #252525;
}

.playbook-title {
    display: flex;
    align-items: center;
}

.playbook-icon {
    font-size: 1.5rem;
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #2c2c2c;
    border-radius: 8px;
    margin-right: 1rem;
}

.playbook-name {
    font-weight: 500;
    font-size: 1rem;
}

.playbook-date {
    color: #999;
    font-size: 0.8rem;
}

.text-success {
    color: #2dce89 !important;
}

.text-danger {
    color: #f5365c !important;
}

.text-end {
    text-align: right;
}

.action-buttons {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
}

.btn {
    padding: 0.5rem 1rem;
    border-radius: 0.375rem;
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.15s ease;
}

.btn-sm {
    padding: 0.25rem 0.5rem;
    font-size: 0.75rem;
}

.btn-outline-light {
    border: 1px solid #333;
    color: #fff;
    background-color: transparent;
}

.btn-outline-light:hover {
    background-color: #333;
    border-color: #444;
}

.btn-outline-danger {
    border: 1px solid #f5365c;
    color: #f5365c;
    background-color: transparent;
}

.btn-outline-danger:hover {
    background-color: rgba(245, 54, 92, 0.1);
}

.btn-danger {
    background-color: #f5365c;
    border-color: #f5365c;
    color: white;
}

.btn-danger:hover {
    background-color: #e03057;
}

.btn-primary {
    background-color: #5e72e4;
    border-color: #5e72e4;
    color: white;
    padding: 0.5rem 1.25rem;
}

.btn-primary:hover {
    background-color: #4c61d0;
}

.btn i {
    margin-right: 0.25rem;
}

.tags-wrapper {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
}

.tag {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    background-color: #555;
    color: white;
}

.tag-more {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    background-color: #333;
    color: #999;
}

.no-tags {
    color: #666;
}

.txt-small {
    font-size: 0.8rem;
}

.confirm-dialog-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.confirm-dialog {
    background-color: #1e1e1e;
    border-radius: 8px;
    padding: 1.5rem;
    width: 400px;
    max-width: 90%;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.confirm-dialog h3 {
    margin-top: 0;
    margin-bottom: 1rem;
}

.confirm-dialog .warning-text {
    color: #f5365c;
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
}

.dialog-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
}

.alert {
    padding: 0.75rem 1.25rem;
    border-radius: 0.375rem;
    margin-bottom: 1rem;
}

.alert-danger {
    background-color: rgba(245, 54, 92, 0.1);
    color: #f5365c;
    border: 1px solid rgba(245, 54, 92, 0.2);
}

.me-2 {
    margin-right: 0.5rem;
}
</style>