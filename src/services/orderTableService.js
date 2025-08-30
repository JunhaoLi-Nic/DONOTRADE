import { message } from 'ant-design-vue'
import orderSyncService from './orderSyncService'
import holdingsMatchService from './holdingsMatchService'

/**
 * Service for managing order table MongoDB operations
 * Handles saving, loading, and checking orders in MongoDB
 */
class OrderTableService {

  /**
   * Check for duplicate orders in MongoDB and load their checklists
   */
  async checkAndLoadOrdersFromMongoDB(processedOrders, ordersWithReasons, ordersWithCatalysts, openOrders, emit) {
    try {
      console.log('Checking MongoDB for existing orders and their checklists...')
      
      // First get all orders from MongoDB
      const storedOrders = await orderSyncService.fetchOrdersFromMongoDB()
      if (!storedOrders || storedOrders.length === 0) {
        console.log('No orders found in MongoDB to check against.')
        return
      }
      
      // Get all new position orders that need to be checked
      const newPositionOrders = processedOrders.filter(order => order.isMainOrder)
      if (newPositionOrders.length === 0) {
        console.log('No new position orders to check.')
        return
      }
      
      console.log(`Checking ${newPositionOrders.length} new position orders against ${storedOrders.length} MongoDB orders`)
      
      // For each new position order, check if it exists in MongoDB
      let matchedCount = 0
      for (const order of newPositionOrders) {
        // Check for matching orders in MongoDB
        const matchingOrders = storedOrders.filter(storedOrder => 
          storedOrder.symbol === order.symbol &&
          storedOrder.action === order.action &&
          storedOrder.orderType === order.orderType &&
          Math.abs(storedOrder.totalQuantity - order.totalQuantity) < 0.001
        )
        
        if (matchingOrders.length > 0) {
          // Sort by most recent first
          matchingOrders.sort((a, b) => new Date(b.savedAt || 0) - new Date(a.savedAt || 0))
          
          const latestMatch = matchingOrders[0]
          console.log(`Found matching order in MongoDB for ${order.symbol}:`, latestMatch)
          
          // If the matching order has reasonData, apply it to the current order
          if (latestMatch.reasonData) {
            console.log(`Applying checklist data from MongoDB to ${order.symbol}`)
            
            // Store the reason data in the local state
            ordersWithReasons[order.orderId] = true
            
            // Create a deep copy of the reasonData and assign directly to the order
            const reasonDataCopy = JSON.parse(JSON.stringify(latestMatch.reasonData))
            order.reasonData = reasonDataCopy
            order.reasonCompleted = true
            
            // Also update in the original orders array to ensure it persists
            const originalOrder = openOrders.find(o => o.orderId === order.orderId)
            if (originalOrder) {
              originalOrder.reasonData = reasonDataCopy
              originalOrder.reasonCompleted = true
              console.log(`Updated original order ${originalOrder.orderId} with reason data`)
            }
            
            // Store catalyst data if available
            if (latestMatch.catalystData) {
              const catalystDataCopy = JSON.parse(JSON.stringify(latestMatch.catalystData))
              ordersWithCatalysts[order.orderId] = catalystDataCopy
              order.catalystData = catalystDataCopy
              
              if (originalOrder) {
                originalOrder.catalystData = catalystDataCopy
              }
            }
            
            // Store tradeNoteId if available for future updates
            if (latestMatch.tradeNoteId || latestMatch.orderId) {
              // Store MongoDB ID to indicate this is an update, not a new order
              const mongoId = latestMatch.tradeNoteId || latestMatch.orderId
              order.mongoDbId = mongoId
              console.log(`Set mongoDbId to ${order.mongoDbId} for future reference`)
              
              if (originalOrder) {
                originalOrder.mongoDbId = mongoId
              }
            }
            
            matchedCount++
          }
        }
      }
      
      if (matchedCount > 0) {
        console.log(`Found and loaded checklists for ${matchedCount} orders from MongoDB`)
        // Force reactivity by emitting updated orders
        emit('orders-updated', [...openOrders])
      } else {
        console.log('No matching checklists found in MongoDB.')
      }
    } catch (error) {
      console.error('Error checking for duplicate orders:', error)
    }
  }

