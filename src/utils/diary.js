import { diaries, selectedMonth, endOfList, spinnerLoadingPage, spinnerLoadMore, pageId, diaryIdToEdit, diaryUpdate, selectedItem, renderData, diaryQueryLimit, diaryPagination } from "../stores/globals.js"
import { usePageRedirect } from "./utils.js";
import { useUpdateTags, useUpdateAvailableTags } from "./daily.js";
import { AuthService } from '../services/auth.js';
import axios from 'axios';

export async function useGetDiaries(param1, param2) {
    //param1: true is diary page
    //param2: true is diary delete
    //console.log("param 1 "+ param1)
    //console.log("param 2 "+ param2)
    return new Promise(async (resolve, reject) => {
        console.log(" -> Getting diaries");
        
        try {
            // Check if user is authenticated
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                resolve();
                return;
            }
            
            // Prepare API parameters
            let url = '/api/diaries';
            const params = {};
            
            if (param1) {
                params.limit = diaryQueryLimit.value;
                params.skip = diaryPagination.value;
            } else {
                params.startDate = selectedMonth.value.start;
                params.endDate = selectedMonth.value.end;
            }
            
            console.log(` -> Requesting diaries with params:`, params);
            
            try {
                // Make API request with auth headers
                const headers = AuthService.getAuthHeaders();
                console.log(" -> Using auth headers:", headers);
                
                const response = await axios.get(url, { 
                    params,
                    headers
                });
                
                // Process response
                if (response.data && response.data.length > 0) {
                    if (param1) { //when on diary page and not deleting diary
                        response.data.forEach(element => {
                            diaries.push(element); // Concatenate
                        });
                    } else {
                        diaries.length = 0; // Reset before adding
                        response.data.forEach(element => {
                            diaries.push(element);
                        });
                    }
                } else {
                    if (pageId.value == "diary") {
                        endOfList.value = true;
                    }
                }
                
                diaryPagination.value = diaryPagination.value + diaryQueryLimit.value;
            } catch (error) {
                console.error("API error getting diaries:", error.response?.data || error.message);
                // If we get a 401, try to refresh the token
                if (error.response?.status === 401) {
                    console.warn("Authentication error, will try to refresh session");
                    try {
                        await AuthService.refreshUser();
                    } catch (refreshError) {
                        console.error("Failed to refresh user session:", refreshError);
                        window.dispatchEvent(new Event('auth:expired'));
                    }
                }
            }
            
            if (pageId.value != "daily") spinnerLoadingPage.value = false;
            spinnerLoadMore.value = false;
            resolve();
            
        } catch (error) {
            console.error("Error getting diaries:", error);
            if (pageId.value != "daily") spinnerLoadingPage.value = false;
            spinnerLoadMore.value = false;
            resolve(); // Resolve anyway to continue the flow
        }
    });
}

export async function useUploadDiary(param) {
    //console.log(" diaray param "+param)
    return new Promise(async (resolve, reject) => {
        try {
            await Promise.all([useUpdateAvailableTags(), useUpdateTags()]);
            
            // Check authentication
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                resolve();
                return;
            }
            
            if (diaryIdToEdit.value) {
                console.log(" -> Updating diary");
                
                // Update existing diary
                await axios.put(`/api/diaries/${diaryIdToEdit.value}`, {
                    date: diaryUpdate.dateDateFormat,
                    dateUnix: diaryUpdate.dateUnix,
                    diary: diaryUpdate.diary
                }, {
                    headers: AuthService.getAuthHeaders()
                });
                
                if (param != "autoSave") usePageRedirect();
                
            } else {
                // Check if diary with this date exists
                try {
                    const checkResponse = await axios.get('/api/diaries', {
                        params: { 
                            dateUnix: diaryUpdate.dateUnix,
                            exact: true
                        },
                        headers: AuthService.getAuthHeaders()
                    });
                    
                    if (checkResponse.data && checkResponse.data.length > 0) {
                        alert("Diary with that date already exists");
                        resolve();
                        return;
                    }
                } catch (error) {
                    console.error("Error checking for existing diary:", error);
                }
                
                console.log(" -> saving diary");
                const response = await axios.post('/api/diaries', {
                    date: diaryUpdate.dateDateFormat,
                    dateUnix: diaryUpdate.dateUnix,
                    diary: diaryUpdate.diary
                }, {
                    headers: AuthService.getAuthHeaders()
                });
                
                console.log('  --> Added new diary with id ' + response.data.id);
                if (param != "autoSave") {
                    usePageRedirect();
                } else {
                    diaryIdToEdit.value = response.data.id;
                }
            }
            
            resolve();
        } catch (error) {
            console.error("Error uploading diary:", error);
            alert("Failed to save diary: " + error.message);
            resolve();
        }
    })
}

export async function useDeleteDiary(param1, param2) {
    //console.log("selected item " + selectedItem.value)
    console.log("\nDELETING DIARY ENTRY")
    
    try {
        await axios.delete(`/api/diaries/${selectedItem.value}`, {
            headers: AuthService.getAuthHeaders()
        });
        await refreshDiaries();
    } catch (error) {
        console.error("Error deleting diary:", error);
        alert("There was a problem deleting the diary");
    }
}

async function refreshDiaries() {
    console.log(" -> Refreshing diary entries")
    return new Promise(async (resolve, reject) => {
        diaryQueryLimit.value = 10
        diaryPagination.value = 0
        diaries.length = 0
        await useGetDiaries(true)
        //useInitPopover()
        await (renderData.value += 1)
        selectedItem.value = null
        resolve()
    })
}