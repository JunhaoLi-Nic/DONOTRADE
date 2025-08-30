<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import axios from '../config/api';
import { ORDER_ENDPOINTS } from '../config/api';

const props = defineProps({
  orders: {
    type: Array,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  }
});

// State for MongoDB orders
const mongoDbOrders = ref([]);
const mongoDbLoading = ref(false);
const currentPage = ref(1);
const pageSize = ref(25);
const totalOrders = ref(0);

// Computed property to get all orders with checklist data
const ordersWithChecklist = computed(() => {
  // Combine orders from props and MongoDB
  const allOrders = [...props.orders, ...mongoDbOrders.value];
  
  return allOrders.filter(order => 
    order.reasonData && (
      order.reasonData.buyReason || 
      order.reasonData.timeframe || 
      order.reasonData.strategy || 
      order.reasonData.entryBasis || 
      order.reasonData.stopLoss || 
      order.reasonData.whatCanGoWrong
    )
  );
});

// Toggle expanded state for each order
const expandedOrders = ref({});

const toggleExpand = (orderId) => {
  expandedOrders.value[orderId] = !expandedOrders.value[orderId];
};

const isExpanded = (orderId) => {
  return !!expandedOrders.value[orderId];
};

// Fetch orders from MongoDB
const fetchOrders = async () => {
  try {
    mongoDbLoading.value = true;
    const skip = (currentPage.value - 1) * pageSize.value;
    
    const response = await axios.get(ORDER_ENDPOINTS.ORDERS, {
      params: {
        limit: pageSize.value,
        skip: skip
      }
    });
    
    // Filter orders that have reasonData
    mongoDbOrders.value = response.data.filter(order => 
      order.reasonData && (
        order.reasonData.buyReason || 
        order.reasonData.timeframe || 
        order.reasonData.strategy || 
        order.reasonData.entryBasis || 
        order.reasonData.stopLoss || 
        order.reasonData.whatCanGoWrong
      )
    );
    
    // Estimate total orders (this is approximate since we don't have a count endpoint)
    if (response.data.length === pageSize.value) {
      totalOrders.value = Math.max(totalOrders.value, skip + pageSize.value + 1);
    } else {
      totalOrders.value = skip + response.data.length;
    }
    
  } catch (error) {
    console.error('Error fetching orders from MongoDB:', error);
  } finally {
    mongoDbLoading.value = false;
  }
};

// Handle page change
const changePage = (page) => {
  currentPage.value = page;
  fetchOrders();
};

// Calculate total pages
const totalPages = computed(() => {
  return Math.ceil(totalOrders.value / pageSize.value);
});

// Generate page numbers for pagination
const pageNumbers = computed(() => {
  const pages = [];
  const maxVisiblePages = 5;
  
  if (totalPages.value <= maxVisiblePages) {
    // Show all pages if total pages is less than max visible pages
    for (let i = 1; i <= totalPages.value; i++) {
      pages.push(i);
    }
  } else {
    // Always show first page
    pages.push(1);
    
    // Calculate start and end of visible pages
    let start = Math.max(2, currentPage.value - 1);
    let end = Math.min(totalPages.value - 1, currentPage.value + 1);
    
    // Adjust if we're near the beginning or end
    if (currentPage.value <= 2) {
      end = Math.min(totalPages.value - 1, maxVisiblePages - 1);
    } else if (currentPage.value >= totalPages.value - 2) {
      start = Math.max(2, totalPages.value - maxVisiblePages + 2);
    }
    
    // Add ellipsis if needed
    if (start > 2) {
      pages.push('...');
    }
    
    // Add middle pages
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    
    // Add ellipsis if needed
    if (end < totalPages.value - 1) {
      pages.push('...');
    }
    
    // Always show last page
    pages.push(totalPages.value);
  }
  
  return pages;
});

// Watch for changes in orders prop
watch(() => props.orders, () => {
  // Re-fetch orders when props.orders changes
  fetchOrders();
}, { deep: true });

// Fetch orders on component mount
onMounted(() => {
  fetchOrders();
});
</script>