  /**
   * Save orders to MongoDB
   */
  async saveOrdersToMongoDB(processedOrders, getPositionType, setSaveLoading) {
    if (!processedOrders || processedOrders.length === 0) {
      message.warning('No orders to save')
      return
    }
    
    setSaveLoading(true)
    try {
      // Count main orders from new positions with strict filtering
      const mainNewPositionOrders = processedOrders.filter(order => {
        // Must be a main order
        if (!order.isMainOrder) {
          console.log(`${order.symbol}: Not a main order, skipping`)
          return false
        }
        
        // Must NOT be an exit position order
        if (order.isExitPositionOrder === true) {
          console.log(`${order.symbol}: Is an exit position order, skipping`)
          return false
        }
        
        // For new positions: BUY for long positions, SELL for short positions
        const isLongPosition = !getPositionType(order.symbol)
        const isBuyAction = order.action && order.action.toUpperCase() === 'BUY'
        const isSellAction = order.action && order.action.toUpperCase() === 'SELL'
        
        // Check if this is a valid new position order
        const isValidNewPosition = (isLongPosition && isBuyAction) || (!isLongPosition && isSellAction)
        
        console.log(`${order.symbol}: isLongPosition=${isLongPosition}, action=${order.action}, isValid=${isValidNewPosition}`)
        
        return isValidNewPosition
      })
      
      console.log(`Found ${mainNewPositionOrders.length} main orders from new positions to save:`)
      mainNewPositionOrders.forEach(order => {
        console.log(`- ${order.symbol} ${order.action} ${order.orderType}: ${order.totalQuantity} @ ${order.limitPrice || order.stopPrice}`)
        
        // Log MongoDB ID information
        if (order._id) {
          console.log(`  Has MongoDB _id: ${order._id}`)
        }
        if (order.mongoDbId) {
          console.log(`  Has mongoDbId: ${order.mongoDbId}`)
        }
        
        // Log reason data status
        if (order.reasonData) {
          console.log(`  Has reasonData: ${Object.keys(order.reasonData).length} fields`)
        }
      })
      
      if (mainNewPositionOrders.length === 0) {
        message.warning('No main orders from new positions to save')
        setSaveLoading(false)
        return
      }
      
      // Prepare orders for saving with all table column data
      const ordersToSave = mainNewPositionOrders.map(order => {
        // Ensure potential profit values are positive
        const potentialProfit = order.potentialProfit ? Math.abs(order.potentialProfit) : null
        const potentialProfitPercent = order.potentialProfitPercent ? Math.abs(order.potentialProfitPercent) : null
        
        // Calculate position value if not already present
        let positionValue = order.positionValue
        if (!positionValue && order.limitPrice && order.totalQuantity) {
          positionValue = order.limitPrice * order.totalQuantity
        }
        
        // Calculate allocation percent if not already present
        let allocationPercent = order.positionSizePercent || order.allocationPercent
        
        // Use MongoDB ID if available for updates
        const mongoDbId = order.mongoDbId || order._id
        
        return {
          ...order,
          orderId: order.tradeNoteId, // Use TradeNote ID as the MongoDB ID
          mongoDbId: mongoDbId, // Include mongoDbId if it exists for updates
          isExecutedOrder: true,
          timestamp: new Date(),
          // Mark as preorder for duplicate detection
          currentState: "preorder",
          // Ensure reasonCompleted is set if reasonData exists
          reasonCompleted: order.reasonData ? true : order.reasonCompleted,
          // Add source field to identify where this save came from
          source: 'table_save',
          // Ensure all table column data is included
          symbol: order.symbol,
          action: order.action,
          orderType: order.orderType,
          totalQuantity: order.totalQuantity,
          limitPrice: order.limitPrice,
          stopPrice: order.stopPrice,
          currentPrice: order.currentPrice,
          positionValue: positionValue,
          allocationPercent: allocationPercent,
          stopLossRisk: order.stopLossRisk,
          stopLossPercent: order.stopLossPercent,
          potentialProfit: potentialProfit,
          potentialProfitPercent: potentialProfitPercent,
          riskRewardRatio: order.riskRewardRatio,
          status: order.status
        }
      })
      
      // Save only main orders from new positions to MongoDB using the sync service
      const savedOrders = await orderSyncService.saveMainOrdersToMongoDB(ordersToSave)
      
      // Check the response from the server
      console.log('Response from server:', savedOrders)
      
      // Handle different response formats including duplicate preorder information
      if (savedOrders) {
        // Reset the highlight state on the save button
        const saveBtn = document.querySelector('.save-btn')
        if (saveBtn) {
          saveBtn.classList.remove('save-btn-highlight')
        }
        
        // Check if the response includes information about duplicate preorders
        if (typeof savedOrders === 'object' && savedOrders.message) {
          // Display the server's message directly
          message.success(savedOrders.message)
          
          // Additional console logging for debug
          console.log('Orders processed with results:', {
            inserted: savedOrders.inserted || 0,
            updated: savedOrders.updated || 0,
            duplicates: savedOrders.duplicates || 0
          })
        } else if (savedOrders.length > 0 || savedOrders.success === true) {
          // Legacy response format
          const count = savedOrders.length || savedOrders.count || 1
          message.success(`${count} main orders from new positions saved to MongoDB`)
          console.log('Orders saved:', savedOrders)
        } else if (savedOrders.duplicates && savedOrders.duplicates > 0) {
          // All orders were duplicates
          message.info(`All orders were duplicates, nothing saved to MongoDB`)
        } else {
          // No orders saved but request was successful
          message.info('No new orders were saved to MongoDB')
        }
      } else {
        message.warning('No response from server when saving orders')
      }
    } catch (error) {
      console.error('Full error saving to MongoDB:', error)
      message.error(`Failed to save orders: ${error.message || 'Unknown error'}`)
      if (error.response) {
        console.error('Error response:', error.response.data)
        message.error(`Server error: ${error.response.status} - ${error.response.statusText}`)
      }
    } finally {
      setSaveLoading(false)
    }
  }

