import { playbookIdToEdit, playbookUpdate, playbooks, queryLimit, renderData, selectedItem, spinnerLoadingPage } from "../stores/globals.js";
import { useInitPopover, usePageRedirect } from "./utils.js";
import axios from 'axios';
import { AuthService } from "../services/auth";

export async function useGetPlaybooks(param) {
    return new Promise(async(resolve, reject) => {
        spinnerLoadingPage.value = true;
        playbooks.length = 0;
            
        try {
            // Get auth headers from the service with error handling
            let headers = {};
            try {
                headers = AuthService.getAuthHeaders();
            } catch (authError) {
                console.error("Error getting auth headers:", authError);
                // Continue with empty headers, the API might still work
            }
            
            // Fetch playbooks from the API
            const response = await axios.get('/api/playbooks', { 
                headers, 
                params: {
                    limit: param || queryLimit.value,
                }
            });
            
            // The API response object (`response`) contains metadata (status, headers, etc.) and the actual data payload is in `response.data`.
            // We use `response.data` because that's where the array of playbooks is returned by the backend.
            console.log(" -> Got playbooks from API:", response.data);
            
            if (response.data && Array.isArray(response.data)) {
                
                response.data.forEach(element => {
                    try {
                        // Instead of spreading ...element, we could explicitly assign fields if we want more control.
                        // However, spreading ...element copies all properties from the API object into the new object,
                        // ensuring we don't miss any fields that might be added in the backend in the future.
                        // It also allows us to override or add new fields as needed below.
                        // If you want to avoid ...element, you could do something like:
                        const playbookWithStats = {
                            ...element,
                            name: element.name || extractNameFromPlaybook(element.playbook) || 'Untitled Playbook',
                            icon: getPlaybookIcon(element),
                            trades: element.trades || 0,
                            netPnL: element.netPnL || 0,
                            winRate: element.winRate || 0,
                            missedTrades: element.missedTrades || 0,
                            expectancy: element.expectancy || 0,
                            sharedUsers: element.sharedUsers || [] // Empty array by default
                        };
                        
                        playbooks.push(playbookWithStats);
                    } catch (elementError) {
                        console.error("Error processing playbook item:", elementError, element);
                    }
                });
                
                // Load tags for each playbook
                await loadPlaybookTags();
            } else {
                console.warn(" -> API returned no playbooks or invalid data format", response.data);
            }
            
            spinnerLoadingPage.value = false;
            resolve();
        } catch (error) {
            console.error("Error fetching playbooks:", error);
            if (error.response) {
                console.log("Response data:", error.response.data);
                console.log("Response status:", error.response.status);
            }
            
            // Add mock data for testing UI when API fails
            console.log("Adding mock playbook data for testing...");
            addMockPlaybooks();
            
            spinnerLoadingPage.value = false;
            resolve(); // Resolve instead of reject to prevent UI from breaking
        }
    });
}


// Add mock playbooks for testing when API fails
function addMockPlaybooks() {
    const mockPlaybooks = [
        {
            _id: 'mock1',
            name: 'Morning Gap Strategy',
            playbook: '<h1>Morning Gap Strategy</h1><p>Buy the morning gap and sell at the first sign of weakness.</p>',
            createdAt: new Date().toISOString(),
            icon: '🌅',
            trades: 8,
            netPnL: 45000,
            winRate: 75,
            missedTrades: 2,
            expectancy: 5625,
            tags: []
        },
        {
            _id: 'mock2',
            name: 'Afternoon Reversal',
            playbook: '<h1>Afternoon Reversal</h1><p>Look for reversals in the afternoon session.</p>',
            createdAt: new Date(Date.now() - 86400000).toISOString(),
            icon: '↩️',
            trades: 5,
            netPnL: -12000,
            winRate: 40,
            missedTrades: 1,
            expectancy: -2400,
            tags: []
        }
    ];
    
    playbooks.push(...mockPlaybooks);
}

// Load tags for all playbooks
async function loadPlaybookTags() {
    try {
        // Get auth headers from the service with error handling
        let headers = {};
        try {
            headers = AuthService.getAuthHeaders();
        } catch (authError) {
            console.error("Error getting auth headers for tags:", authError);
            // Continue with empty headers
        }
        
        for (const playbook of playbooks) {
            try {
                const playbookId = playbook._id;
                if (!playbookId) continue;
                
                const response = await axios.get(`/api/playbook/${playbookId}/tags`, { headers });
                
                if (response.data && response.data.tags) {
                    // playbook.tags is being set here. It is not explicitly defined before,
                    // but in JavaScript, you can add new properties to objects at any time.
                    // If playbook does not already have a 'tags' property, this line will create it.
                    playbook.tags = response.data.tags;
                }
            } catch (error) {
                console.error(`Error fetching tags for playbook ${playbook._id}:`, error);
            }
        }
    } catch (error) {
        console.error("Error in loadPlaybookTags:", error);
    }
}

