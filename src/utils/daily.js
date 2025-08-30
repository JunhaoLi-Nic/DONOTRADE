import { excursions, queryLimit, satisfactionArray, satisfactionTradeArray, tags, selectedRange, availableTags, currentUser, tradeTags, tradeTagsDateUnix, tradeTagsId, newTradeTags, pageId, notes, tradeNote, tradeNoteDateUnix, tradeNoteId, spinnerSetups, spinnerSetupsText, availableTagsArray, tagInput, selectedTagIndex, showTagsList, tradeTagsChanged, filteredTrades, itemTradeIndex, tradeIndex, saveButton, screenshot, screenshotsPagination, screenshotsQueryLimit, diaryUpdate, diaryQueryLimit, diaryPagination, apis } from "../stores/globals.js";
import { daysBack } from "../stores/globals.js";
import axios from 'axios'
import { AuthService } from '../services/auth.js'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
dayjs.extend(utc)
import isoWeek from 'dayjs/plugin/isoWeek.js'
dayjs.extend(isoWeek)
import timezone from 'dayjs/plugin/timezone'
dayjs.extend(timezone)
import duration from 'dayjs/plugin/duration.js'
dayjs.extend(duration)
import updateLocale from 'dayjs/plugin/updateLocale.js'
dayjs.extend(updateLocale)
import localizedFormat from 'dayjs/plugin/localizedFormat.js'
dayjs.extend(localizedFormat)
import customParseFormat from 'dayjs/plugin/customParseFormat.js'
dayjs.extend(customParseFormat)
import { validateDateTimestamp } from './utils.js'

//query limit must be same as diary limit
let satisfactionPagination = 0

export async function useGetSatisfactions() {
    return new Promise(async (resolve, reject) => {
        console.log("\nGETTING SATISFACTIONS");
        
        try {
            // Use our direct API instead of Parse
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                resolve();
                return;
            }
            
            let url = '/api/satisfactions';
            const params = {};
            
            if (pageId.value == "diary") {
                params.tradeId = "undefined"; // Special flag to get non-trade satisfactions
                params.limit = diaryQueryLimit.value;
                params.skip = satisfactionPagination;
            } else {
                satisfactionTradeArray.length = 0;
                satisfactionArray.length = 0;
                let startD = selectedRange.value?.start || dayjs().startOf('month').unix();
                let endD = selectedRange.value?.end || dayjs().endOf('month').unix();
                
                // Ensure dates aren't identical (add 1 day if they are)
                if (startD === endD) {
                    endD = dayjs.unix(startD).add(1, 'day').endOf('day').unix();
                }
                
                params.startDate = startD;
                params.endDate = endD;
                params.limit = queryLimit.value;
            }
            
            // Add auth token to headers
            const headers = {
                'Authorization': `Bearer ${AuthService.token}`
            };
            
            const response = await axios.get(url, { 
                params,
                headers
            });
            
            // Process the response
            if (response.data && Array.isArray(response.data)) {
                response.data.forEach(item => {
                    if (item.tradeId != undefined) {
                        satisfactionTradeArray.push(item);
                    } else {
                        satisfactionArray.push(item);
                    }
                });
            }
            
            console.log(" -> Trades satisfaction loaded");
            satisfactionPagination = satisfactionPagination + diaryQueryLimit.value;
            
        } catch (error) {
            console.error("Error getting satisfactions:", error);
        }
        
        resolve();
    });
}

export const useDailySatisfactionChange = async (tradeId, dateUnix, satisfaction, itemTrade = null) => {
    console.log("\nDAILY SATISFACTION CHANGE")

    if (itemTrade) {
        itemTrade.satisfaction = satisfaction;
    }

    if (tradeId) {
        let index = satisfactionTradeArray.findIndex(obj => obj.tradeId == tradeId)
        if (index != -1) {
            satisfactionTradeArray[index].satisfaction = satisfaction
        } else {
            let temp = {}
            temp.dateUnix = dateUnix
            temp.satisfaction = satisfaction
            temp.tradeId = tradeId
            satisfactionTradeArray.push(temp)
        }
        await useUpdateSatisfaction(dateUnix, satisfaction, tradeId)
    } else {
        let index = satisfactionArray.findIndex(obj => obj.dateUnix == dateUnix)
        if (index != -1) {
            satisfactionArray[index].satisfaction = satisfaction
        } else {
            let temp = {}
            temp.dateUnix = dateUnix
            temp.satisfaction = satisfaction
            satisfactionArray.push(temp)
        }
        await useUpdateSatisfaction(dateUnix, satisfaction, null)
    }
}