  /**
   * Load orders from MongoDB
   */
  async loadOrdersFromMongoDB(ordersWithCatalysts, ordersWithReasons, positionTypes, getPositionType, fetchCurrentPrices, emit, setLoadLoading) {
    setLoadLoading(true)
    try {
      // Fetch orders from MongoDB using the sync service
      const storedOrders = await orderSyncService.fetchOrdersFromMongoDB()
      
      if (storedOrders && storedOrders.length > 0) {
        // Process stored orders
        storedOrders.forEach(order => {
          // Store the MongoDB ID for future reference
          if (order._id) {
            console.log(`Order ${order.symbol} loaded with MongoDB ID: ${order._id}`)
            // Ensure we keep the MongoDB ID for updates
            order.mongoDbId = order._id
          }
          
          // Store catalyst data in local state
          if (order.catalystData) {
            ordersWithCatalysts[order.tradeNoteId || order.orderId] = order.catalystData
          }
          
          // Store reason data in local state for checklist button state
          if (order.reasonData) {
            ordersWithReasons[order.tradeNoteId || order.orderId] = true
            // Ensure reasonCompleted is true if reasonData exists
            order.reasonCompleted = true
            
            // Log for debugging
            console.log(`Order ${order.symbol} has reason data:`, order.reasonData)
            console.log(`Setting reasonCompleted to true for order ${order.orderId || order.tradeNoteId}`)
          }
          
          // Restore position types
          if (order.positionType) {
            positionTypes[order.symbol] = order.positionType === 'short'
          }
          
          // Calculate stopLossRisk if missing - needed for risk management display
          if (!order.stopLossRisk && order.limitPrice && order.stopPrice && order.totalQuantity) {
            const isShort = order.positionType === 'short' || getPositionType(order.symbol)
            
            if (isShort) {
              // For short positions, risk is (stopPrice - limitPrice) * quantity (positive when stop > limit)
              order.stopLossRisk = (order.stopPrice - order.limitPrice) * order.totalQuantity
            } else {
              // For long positions, risk is (limitPrice - stopPrice) * quantity (negative value)
              order.stopLossRisk = (order.limitPrice - order.stopPrice) * order.totalQuantity * -1
            }
          }
        })
        
        // Set up parent-child relationships for orders
        const processedOrders = orderSyncService.setupOrderRelationships(storedOrders)
        
        // Fetch current prices for loaded orders
        const symbols = Array.from(new Set(processedOrders.map(order => order.symbol)))
        fetchCurrentPrices(symbols)
        
        // Emit orders to parent to update the state
        emit('orders-updated', processedOrders)
        message.success(`${processedOrders.length} orders loaded from MongoDB`)
      } else {
        message.info('No saved orders found in MongoDB')
      }
    } catch (error) {
      console.error('Full error loading from MongoDB:', error)
      message.error(`Failed to load orders: ${error.message || 'Unknown error'}`)
      if (error.response) {
        console.error('Error response:', error.response.data)
        message.error(`Server error: ${error.response.status} - ${error.response.statusText}`)
      }
    } finally {
      setLoadLoading(false)
    }
  }