<template>
  <div class="order-checklist-table">
    <div v-if="mongoDbLoading && ordersWithChecklist.length === 0" class="text-center py-4">
      <i class="fa fa-spinner fa-spin me-2"></i>
      Loading order checklist...
    </div>
    
    <div v-else-if="ordersWithChecklist.length === 0" class="text-center py-4">
      <div class="empty-state">
        <i class="fa fa-clipboard-check fa-2x mb-3"></i>
        <h5>No order checklists available</h5>
        <p>Create new orders with checklist data to see them here.</p>
      </div>
    </div>
    
    <div v-else class="table-responsive">
      <table class="table">
        <thead>
          <tr>
            <th></th>
            <th>Symbol</th>
            <th>Action</th>
            <th>Reason</th>
            <th>Timeframe</th>
            <th>Strategy</th>
            <th>Entry Basis</th>
            <th>Stop Loss</th>
            <th>Risk/Reward</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="order in ordersWithChecklist" :key="order.orderId">
            <!-- Main row -->
            <tr :class="{ 'expanded': isExpanded(order.orderId) }">
              <td>
                <button 
                  class="btn btn-sm btn-outline-secondary expand-btn"
                  @click="toggleExpand(order.orderId)"
                >
                  <i :class="isExpanded(order.orderId) ? 'fa fa-chevron-down' : 'fa fa-chevron-right'"></i>
                </button>
              </td>
              <td>{{ order.symbol }}</td>
              <td>{{ order.action }}</td>
              <td>{{ order.reasonData?.buyReason ? order.reasonData.buyReason.substring(0, 30) + (order.reasonData.buyReason.length > 30 ? '...' : '') : '-' }}</td>
              <td>{{ order.reasonData?.timeframe || '-' }}</td>
              <td>{{ order.reasonData?.strategy || '-' }}</td>
              <td>{{ order.reasonData?.entryBasis ? order.reasonData.entryBasis.substring(0, 30) + (order.reasonData.entryBasis.length > 30 ? '...' : '') : '-' }}</td>
              <td>{{ order.reasonData?.stopLoss ? order.reasonData.stopLoss.substring(0, 30) + (order.reasonData.stopLoss.length > 30 ? '...' : '') : '-' }}</td>
              <td>{{ order.riskRewardRatio ? `1:${order.riskRewardRatio.toFixed(2)}` : '-' }}</td>
            </tr>
            
            <!-- Expanded details row -->
            <tr v-if="isExpanded(order.orderId)" class="details-row">
              <td colspan="9">
                <div class="order-details">
                  <div class="detail-section">
                    <h6>My reason for buying this stock is:</h6>
                    <p>{{ order.reasonData?.buyReason || 'Not specified' }}</p>
                  </div>
                  
                  <div class="detail-section">
                    <h6>Expected timeframe for this trade:</h6>
                    <p>{{ 
                      order.reasonData?.timeframe === 'short-term' ? 'Short-term (1-5 days)' :
                      order.reasonData?.timeframe === 'swing' ? 'Swing (1-3 weeks)' :
                      order.reasonData?.timeframe === 'position' ? 'Medium-term' :
                      order.reasonData?.timeframe || 'Not specified'
                    }}</p>
                  </div>
                  
                  <div class="detail-section">
                    <h6>My trading strategy is:</h6>
                    <p>{{ 
                      order.reasonData?.strategy === 'pullback' ? 'Pullback Entry' :
                      order.reasonData?.strategy === 'breakout' ? 'Breakout Entry' :
                      order.reasonData?.strategy === 'vcp' ? 'VCP' :
                      order.reasonData?.strategy === 'reversal' ? 'ICT Reversal' :
                      order.reasonData?.strategy || 'Not specified'
                    }}</p>
                  </div>
                  
                  <div class="detail-section">
                    <h6>My entry point is based on:</h6>
                    <p>{{ order.reasonData?.entryBasis || 'Not specified' }}</p>
                  </div>
                  
                  <div class="detail-section">
                    <h6>My stop loss is set at:</h6>
                    <p>{{ order.reasonData?.stopLoss || 'Not specified' }}</p>
                  </div>
                  
                  <div class="detail-section">
                    <h6>What can go wrong with this trade:</h6>
                    <p>{{ order.reasonData?.whatCanGoWrong || 'Not specified' }}</p>
                  </div>
                  
                  <div class="detail-section">
                    <h6>The catalyst/driver for this stock is:</h6>
                    <p>{{ order.reasonData?.catalysts || 'Not specified' }}</p>
                  </div>
                  
                  <div class="detail-section">
                    <h6>Sector:</h6>
                    <p>{{ order.reasonData?.sector || 'Not specified' }}</p>
                  </div>
                  
                  <div class="detail-section">
                    <h6>Position size:</h6>
                    <p>{{ order.reasonData?.positionSize ? order.reasonData.positionSize + '%' : 'Not specified' }}</p>
                  </div>
                  
                  <div class="detail-section">
                    <h6>Risk/Reward ratio:</h6>
                    <p>{{ order.riskRewardRatio ? `1:${order.riskRewardRatio.toFixed(2)}` : 'Not specified' }}</p>
                  </div>
                  
                  <div class="detail-section">
                    <h6>Can I accept this loss calmly?</h6>
                    <p>{{ order.reasonData?.checkAcceptLoss === true ? 'Yes' : order.reasonData?.checkAcceptLoss === false ? 'No' : 'Not specified' }}</p>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      
      <!-- Pagination -->
      <div class="pagination-container" v-if="totalPages > 1">
        <nav aria-label="Order checklist pagination">
          <ul class="pagination">
            <li class="page-item" :class="{ disabled: currentPage === 1 }">
              <a class="page-link" href="#" @click.prevent="currentPage > 1 && changePage(currentPage - 1)">
                <i class="fa fa-chevron-left"></i>
              </a>
            </li>
            
            <li 
              v-for="page in pageNumbers" 
              :key="page"
              class="page-item" 
              :class="{ active: page === currentPage, disabled: page === '...' }"
            >
              <a 
                class="page-link" 
                href="#" 
                @click.prevent="page !== '...' && changePage(page)"
              >
                {{ page }}
              </a>
            </li>
            
            <li class="page-item" :class="{ disabled: currentPage === totalPages || totalPages === 0 }">
              <a class="page-link" href="#" @click.prevent="currentPage < totalPages && changePage(currentPage + 1)">
                <i class="fa fa-chevron-right"></i>
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </div>
  </div>