export const useUpdateSatisfaction = async (dateUnix, satisfaction, tradeId) => { //param1 : daily unixDate ; param2 : true / false ; param3: dateUnixDay ; param4: tradeId
    //console.log(" param 1 " + dateUnix)
    console.log(" -> updating satisfactions")
    return new Promise(async (resolve, reject) => {
        try {
            // Use our direct API instead of Parse
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                reject("No user logged in");
                return;
            }
            
            // Prepare data for API
            const satisfactionData = {
                dateUnix: dateUnix,
                satisfaction: satisfaction
            };

            if (tradeId) {
                satisfactionData.tradeId = tradeId;
            }
            
            // Send to API
            await axios.post('/api/updateSatisfaction', satisfactionData);
            console.log(' -> Updated satisfaction successfully');
            
            // Re-fetch satisfactions to update the UI
            await useGetSatisfactions();
            
            resolve();
        } catch (error) {
            console.error('Failed to update satisfaction:', error);
            reject(error);
        }
    });
}


export async function useGetExcursions() {
    return new Promise(async (resolve, reject) => {
        console.log("\nGETTING EXCURSIONS");
        
        try {
            // Instead of using Parse, use our direct API
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                excursions.length = 0;
                resolve();
                return;
            }
            
            let url = '/api/excursions';
            const params = {};
            
            if (pageId.value === "addExcursions") {
                let startD = dayjs().subtract(daysBack.value, 'days').unix();
                let endD = dayjs().unix();
                params.startDate = startD;
                params.endDate = endD;
                params.sortBy = "dateUnix";
                params.sortDirection = "asc";
            } else {
                let startD = selectedRange.value?.start || dayjs().startOf('month').unix();
                let endD = selectedRange.value?.end || dayjs().endOf('month').unix();
                
                // Ensure dates aren't identical (add 1 day if they are)
                if (startD === endD) {
                    endD = dayjs.unix(startD).add(1, 'day').endOf('day').unix();
                }
                
                params.startDate = startD;
                params.endDate = endD;
                params.limit = queryLimit.value;
            }
            
            // Add auth token to headers
            const headers = {
                'Authorization': `Bearer ${AuthService.token}`
            };
            
            const response = await axios.get(url, { 
                params,
                headers
            });
            
            // Clear existing excursions
            excursions.length = 0;
            
            // Add the new data
            if (response.data && Array.isArray(response.data)) {
                response.data.forEach(element => {
                    excursions.push(element);
                });
            }
            
            console.log(" -> Excursions loaded successfully");
            
        } catch (error) {
            console.error("Error getting excursions:", error);
            excursions.length = 0;
        }
        
        resolve();
    });
}

/****************************************$
 * 
 * TAGS 
 ****************************************/
export const useGetTagInfo = (param) => {
    //console.log("param "+JSON.stringify(param))
    //console.log(" available tags "+JSON.stringify(availableTags))
    const findTagInfo = (tagId) => {
        let temp = {}
        //check if tag id exists then return color
        for (let obj of availableTags) {
            for (let tag of obj.tags) {
                if (tag.id === tagId) {
                    temp.tagGroupId = obj.id
                    temp.tagGroupName = obj.name
                    temp.groupColor = obj.color
                    temp.tagName = tag.name
                    return temp
                }
            }
        }

        //Else return default color or new Ungrouped color
        let color = "#6c757d"
        if (availableTags.length > 0) {
            color = availableTags.filter(obj => obj.id == "group_0")[0].color
        }
        temp.groupColor = color
        temp.tagName = ''
        return temp
    }

    const tagIdToFind = param;
    const tagInfo = findTagInfo(tagIdToFind);
    //console.log(" tagInfo "+JSON.stringify(tagInfo))
    return tagInfo
}

