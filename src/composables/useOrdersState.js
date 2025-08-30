import { ref, reactive, computed } from 'vue';

/**
 * Composable for managing orders reactive state
 */
export function useOrdersState() {
  // Loading states
  const priceLoading = ref(false);
  const saveLoading = ref(false);
  const loadLoading = ref(false);

  // Data state
  const currentPrices = reactive({});
  const ordersWithReasons = reactive({});
  const positionTypes = reactive({});
  const ordersWithCatalysts = reactive({});
  const expandedOrders = reactive({});

  // Computed properties for loading states
  const isLoading = computed(() => 
    priceLoading.value || saveLoading.value || loadLoading.value
  );

  const hasExpandedOrders = computed(() => 
    Object.keys(expandedOrders).some(key => expandedOrders[key])
  );

  // Methods for state management
  const setPriceLoading = (loading) => {
    priceLoading.value = loading;
  };

  const setSaveLoading = (loading) => {
    saveLoading.value = loading;
  };

  const setLoadLoading = (loading) => {
    loadLoading.value = loading;
  };

  const updateCurrentPrice = (symbol, priceData) => {
    currentPrices[symbol] = priceData;
  };

  const updateOrderReason = (orderId, completed) => {
    ordersWithReasons[orderId] = completed;
  };

  const updateOrderCatalyst = (orderId, catalyst) => {
    ordersWithCatalysts[orderId] = catalyst;
  };

  const updatePositionType = (symbol, isShort) => {
    positionTypes[symbol] = isShort;
  };

  const toggleOrderExpansion = (orderId) => {
    expandedOrders[orderId] = !expandedOrders[orderId];
  };

  const clearState = () => {
    Object.keys(currentPrices).forEach(key => delete currentPrices[key]);
    Object.keys(ordersWithReasons).forEach(key => delete ordersWithReasons[key]);
    Object.keys(positionTypes).forEach(key => delete positionTypes[key]);
    Object.keys(ordersWithCatalysts).forEach(key => delete ordersWithCatalysts[key]);
    Object.keys(expandedOrders).forEach(key => delete expandedOrders[key]);
  };

  return {
    // State
    priceLoading,
    saveLoading,
    loadLoading,
    currentPrices,
    ordersWithReasons,
    positionTypes,
    ordersWithCatalysts,
    expandedOrders,

    // Computed
    isLoading,
    hasExpandedOrders,

    // Methods
    setPriceLoading,
    setSaveLoading,
    setLoadLoading,
    updateCurrentPrice,
    updateOrderReason,
    updateOrderCatalyst,
    updatePositionType,
    toggleOrderExpansion,
    clearState
  };
}