</template>

<style scoped>
.order-checklist-table {
  width: 100%;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: #6c757d;
}

.expand-btn {
  padding: 0.25rem 0.5rem;
  background: transparent;
  border: none;
}

.expand-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

tr.expanded {
  background-color: rgba(255, 255, 255, 0.05);
}

.details-row {
  background-color: rgba(255, 255, 255, 0.02);
}

.order-details {
  padding: 1rem;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.detail-section {
  margin-bottom: 0.5rem;
}

.detail-section h6 {
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
  color: #adb5bd;
}

.detail-section p {
  margin: 0;
  font-size: 0.95rem;
  white-space: pre-wrap;
}

/* Pagination styles */
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 1rem;
}

.pagination {
  display: flex;
  list-style: none;
  padding: 0;
  margin: 0;
}

.page-item {
  margin: 0 0.25rem;
}

.page-link {
  display: block;
  padding: 0.5rem 0.75rem;
  color: #4a6cf7;
  background-color: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 0.25rem;
  text-decoration: none;
  transition: background-color 0.2s;
}

.page-link:hover {
  background-color: #3a3a3a;
}

.page-item.active .page-link {
  background-color: #4a6cf7;
  color: #fff;
  border-color: #4a6cf7;
}

.page-item.disabled .page-link {
  color: #6c757d;
  pointer-events: none;
  background-color: #2a2a2a;
  border-color: #3a3a3a;
}

@media (max-width: 768px) {
  .order-details {
    grid-template-columns: 1fr;
  }
}
</style> 