export async function useGetTags() {
    return new Promise(async (resolve, reject) => {
        console.log("\nGETTING TAGS");
        
        try {
            // Check authentication
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                tags.length = 0;
                // Trigger login modal
                window.dispatchEvent(new Event('auth:expired'));
                resolve();
                return;
            }
            
            // Debug auth information
            console.log(" -> Auth Debug Info:");
            console.log(" -> Current User:", currentUser ? currentUser.email : "null");
            console.log(" -> Has Token:", !!AuthService.token);
            
            // Force refresh auth token
            AuthService.debug();
            
            let url = '/api/tags';
            const params = {};
            
            // Get date range
            let startD = selectedRange.value?.start || dayjs().startOf('month').unix();
            let endD = selectedRange.value?.end || dayjs().endOf('month').unix();
            
            // Validate the dates directly
            const validatedDates = validateDateTimestamp({ start: startD, end: endD });
            
            // Use validated dates in the request
            params.startDate = validatedDates.start;
            params.endDate = validatedDates.end;
            
            // Use a reasonable limit value
            params.limit = queryLimit.value || 1000;
            
            // Ensure we have auth headers
            const headers = AuthService.getAuthHeaders();
            console.log(" -> Auth headers:", headers);
            
            // Log the request info for debugging
            console.log(`  -> Requesting tags with date range: ${dayjs.unix(validatedDates.start).format('YYYY-MM-DD')} to ${dayjs.unix(validatedDates.end).format('YYYY-MM-DD')}`);
            
            const response = await axios.get(url, { 
                params,
                headers
            });
            
            // Reset and process data
            tags.length = 0;
            
            if (response.data && Array.isArray(response.data)) {
                response.data.forEach(element => {
                    tags.push(element);
                });
                console.log(` -> Loaded ${response.data.length} tags successfully`);
            }
            
        } catch (error) {
            console.error("Error getting tags:", error.response?.data || error.message || error);
            
            // Check if this is an auth error
            if (error.response?.status === 401) {
                console.warn("Authentication error detected. Showing login modal...");
                // Trigger login modal
                window.dispatchEvent(new Event('auth:expired'));
            }
        }
        
        resolve();
    });
}

export async function useGetAvailableTags() {
    return new Promise(async (resolve, reject) => {
        console.log(" -> Getting Available Tags");
        
        try {
            // Use our direct API instead of Parse
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                resolve();
                return;
            }
            
            // Add auth token to headers
            const headers = {
                'Authorization': `Bearer ${AuthService.token}`
            };
            
            const response = await axios.get('/api/availableTags', { headers });
            
            // Clear existing tags
            availableTags.length = 0;
            
            // Process the response
            if (response.data && Array.isArray(response.data)) {
                response.data.forEach(item => {
                    availableTags.push(item);
                });
                console.log(` -> Loaded ${availableTags.length} available tag groups`);
            } else {
                // Create default structure if no tags exist
                availableTags.push({
                    id: "group_0",
                    name: "Ungrouped",
                    color: "#6c757d",
                    tags: []
                });
            }
            
            // Create array form for autocomplete
            useCreateAvailableTagsArray();
            
        } catch (error) {
            console.error("Error getting available tags:", error);
            // Create a default tag group if we can't load from server
            availableTags.length = 0;
            availableTags.push({
                id: "group_0",
                name: "Ungrouped",
                color: "#6c757d",
                tags: []
            });
        }
        
        resolve();
    });
}

export const useCreateAvailableTagsArray = () => {
    availableTagsArray.splice(0)
    for (let index = 0; index < availableTags.length; index++) {
        const element = availableTags[index];
        for (let index = 0; index < element.tags.length; index++) {
            const el = element.tags[index];
            availableTagsArray.push(el)
        }
    }
}