  /**
   * Process orders watch handler
   */
  async processOrdersWatch(newOrders, oldOrders, positionTypes, stockHoldings, emit, checkAndLoadOrdersFromMongoDB) {
    if (!newOrders || newOrders.length === 0) return
    
    // Skip if the arrays are the same length and have the same order IDs
    // This prevents unnecessary updates that can trigger API call loops
    if (oldOrders && 
        newOrders.length === oldOrders.length && 
        JSON.stringify(newOrders.map(o => o.orderId).sort()) === 
        JSON.stringify(oldOrders.map(o => o.orderId).sort())) {
      console.log('Orders unchanged, skipping processing')
      return
    }
    
    try {
      // Process IBKR orders - add TradeNote IDs and match with MongoDB data
      // Pass stock holdings to help with identifying exit position orders
      const processedOrders = await orderSyncService.processIbkrOrders(
        newOrders, 
        positionTypes,
        stockHoldings
      )
      
      // Match orders with stock holdings to identify exit position orders
      const ordersWithHoldingInfo = holdingsMatchService.updateOrdersWithHoldingInfo(
        processedOrders, 
        stockHoldings
      )
      
      // Log information about order classification
      const newPositionCount = ordersWithHoldingInfo.filter(o => !o.isExitPositionOrder).length
      const exitPositionCount = ordersWithHoldingInfo.filter(o => o.isExitPositionOrder).length
      console.log(`Order classification: ${newPositionCount} new position orders, ${exitPositionCount} exit position orders`)
      
      // Only emit if we need to update the parent component
      // This is necessary for initial load but can cause loops if emitted too often
      if (!oldOrders) {
        console.log('Initial load - updating parent component')
        emit('orders-updated', ordersWithHoldingInfo)
      }
      
      // Check for duplicate orders in MongoDB and load their checklists
      await checkAndLoadOrdersFromMongoDB()
      
    } catch (error) {
      console.error('Error processing IBKR orders:', error)
    }
  }

  /**
   * Process stock holdings watch handler
   */
  processStockHoldingsWatch(newHoldings, processedOrders, emit) {
    if (newHoldings && newHoldings.length > 0 && processedOrders.length > 0) {
      // Re-classify orders based on updated holdings
      const updatedOrders = holdingsMatchService.updateOrdersWithHoldingInfo(
        processedOrders,
        newHoldings
      )
      
      // Update orders in parent component
      if (updatedOrders.length > 0) {
        emit('orders-updated', updatedOrders)
      }
    }
  }

  /**
   * Helper function to get order reason data from localStorage if needed
   */
  getOrderReasonData(orderId) {
    try {
      const storageKey = 'orderReasonData'
      const existingData = localStorage.getItem(storageKey)
      if (existingData) {
        const allReasonData = JSON.parse(existingData)
        return allReasonData[orderId] || null
      }
    } catch (error) {
      console.error('Error getting reason data from localStorage:', error)
    }
    return null
  }
}

// Export a singleton instance
export default new OrderTableService()