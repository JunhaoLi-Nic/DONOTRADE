<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';

const props = defineProps({
  isOpen: Boolean,
  tradeId: String,
  symbol: String,
  orders: Array,
  loadingOrders: Boolean
});

const emit = defineEmits(['close', 'link-order']);

const popup = ref(null);

// Close popup when clicking outside
function handleClickOutside(event) {
  if (popup.value && !popup.value.contains(event.target)) {
    emit('close');
  }
}

// Link an order to the trade
function linkOrder(orderId) {
  emit('link-order', props.tradeId, orderId);
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleClickOutside);
});
</script>

<template>
  <div v-if="isOpen" class="order-popup-overlay">
    <div ref="popup" class="order-popup">
      <div class="order-popup-header">
        <h5>Link Order to Trade</h5>
        <button type="button" class="btn-close" @click="$emit('close')" aria-label="Close"></button>
      </div>
      
      <div class="order-popup-body">
        <p>Select an order to link to {{ symbol }} trade:</p>
        
        <!-- Loading indicator -->
        <div v-if="loadingOrders" class="text-center p-3">
          <div class="spinner-border" role="status"></div>
          <p class="mt-2">Loading orders...</p>
        </div>
        
        <!-- No orders message -->
        <div v-else-if="orders.length === 0" class="no-orders">
          <p>No matching orders found for {{ symbol }}</p>
        </div>
        
        <!-- Order list -->
        <div v-else class="order-list">
          <div 
            v-for="order in orders" 
            :key="order.orderId"
            @click="linkOrder(order.orderId)" 
            class="order-item"
          >
            <div class="order-details">
              <div class="order-main">
                <div class="order-symbol">{{ order.symbol }}</div>
                <div class="order-action">{{ order.action }} {{ order.totalQuantity }}</div>
              </div>
              <div class="order-price">@ {{ order.limitPrice || order.stopPrice }}</div>
            </div>
            <div class="order-id">ID: {{ order.orderId }}</div>
          </div>
        </div>
      </div>
      
      <div class="order-popup-footer">
        <button type="button" class="btn btn-secondary" @click="$emit('close')">Cancel</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.order-popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.order-popup {
  background-color: white;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.order-popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #e9ecef;
}

.order-popup-header h5 {
  margin: 0;
  font-weight: 600;
}

.order-popup-body {
  padding: 1rem;
  overflow-y: auto;
  flex-grow: 1;
}

.order-popup-footer {
  padding: 1rem;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: flex-end;
}

.order-list {
  max-height: 300px;
  overflow-y: auto;
}

.order-item {
  padding: 0.75rem;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.order-item:hover {
  background-color: #f8f9fa;
}

.order-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.order-main {
  display: flex;
  align-items: center;
}

.order-symbol {
  font-weight: 600;
  margin-right: 0.5rem;
  color: #495057
}

.order-action {
  color: #495057;
}

.order-price {
  font-weight: 500;
}

.order-id {
  font-size: 0.8rem;
  color: #6c757d;
  margin-top: 0.25rem;
}

.no-orders {
  text-align: center;
  padding: 2rem;
  color: #6c757d;
}
</style> 