let filteredSuggestions = []
export const useFilterSuggestions = (param) => {

    //console.log(" availableTagsArray " + JSON.stringify(availableTagsArray))
    //console.log(" filtered suggestion param " + param)
    let index = availableTags.findIndex(obj => obj.id == param)
    //console.log(" index " + index)
    let temp = {}
    temp.id = param
    temp.tags = availableTags[index].tags.filter(tag => tag.name.toLowerCase().startsWith(tagInput.value.toLowerCase()));
    let index2 = filteredSuggestions.findIndex(obj => obj.id == temp.id)
    if (index2 == -1) {
        filteredSuggestions.push(temp)
    } else {
        filteredSuggestions[index2].tags = temp.tags
    }
    //console.log(" filteredSuggestions " + JSON.stringify(filteredSuggestions))
    return filteredSuggestions
}

export const useTradeTagsChange = async (param1, param2) => {
    console.log(" -> Type of trade tags change: " + param1)
    console.log(" -> Input added: " + JSON.stringify(param2))
    console.log(" -> Current pageId:", pageId.value);
    console.log(" -> Current tradeTagsId:", tradeTagsId.value);
    console.log(" -> Current tradeTagsDateUnix:", tradeTagsDateUnix.value);
    //console.log(" tags " + JSON.stringify(tags))

    if (param1 == "add") {

        //Case when arrow select and enter button
        if (selectedTagIndex.value != -1) {
            console.log(" -> Adding on arrow down and enter " + param2)

            let tradeTagsIndex = tradeTags.findIndex(obj => obj.id == filteredSuggestions[selectedTagIndex.value].id)

            //only add if does not exist in tradeTags already
            if (tradeTagsIndex == -1) {
                tradeTags.push(filteredSuggestions[selectedTagIndex.value]);
                tradeTagsChanged.value = true
                saveButton.value = true
                tagInput.value = ''; // Clear input after adding tag
                console.log(" -> Tag added successfully. tradeTagsChanged:", tradeTagsChanged.value);
            }

        } else if (param2) {

            let inputTextIndex = tradeTags.findIndex(obj => obj.name.toLowerCase() == param2.toLowerCase())
            console.log(" -> InputTextIndex " + inputTextIndex)

            //First check if input text already exists in trades tags ( = current array of tags)
            if (inputTextIndex != -1) {
                console.log("  --> Input text already exists in trades tags")
            } else {
                //Check if already in availableTags
                let inAvailableTagsIndex = availableTagsArray.findIndex(tag =>
                    tag.name.toLowerCase() == param2.toLowerCase())
                console.log("  --> InAvailableTagsIndex " + JSON.stringify(inAvailableTagsIndex))

                if (inAvailableTagsIndex != -1) {
                    console.log("  --> Input text already exists in availableTags")
                    tradeTags.push(availableTagsArray[inAvailableTagsIndex])
                    tradeTagsChanged.value = true
                    saveButton.value = true
                    console.log("  --> Tag added from available tags. tradeTagsChanged:", tradeTagsChanged.value);
                }
                else {
                    //Else new tag
                    console.log("  --> Input is a new tag")
                    let temp = {}



                    // Get the highest id number
                    const highestIdNumberAvailableTags = useFindHighestIdNumber(availableTags);
                    const highestIdNumberTradeTags = useFindHighestIdNumberTradeTags(tradeTags);

                    function chooseHighestNumber(num1, num2) {
                        return Math.max(num1, num2);
                    }

                    // Example usage:
                    const highestIdNumber = chooseHighestNumber(highestIdNumberAvailableTags, highestIdNumberTradeTags);

                    //console.log(" -> Highest tag id number " + highestIdNumber);

                    temp.id = "tag_" + (highestIdNumber + 1).toString()
                    temp.name = param2
                    tradeTags.push(temp)
                    tradeTagsChanged.value = true
                    saveButton.value = true
                    console.log("  --> New tag created and added. tradeTagsChanged:", tradeTagsChanged.value);

                    newTradeTags.push(temp)


                    tagInput.value = ''; // Clear input after adding tag
                }

            }
        }
        selectedTagIndex.value = -1
        showTagsList.value = false
        console.log(" -> TradeTags " + JSON.stringify(tradeTags))
    }
    if (param1 == "addFromDropdownMenu") {
        let index = tradeTags.findIndex(obj => obj.id == param2.id)
        //First check if input text already exists in trades tags ( = current array of tags)
        if (index == -1) {
            console.log(" -> Adding " + JSON.stringify(param2))
            tradeTags.push(param2);
            tradeTagsChanged.value = true
            saveButton.value = true
            tagInput.value = ''; // Clear input after adding tag
            console.log(" -> Tag added from dropdown. tradeTagsChanged:", tradeTagsChanged.value);
        }
        selectedTagIndex.value = -1
        showTagsList.value = false
        console.log(" -> TradeTags " + JSON.stringify(tradeTags))
    }

    if (param1 == "remove") {
        //param2 is index of element to remove inside tradeTags
        tradeTags.splice(param2, 1);
        tradeTagsChanged.value = true
        saveButton.value = true
        console.log(" -> Tag removed. tradeTagsChanged:", tradeTagsChanged.value);
    }


    // Handle different page types for setting tradeTagsId and tradeTagsDateUnix
    if (pageId.value == "daily") {
        //console.log(" itemTradeIndex.value " + itemTradeIndex.value)
        //console.log(" tradeIndex.value " + tradeIndex.value)
        tradeTagsDateUnix.value = filteredTrades[itemTradeIndex.value].dateUnix
        console.log(" tradeIndex.value " + tradeIndex.value)
        if (tradeIndex.value != undefined) {
            tradeTagsId.value = filteredTrades[itemTradeIndex.value].trades[tradeIndex.value].id
        } else {
            tradeTagsId.value = null // setting null so that when in useUpdateTags tradeTagsId is null / we're updating daily tags
        }
        console.log(" -> Updated tradeTagsId:", tradeTagsId.value);
        console.log(" -> Updated tradeTagsDateUnix:", tradeTagsDateUnix.value);
    }
    // Note: For other pages (like when using TradeDetailsModal), 
    // the tradeTagsId and tradeTagsDateUnix should already be set
    // in the processTradeData function of the modal

};

