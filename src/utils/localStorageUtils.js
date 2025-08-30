/**
 * Utility functions for managing order checklist and catalyst data in localStorage
 */

const CHECKLIST_STORAGE_KEY = 'orderChecklists';
const CATALYST_STORAGE_KEY = 'orderCatalysts';

/**
 * Save order checklist data to localStorage
 * @param {string} orderId - ID of the order
 * @param {boolean} completed - Whether the checklist is completed
 * @param {object} reasonData - Checklist reason data
 * @returns {boolean} - Success status
 */
export const saveOrderChecklistToLocalStorage = (orderId, completed, reasonData) => {
  try {
    // Get existing data or initialize as empty object
    const existingData = localStorage.getItem(CHECKLIST_STORAGE_KEY) 
      ? JSON.parse(localStorage.getItem(CHECKLIST_STORAGE_KEY)) 
      : {};
    
    // Update with new data
    existingData[orderId] = {
      completed,
      reasonData,
      timestamp: new Date().toISOString()
    };
    
    // Save back to localStorage
    localStorage.setItem(CHECKLIST_STORAGE_KEY, JSON.stringify(existingData));
    console.log('Order checklist saved to localStorage:', orderId);
    return true;
  } catch (error) {
    console.error('Error saving order checklist to localStorage:', error);
    return false;
  }
};

/**
 * Save order catalyst data to localStorage
 * @param {string} orderId - ID of the order
 * @param {object} catalyst - Catalyst data
 * @returns {boolean} - Success status
 */
export const saveOrderCatalystToLocalStorage = (orderId, catalyst) => {
  try {
    // Get existing data or initialize as empty object
    const existingData = localStorage.getItem(CATALYST_STORAGE_KEY) 
      ? JSON.parse(localStorage.getItem(CATALYST_STORAGE_KEY)) 
      : {};
    
    // Update with new data
    existingData[orderId] = {
      catalyst,
      timestamp: new Date().toISOString()
    };
    
    // Save back to localStorage
    localStorage.setItem(CATALYST_STORAGE_KEY, JSON.stringify(existingData));
    console.log('Order catalyst saved to localStorage:', orderId);
    return true;
  } catch (error) {
    console.error('Error saving order catalyst to localStorage:', error);
    return false;
  }
};

/**
 * Load order checklists from localStorage
 * @returns {object|null} - Object with orderId keys and checklist data values, or null if error
 */
export const loadOrderChecklistsFromLocalStorage = () => {
  try {
    const data = localStorage.getItem(CHECKLIST_STORAGE_KEY);
    return data ? JSON.parse(data) : {};
  } catch (error) {
    console.error('Error loading order checklists from localStorage:', error);
    return null;
  }
};

/**
 * Load order catalysts from localStorage
 * @returns {object|null} - Object with orderId keys and catalyst data values, or null if error
 */
export const loadOrderCatalystsFromLocalStorage = () => {
  try {
    const data = localStorage.getItem(CATALYST_STORAGE_KEY);
    return data ? JSON.parse(data) : {};
  } catch (error) {
    console.error('Error loading order catalysts from localStorage:', error);
    return null;
  }
};

/**
 * Clear all order data from localStorage after MongoDB save
 * @returns {boolean} - Success status
 */
export const clearOrderDataFromLocalStorage = () => {
  try {
    localStorage.removeItem(CHECKLIST_STORAGE_KEY);
    localStorage.removeItem(CATALYST_STORAGE_KEY);
    console.log('Cleared checklist and catalyst data from localStorage');
    return true;
  } catch (error) {
    console.error('Error clearing order data from localStorage:', error);
    return false;
  }
};

/**
 * Apply localStorage data to orders state
 * @param {object} ordersWithReasons - State object to update with reason data
 * @param {object} ordersWithCatalysts - State object to update with catalyst data
 * @param {array} openOrders - Array of open orders to update with reason data
 * @returns {boolean} - Whether any data was loaded
 */
export const applyLocalStorageToOrdersState = (ordersWithReasons, ordersWithCatalysts, openOrders = []) => {
  try {
    let dataLoaded = false;
    
    const checklistData = loadOrderChecklistsFromLocalStorage();
    if (checklistData) {
      Object.keys(checklistData).forEach(orderId => {
        const data = checklistData[orderId];
        if (data.completed) {
          ordersWithReasons[orderId] = data.completed;
          dataLoaded = true;
          
          // Also update the order object with the complete reasonData
          // This ensures the form can open in view/edit mode
          const orderToUpdate = openOrders.find(
            order => (order.tradeNoteId === orderId) || (order.orderId === orderId)
          );
          
          if (orderToUpdate) {
            orderToUpdate.reasonData = data.reasonData;
            orderToUpdate.reasonCompleted = data.completed;
            console.log(`Updated order ${orderId} with reason data from localStorage`);
          }
        }
      });
      console.log('Applied checklist data from localStorage to state');
    }
    
    const catalystData = loadOrderCatalystsFromLocalStorage();
    if (catalystData) {
      Object.keys(catalystData).forEach(orderId => {
        const data = catalystData[orderId];
        if (data.catalyst) {
          ordersWithCatalysts[orderId] = data.catalyst;
          dataLoaded = true;
          
          // Also update the order object with the catalyst data
          const orderToUpdate = openOrders.find(
            order => (order.tradeNoteId === orderId) || (order.orderId === orderId)
          );
          
          if (orderToUpdate) {
            orderToUpdate.catalystData = data.catalyst;
            console.log(`Updated order ${orderId} with catalyst data from localStorage`);
          }
        }
      });
      console.log('Applied catalyst data from localStorage to state');
    }
    
    return dataLoaded;
  } catch (error) {
    console.error('Error applying localStorage data to orders state:', error);
    return false;
  }
}; 