<script setup>
import { onBeforeMount, ref, onMounted, nextTick, onBeforeUnmount, computed } from 'vue';
import SpinnerLoadingPage from '../components/SpinnerLoadingPage.vue';
import { imports, selectedItem, itemToEditId, currentDate, diaryUpdate, timeZoneTrade, diaryIdToEdit, diaryButton, tradeTags, tagInput, selectedTagIndex, showTagsList, availableTags, tags, countdownSeconds, selectedBroker, brokers } from '../stores/globals';
import { useInitQuill, useDateCalFormat, useInitPopover } from '../utils/utils';
import { useUploadDiary } from '../utils/diary'
import { useFilterSuggestions, useTradeTagsChange, useFilterTags, useToggleTagsDropdown, useGetTags, useGetAvailableTags, useGetTagInfo } from '../utils/daily';
import { useGetTrades } from '../utils/trades';

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


let syncActiveBrokers = ref([])
let autoSyncInputs = ref({})
let isDeleting = ref(false)
let isLoading = ref(true)

// Simple pagination state
const currentPage = ref(1)
const itemsPerPage = ref(50)

// Selected items for bulk delete
const selectedItems = ref([])

// Track navigation when leaving the imports page
onBeforeUnmount(() => {
    // Set flag indicating we're navigating from imports page
    localStorage.setItem('from_imports', 'true');
    console.log('Navigating away from imports page - setting navigation flag');
});

onBeforeMount(async () => {
    isLoading.value = true;
    try {
        await useGetTrades("imports");
        await useInitPopover();
        syncActiveBrokers.value = brokers.filter(f => f.autoSync.active);
        if (!syncActiveBrokers.value.includes(localStorage.getItem('selectedBroker'))) {
            inputChooseBroker(syncActiveBrokers.value[0]?.value || '');
        }
        
        // Add event listener for delete confirmation
        nextTick(() => {
            document.addEventListener('click', handlePopoverClick);
        });
    } catch (error) {
        console.error("Error loading imports:", error);
    } finally {
        isLoading.value = false;
    }
})

onMounted(() => {
    // Clean up event listener when component is unmounted
    return () => {
        document.removeEventListener('click', handlePopoverClick)
    }
})

const selectedTab = "manageTab"

const tabs = [
    {
        id: "manageTab",
        label: "Manage Imports",
        target: "#manageNav"
    },
    /*{
        id: "syncImpTab",
        label: "Auto-Sync Imports",
        target: "#syncImpNav"
    },
    {
        id: "syncExcTab",
        label: "Auto-Sync Excursions",
        target: "#syncExcNav"
    }*/
]

function inputChooseBroker(param) {
    localStorage.setItem('selectedBroker', param)
    selectedBroker.value = param
}

// Handle clicks on the popover buttons
function handlePopoverClick(event) {
    if (event.target.classList.contains('popoverYes')) {
        deleteImport()
    } else if (event.target.classList.contains('popoverNo')) {
        selectedItem.value = null
    }
}

// Safe accessing of imports array
const importsArray = computed(() => {
    return imports.value || [];
});

// Calculate total pages and paginated imports
const totalPages = computed(() => {
    return Math.ceil(importsArray.value.length / itemsPerPage.value) || 1;
});

const paginatedImports = computed(() => {
    const start = (currentPage.value - 1) * itemsPerPage.value;
    const end = start + itemsPerPage.value;
    return importsArray.value.slice(start, end);
});

// Handle pagination
function changePage(page) {
    if (page >= 1 && page <= totalPages.value) {
        currentPage.value = page;
        selectedItems.value = [];
    }
}

function changePageSize(size) {
    itemsPerPage.value = parseInt(size);
    currentPage.value = 1;
    selectedItems.value = [];
}

// Handle item selection
function toggleSelectItem(dateUnix) {
    const index = selectedItems.value.indexOf(dateUnix);
    if (index === -1) {
        selectedItems.value.push(dateUnix);
    } else {
        selectedItems.value.splice(index, 1);
    }
}

function isItemSelected(dateUnix) {
    return selectedItems.value.includes(dateUnix);
}