export const useFilterTags = () => {
    if (tagInput.value == '') selectedTagIndex.value = -1
    let showDropdownToReturn = tagInput.value !== '' && filteredSuggestions.length > 0
    //console.log("Filtered tags showDropdownToReturn " + showDropdownToReturn)
    showTagsList.value = showDropdownToReturn
};

export const useHandleKeyDown = (event) => {
    if (showTagsList.value) {
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            console.log("filteredSuggestions " + JSON.stringify(filteredSuggestions))
            selectedTagIndex.value = Math.min(selectedTagIndex.value + 1, filteredSuggestions.length - 1);
            //console.log(" arrow down and selectedTagIndex " + selectedTagIndex.value)
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            selectedTagIndex.value = Math.max(selectedTagIndex.value - 1, 0);
        }
    }
};

export const useToggleTagsDropdown = () => {
    selectedTagIndex.value = -1
    showTagsList.value = !showTagsList.value
}


export const useGetTagGroup = (param) => {
    const findGroupName = (tagId) => {
        for (let obj of availableTags) {
            for (let tag of obj.tags) {
                if (tag.id === tagId) {
                    return obj.name;
                }
            }
        }

        let name = null
        if (availableTags.length > 0) {
            name = availableTags.filter(obj => obj.id == "group_0")[0].name
        }
        return name // Return ungroupcolor if no result
    }

    const tagIdToFind = param;
    const groupName = findGroupName(tagIdToFind);

    return groupName
}

export const useResetTags = () => {
    tradeTags.splice(0);
}

export const useFindHighestIdNumber = (param) => {
    let highestId = -Infinity;
    if (param.length == 0) {
        highestId = 0
    } else {
        param.forEach(innerArray => {
            innerArray.tags.forEach(obj => {
                if (Number(obj.id.replace("tag_", "")) > highestId) {
                    highestId = Number(obj.id.replace("tag_", ""))
                }
            });
        });
    }
    return highestId;
}