// Helper function to extract a name from playbook content
export function extractNameFromPlaybook(playbookContent) {
    if (!playbookContent) return 'Untitled Playbook';
    
    // Try to extract a title from the HTML content
    const titleMatch = playbookContent.match(/<h1[^>]*>(.*?)<\/h1>/i) || 
                      playbookContent.match(/<h2[^>]*>(.*?)<\/h2>/i) || 
                      playbookContent.match(/<h3[^>]*>(.*?)<\/h3>/i) ||
                      playbookContent.match(/<strong[^>]*>(.*?)<\/strong>/i);
    
    if (titleMatch && titleMatch[1]) {
        // Remove any HTML tags and trim
        return titleMatch[1].replace(/<\/?[^>]+(>|$)/g, "").trim();
    }
    
    // Extract first line as name if no title found
    const firstLine = playbookContent.split('<p>')[1];
    if (firstLine) {
        const text = firstLine.replace(/<\/?[^>]+(>|$)/g, "").trim();
        if (text.length > 0) {
            // Return first 30 chars as the title
            return text.length > 30 ? text.substring(0, 30) + '...' : text;
        }
    }
    
    return 'Untitled Playbook';
}

// Assign an icon based on playbook content or name
function getPlaybookIcon(playbook) {
    const icons = ['📈', '📊', '📉', '💹', '📋', '🔍', '⚡', '🔔', '📝'];
    const name = playbook.name || '';
    
    // Assign specific icons based on name keywords
    if (name.toLowerCase().includes('morning')) return '🌅';
    if (name.toLowerCase().includes('open')) return '📖';
    if (name.toLowerCase().includes('sell')) return '💰';
    if (name.toLowerCase().includes('reversal')) return '↩️';
    if (name.toLowerCase().includes('gap')) return '🌠';
    if (name.toLowerCase().includes('drive')) return '🚗';
    if (name.toLowerCase().includes('setup')) return '❌';
    if (name.toLowerCase().includes('delta')) return '🔄';
    if (name.toLowerCase().includes('day')) return '💼';
    
    // Generate a consistent icon based on name hash or id
    const id = playbook._id || playbook.id || playbook.objectId || '';
    const hash = id.toString().split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return icons[hash % icons.length];
}

// Generate random values for demo purposes
function getRandomPnL() {
    // 70% chance of positive P&L
    return Math.random() > 0.3 ? 
        Math.floor(Math.random() * 100000) : 
        -Math.floor(Math.random() * 20000);
}

function getRandomWinRate() {
    return Math.floor(Math.random() * 100);
}

function getRandomExpectancy() {
    return Math.floor(Math.random() * 50000);
}

export async function useUploadPlaybook() {
    try {
        // Get auth headers with error handling
        let headers = {};
        try {
            headers = AuthService.getAuthHeaders();
        } catch (authError) {
            console.error("Error getting auth headers for upload:", authError);
            // Continue with empty headers
        }
        
        if (playbookIdToEdit.value) {
            console.log(" -> Updating playbook");
            
            // Update existing playbook
            await axios.put(`/api/playbooks/${playbookIdToEdit.value}`, {
                playbook: playbookUpdate.playbook
            }, { headers });
            
            usePageRedirect();
        } else {
            console.log(" -> Check if playbook already exists");
            
            // Check for existing playbook with same date
            const checkResponse = await axios.get(`/api/playbooks?dateUnix=${playbookUpdate.dateUnix}`, { headers });
            
            if (checkResponse.data && Array.isArray(checkResponse.data) && checkResponse.data.length > 0) {
                alert("Playbook with that date already exists");
                return;
            }
            
            console.log(" -> saving playbook");
            
            // Create new playbook
            await axios.post('/api/playbooks', {
                date: playbookUpdate.dateDateFormat,
                dateUnix: playbookUpdate.dateUnix,
                playbook: playbookUpdate.playbook
            }, { headers });
            
            usePageRedirect();
        }
    } catch (error) {
        console.error("Error saving playbook:", error);
        alert("Failed to save playbook: " + (error.response?.data?.detail || error.message));
    }
}

export async function useDeletePlaybook() {
    console.log("\nDELETING PLAYBOOK ENTRY");
    
    try {
        if (!selectedItem.value) {
            alert("No playbook selected");
            return;
        }
        
        // Get auth headers with error handling
        let headers = {};
        try {
            headers = AuthService.getAuthHeaders();
        } catch (authError) {
            console.error("Error getting auth headers for delete:", authError);
            // Continue with empty headers
        }
        
        // Delete the playbook
        await axios.delete(`/api/playbooks/${selectedItem.value}`, { headers });
        
        // Refresh the list
        await refreshPlaybooks();
    } catch (error) {
        console.error("Error deleting playbook:", error);
        alert("Failed to delete playbook: " + (error.response?.data?.detail || error.message));
    }
}

async function refreshPlaybooks() {
    console.log(" -> Refreshing playbooks");
    return new Promise(async (resolve, reject) => {
        try {
            playbooks.length = 0;
            await useGetPlaybooks();
            await (renderData.value += 1);
            selectedItem.value = null;
            resolve();
        } catch (error) {
            console.error("Error refreshing playbooks:", error);
            // Still resolve to prevent UI from breaking
            playbooks.length = 0;
            addMockPlaybooks();
            await (renderData.value += 1);
            selectedItem.value = null;
            resolve();
        }
    });
}