// Delete the selected import(s)
async function deleteImport() {
    if ((!selectedItem.value && selectedItems.value.length === 0) || isDeleting.value) return;
    
    isDeleting.value = true;
    
    try {
        // Get IDs to delete - either single selected item or bulk selected items
        const idsToDelete = selectedItem.value ? [selectedItem.value] : selectedItems.value;
        
        // Collect all trade IDs to delete
        const allTradeIds = [];
        
        for (const dateUnix of idsToDelete) {
            const tradesForImport = importsArray.value.find(imp => imp.dateUnix === dateUnix)?.trades || [];
            if (tradesForImport.length) {
                const tradeIds = tradesForImport.map(trade => trade.objectId || trade._id);
                allTradeIds.push(...tradeIds);
            }
        }
        
        if (allTradeIds.length === 0) {
            console.error("No trades found for these imports");
            isDeleting.value = false;
            return;
        }
        
        // Get auth token
        const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
        
        if (!token) {
            console.error("Authentication token not found");
            alert("You need to log in again to perform this action.");
            isDeleting.value = false;
            return;
        }
        
        console.log(`Deleting ${allTradeIds.length} trades`);
        
        // Make API request to delete trades
        const response = await fetch('/api/trades', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ trade_ids: allTradeIds }),
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Remove the deleted imports from the list
            for (const dateUnix of idsToDelete) {
                const index = imports.value.findIndex(imp => imp.dateUnix === dateUnix);
                if (index !== -1) {
                    imports.value.splice(index, 1);
                }
            }
            
            // Set a flag to force dashboard refresh
            localStorage.setItem('force_dashboard_refresh', 'true');
            
            // Check if we've deleted all imports
            if (imports.value.length === 0) {
                console.log("All imports have been deleted. Dashboard will need complete refresh.");
                localStorage.setItem('all_imports_deleted', 'true');
            }
            
            // Reset selected items and update pagination if needed
            selectedItems.value = [];
            if (currentPage.value > totalPages.value && currentPage.value > 1) {
                currentPage.value = Math.max(1, totalPages.value);
            }
        } else {
            console.error("Failed to delete trades:", result.message);
        }
    } catch (error) {
        console.error("Error deleting import:", error);
        alert("Failed to delete import: " + error.message);
    } finally {
        isDeleting.value = false;
        selectedItem.value = null;
        
        // Close any open popovers
        const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
        popovers.forEach(popover => {
            const bsPopover = bootstrap.Popover.getInstance(popover);
            if (bsPopover) {
                bsPopover.hide();
            }
        });
    }
}
</script>
<template>
    <div class="row mt-2">
        <div>
            <nav>
                <div class="nav nav-tabs mb-2" id="nav-tab" role="tablist">
                    <button v-for="tab in tabs" :key="tab.id"
                        :class="'nav-link ' + (selectedTab == tab.id ? 'active show' : '')" :id="tab.id" data-bs-toggle="tab"
                        :data-bs-target="tab.target" type="button" role="tab" aria-controls="nav-overview"
                        aria-selected="true">{{ tab.label }}</button>
                </div>
            </nav>
            <div class="tab-content" id="nav-tabContent">
                <div v-bind:class="'tab-pane fade ' + (selectedTab == 'manageTab' ? 'active show' : '')" id="manageNav">
                    <p>Please be careful when deleting imports, especially when you are swing trading, as it can lead to
                        unexpected behavior.</p>
                    <p>When you delete an import, it will also delete your excursions. However, screenshots, tags, notes
                        and satisfactions are not deleted.</p>
                    <p>You can also manage your database using a MongoDB GUI or CLI.</p>
                    
                    <!-- Loading Indicator -->
                    <div v-if="isLoading" class="text-center py-5">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2">Loading imports...</p>
                    </div>
                    
                    <div v-else>
                        <!-- Bulk Actions Bar -->
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <button 
                                    class="btn btn-danger" 
                                    :disabled="selectedItems.length === 0 || isDeleting"
                                    @click="deleteImport"
                                >
                                    <i class="uil uil-trash-alt"></i> Delete Selected
                                    <span v-if="selectedItems.length > 0" class="badge bg-light text-dark ms-1">
                                        {{ selectedItems.length }}
                                    </span>
                                </button>
                            </div>
                            <div class="d-flex align-items-center">
                                <span class="me-2">Rows per page:</span>
                                <select 
                                    :value="itemsPerPage" 
                                    class="form-select form-select-sm" 
                                    style="width: auto;"
                                    @change="changePageSize($event.target.value)"
                                >
                                    <option value="5">5</option>
                                    <option value="10">10</option>
                                    <option value="25">25</option>
                                    <option value="50" selected>50</option>
                                </select>
                            </div>
                        </div>
                        
                        <!-- Imports Table -->
                        <table class="table">
                            <thead>
                                <tr>
                                    <th width="40">Select</th>
                                    <th>Date</th>
                                    <th>Trades</th>
                                    <th class="text-end">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="data in paginatedImports" :key="data.dateUnix">
                                    <td>
                                        <div class="form-check">
                                            <input 
                                                type="checkbox" 
                                                class="form-check-input" 
                                                :checked="isItemSelected(data.dateUnix)"
                                                @change="toggleSelectItem(data.dateUnix)"
                                            >
                                        </div>
                                    </td>
                                    <td>{{ useDateCalFormat(data.dateUnix) }}</td>
                                    <td>{{ data.trades ? data.trades.length : 0 }}</td>
                                    <td class="text-end">
                                        <i :id="data.dateUnix" v-on:click="selectedItem = data.dateUnix"
                                            class="ps-2 uil uil-trash-alt popoverDelete pointerClass" data-bs-html="true"
                                            data-bs-content="<div>Are you sure?</div><div class='text-center'><a type='button' class='btn btn-red btn-sm popoverYes'>Yes</a><a type='button' class='btn btn-outline-secondary btn-sm ms-2 popoverNo'>No</a></div>"
                                            data-bs-toggle="popover" data-bs-placement="left"></i>
                                    </td>
                                </tr>
                                <tr v-if="paginatedImports.length === 0">
                                    <td colspan="4" class="text-center py-3">No imports found</td>
                                </tr>
                            </tbody>
                        </table>
                        
                        <!-- Pagination Controls -->
                        <div v-if="importsArray.length > 0" class="d-flex justify-content-between align-items-center">
                            <div>
                                <span class="text-muted">
                                    Showing {{ (currentPage - 1) * itemsPerPage + 1 }}-{{ Math.min(currentPage * itemsPerPage, importsArray.length) }} of {{ importsArray.length }} imports
                                </span>
                            </div>
                            <nav aria-label="Imports pagination" v-if="totalPages > 1">
                                <ul class="pagination mb-0">
                                    <li class="page-item" :class="{ disabled: currentPage === 1 }">
                                        <button class="page-link dark-pagination" @click="changePage(1)" aria-label="First">
                                            <span aria-hidden="true">&laquo;</span>
                                        </button>
                                    </li>
                                    <li class="page-item" :class="{ disabled: currentPage === 1 }">
                                        <button class="page-link dark-pagination" @click="changePage(currentPage - 1)" aria-label="Previous">
                                            <span aria-hidden="true">&lsaquo;</span>
                                        </button>
                                    </li>
                                    
                                    <li v-for="page in totalPages" :key="page" class="page-item" :class="{ active: page === currentPage }">
                                        <button class="page-link dark-pagination" @click="changePage(page)">{{ page }}</button>
                                    </li>
                                    
                                    <li class="page-item" :class="{ disabled: currentPage === totalPages }">
                                        <button class="page-link dark-pagination" @click="changePage(currentPage + 1)" aria-label="Next">
                                            <span aria-hidden="true">&rsaquo;</span>
                                        </button>
                                    </li>
                                    <li class="page-item" :class="{ disabled: currentPage === totalPages }">
                                        <button class="page-link dark-pagination" @click="changePage(totalPages)" aria-label="Last">
                                            <span aria-hidden="true">&raquo;</span>
                                        </button>
                                    </li>
                                </ul>
                            </nav>
                        </div>
                    </div>
                </div>
                
                
                <div v-bind:class="'tab-pane fade ' + (selectedTab == 'syncImpTab' ? 'active show' : '')"
                    id="syncImpNav">
                    Work in progress
                    <div class="form-floating">
                        <select v-on:input="inputChooseBroker($event.target.value)" class="form-select">
                            <option v-for="item in syncActiveBrokers" v-bind:value="item.value"
                                v-bind:selected="item.value == selectedBroker">
                                {{ item.label }}</option>
                        </select>
                        <label for="floatingSelect">Select your broker or trading platform</label>
                    </div>
                    <p class="mt-2" v-show="selectedBroker">
                        Supported asset types: <span
                            v-for="(item, index) in brokers.filter(f => f.value == selectedBroker)[0].assetTypes">{{
                                item }}<span
                                v-show="brokers.filter(f => f.value == selectedBroker)[0].assetTypes.length > 1 && (index + 1) < brokers.filter(f => f.value == selectedBroker)[0].assetTypes.length">,
                            </span></span>
                    </p>
                    <p class="mt-2" v-show="selectedBroker">Instructions
                    <ul v-for="instruction in brokers.filter(f => f.value == selectedBroker)[0].autoSync.instructions">
                        <li v-html="instruction"></li>
                    </ul>
                    </p>

                    <div class="form-floating mb-2 w-25"
                        v-for="input in brokers.filter(f => f.value == selectedBroker)[0].autoSync.inputs">
                        <input id="floatingInput" type="text" class="form-control" v-model="autoSyncInputs[input.value]"
                            placeholder="" />
                        <label for="floatingInput">{{ input.label }}</label>

                    </div>
                
                </div>
                               
                
                <div v-bind:class="'tab-pane fade ' + (selectedTab == 'syncExcTab' ? 'active show' : '')"
                    id="syncExcNav">
                    Work in progress
                </div>
            </div>
        </div>
    </div>
</template>

<style>
/* Dark theme pagination */
.dark-pagination {
    color: #212529;
    background-color: #f8f9fa;
    border-color: #dee2e6;
}

/* Active state */
.page-item.active .dark-pagination {
    color: #fff;
    background-color: #343a40;
    border-color: #343a40;
}

/* Hover state */
.dark-pagination:hover {
    color: #fff;
    background-color: #495057;
    border-color: #495057;
    z-index: 2;
}

/* Focus state */
.dark-pagination:focus {
    box-shadow: 0 0 0 0.25rem rgba(52, 58, 64, 0.25);
}

/* Disabled state */
.page-item.disabled .dark-pagination {
    color: #6c757d;
    background-color: #f8f9fa;
    border-color: #dee2e6;
}
</style>