export const useFindHighestIdNumberTradeTags = (param) => {
    let highestId = -Infinity;
    if (param.length == 0) {
        highestId = 0
    } else {
        param.forEach(obj => {
            if (Number(obj.id.replace("tag_", "")) > highestId) {
                highestId = Number(obj.id.replace("tag_", ""))
            }
        });
    }
    return highestId;
}

export const useUpdateTags = async () => {
    console.log("\nUPDATING OR SAVING TAGS");
    return new Promise(async (resolve, reject) => {
        try {
            spinnerSetups.value = true;
            // Create array of tag IDs
            let tagsArray = tradeTags.map(tag => tag.id);
            console.log(" -> Tags to save:", tagsArray);
            
            // Safety check - if no tags to save, just resolve
            if (!tagsArray.length) {
                console.log(" -> No tags to save, skipping update");
                spinnerSetups.value = false;
                resolve();
                return;
            }
            
            // Get current user
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                spinnerSetups.value = false;
                resolve();
                return;
            }
            
            spinnerSetupsText.value = "Updating";
            
            // Determine which ID to use based on the current page
            let tagData = {
                tags: tagsArray,
                dateUnix: null,
                tradeId: null
            };
            
            if (pageId.value === "addScreenshot") {
                tagData.dateUnix = screenshot.dateUnix;
                tagData.tradeId = screenshot.name;
                console.log(" -> Using screenshot data for tags:", tagData);
            } else if (pageId.value === "addDiary") {
                tagData.dateUnix = diaryUpdate.dateUnix;
                tagData.tradeId = diaryUpdate.dateUnix.toString();
                console.log(" -> Using diary data for tags:", tagData);
            } else {
                // Safety check for missing values
                if (!tradeTagsDateUnix.value) {
                    console.error(" -> Missing tradeTagsDateUnix value!");
                    spinnerSetups.value = false;
                    resolve();
                    return;
                }
                
                tagData.dateUnix = tradeTagsDateUnix.value;
                
                if (tradeTagsId.value) {
                    tagData.tradeId = tradeTagsId.value;
                } else {
                    // It's the case when changing daily tags
                    tagData.tradeId = tradeTagsDateUnix.value.toString();
                }
                console.log(" -> Using trade data for tags:", tagData);
            }
            
            // Final safety check - ensure we have a tradeId
            if (!tagData.tradeId) {
                console.error(" -> Missing tradeId for tag update!");
                spinnerSetups.value = false;
                resolve();
                return;
            }
            
            // Make the API call
            console.log(" -> Making API call to /api/updateTags with data:", tagData);
            const response = await axios.post('/api/updateTags', tagData);
            console.log(" -> API response:", response.data);
            
            console.log(' -> Updated tags successfully');
            spinnerSetups.value = false;
            resolve();
            
        } catch (error) {
            console.error('Failed to update tags:', error);
            console.error('Error details:', error.response ? error.response.data : 'No response data');
            spinnerSetups.value = false;
            resolve(); // Still resolve to avoid blocking the UI
        }
    });
}

export const useUpdateAvailableTags = async () => {
    console.log("\nUPDATING OR SAVING AVAILABLE TAGS");
    return new Promise(async (resolve, reject) => {
        try {
            // Get current user
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                resolve();
                return;
            }
            
            let tagsToUpdate = [];
            
            // If we're in registration flow, use all tags, otherwise just new tags
            const tagsToAdd = pageId.value === "registerSignup" ? tradeTags : newTradeTags;
            
            console.log(`Updating available tags with ${tagsToAdd.length} new tags`);
            
            try {
                // Get existing tags first
                const response = await axios.get('/api/availableTags');
                
                if (response.data && Array.isArray(response.data) && response.data.length > 0) {
                    // We have existing tags, find the ungrouped group
                    tagsToUpdate = [...response.data];
                    let ungroupedIndex = tagsToUpdate.findIndex(obj => obj.id === "group_0");
                    
                    if (ungroupedIndex === -1) {
                        // Create ungrouped group if it doesn't exist
                        ungroupedIndex = tagsToUpdate.length;
                        tagsToUpdate.push({
                            id: "group_0",
                            name: "Ungrouped",
                            color: "#6c757d",
                            tags: []
                        });
                    }
                    
                    // Add new tags to the ungrouped group if they don't already exist
                    for (const tag of tagsToAdd) {
                        if (!tagsToUpdate[ungroupedIndex].tags.some(t => t.id === tag.id)) {
                            tagsToUpdate[ungroupedIndex].tags.push(tag);
                            console.log(`  --> Adding new tag to available tags: ${tag.name}`);
                        } else {
                            console.log(`  --> Tag already exists in available tags: ${tag.name}`);
                        }
                    }
                } else {
                    // No existing tags, create structure with ungrouped group
                    tagsToUpdate = [{
                        id: "group_0",
                        name: "Ungrouped",
                        color: "#6c757d",
                        tags: [...tagsToAdd]
                    }];
                    console.log("  --> Creating new available tags structure");
                }
                
                // Save the updated tags
                await axios.post('/api/updateAvailableTags', { tags: tagsToUpdate });
                console.log(' -> Saved/Updated available tags successfully');
                
            } catch (error) {
                console.error('Failed to get or update available tags:', error);
            }
            
            resolve();
            
        } catch (error) {
            console.error('Error in useUpdateAvailableTags:', error);
            resolve(); // Still resolve to avoid blocking the UI
        }
    });
}

/****************************************$
 * 
 * NOTES 
 ****************************************/

export async function useGetNotes() {
    return new Promise(async (resolve, reject) => {
        console.log(" -> Getting Notes");
        notes.length = 0;
        
        try {
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                resolve();
                return;
            }
            
            let url = '/api/notes';
            const params = {};
            
            if (pageId.value === "diary") {
                params.limit = queryLimit.value;
            } else {
                let startD = selectedRange.value?.start || dayjs().startOf('month').unix();
                let endD = selectedRange.value?.end || dayjs().endOf('month').unix();
                
                // Ensure dates aren't identical (add 1 day if they are)
                if (startD === endD) {
                    endD = dayjs.unix(startD).add(1, 'day').endOf('day').unix();
                }
                
                params.startDate = startD;
                params.endDate = endD;
                params.limit = queryLimit.value;
            }
            
            const headers = {
                'Authorization': `Bearer ${AuthService.token}`
            };
            
            const response = await axios.get(url, { 
                params,
                headers
            });
            
            if (response.data && Array.isArray(response.data)) {
                response.data.forEach(element => {
                    notes.push(element);
                });
            }
            
        } catch (error) {
            console.error("Error getting notes:", error);
        }
        
        resolve();
    });
}

export const useUpdateNote = async () => {
    console.log("\nUPDATING OR SAVING NOTE");
    return new Promise(async (resolve, reject) => {
        try {
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                resolve();
                return;
            }
            
            // Prepare note data
            const noteData = {
                note: tradeNote.value,
                dateUnix: tradeNoteDateUnix.value,
                tradeId: tradeNoteId.value
            };
            
            // Make API call to update or create note
            const response = await axios.post('/api/updateNote', noteData);
            
            console.log(' -> Saved/Updated note successfully');
            saveButton.value = false;
            resolve();
            
        } catch (error) {
            console.error('Failed to update note:', error);
            resolve(); // Still resolve to avoid blocking the UI
        }
    });
}

export async function useGetAPIS() {
    return new Promise(async (resolve, reject) => {
        console.log(" -> Getting API keys");
        
        try {
            const currentUser = AuthService.getCurrentUser();
            if (!currentUser) {
                console.error("No user logged in");
                resolve();
                return;
            }
            
            const response = await axios.get('/api/apis', {
                headers: AuthService.getAuthHeaders()
            });
            
            if (response.data && Array.isArray(response.data)) {
                // Update the apis array in global store
                apis.length = 0;
                response.data.forEach(element => {
                    apis.push(element);
                });
            }
            
        } catch (error) {
            console.error("Error getting API keys:", error);
        }
        
        resolve();
    });
}

