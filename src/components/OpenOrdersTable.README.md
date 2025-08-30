# OpenOrdersTable.vue Component Documentation

## 1. Overview

`OpenOrdersTable.vue` is a high-level container component responsible for orchestrating the display and management of open trading orders. It does not render the main UI elements itself but instead delegates tasks to specialized child components.

Its primary role is to:
- Accept open order data from a parent component.
- Fetch and manage related data, such as real-time prices and saved order reasons.
- Perform complex calculations for risk, allocation, and potential profit.
- Pass the processed data and handler functions down to its children.
- Coordinate actions like refreshing prices or saving data to the database.

This component was refactored from a monolithic structure to improve modularity and maintainability.

## 2. Component Structure

The component follows the standard Vue 3 Single-File Component structure, using the Composition API (`<script>`).

- **`<template>` (View):**
  - Defines the layout and contains no complex logic.
  - It renders three primary child components, binding data and functions to them via props.

- **`<script>` (Logic):**
  - Contains all the business logic, state management, and data processing.
  - Uses the `setup` function to implement the Composition API.
  - Manages local reactive state (`reactive`), derived state (`computed`), and side effects (`watch`).

- **`<style scoped>` (Styling):**
  - Contains minimal, scoped CSS. Most styling is delegated to the child components to maintain encapsulation.

## 3. Child Components

The component delegates all rendering to these specialized children:

- **`OrderTableHeader.vue`**: Displays the header section, including control buttons (Refresh, Save, Load) and high-level summary metrics (e.g., total risk).
- **`NewPositionOrdersTable.vue`**: Renders the interactive table for orders that establish new positions. It handles the display of individual orders, their details, and user interactions.
- **`RiskSummary.vue`**: Displays a summary of key risk metrics at the bottom of the component.

## 4. Props

The component accepts the following main props from its parent:

- `openOrders: Array`: The primary list of open order objects.
- `accountBalance: Number`: The total account balance, used for allocation calculations.
- `stockHoldings: Array`: A list of current stock holdings, used to differentiate new position orders from exit orders.
- `holdingsStopLossRisk: Number`: The calculated stop-loss risk from existing holdings.
- `loading: Boolean`: A flag to indicate if the parent is loading data.

## 5. Emitted Events

The component communicates with its parent by emitting these events:

- `orders-updated`: Fired whenever there is a change to the orders list, allowing the parent to sync state.
- `refresh`: Fired when the user clicks the refresh button, signaling the parent to fetch fresh data.

## 6. Key Logic & Functions

All logic is contained within the `setup` function.

- **State Management:**
  - `reactive` objects are used to store local state that can change, such as `loadingState`, `currentPrices`, and `expandedOrders`.

- **Computed Properties (13 total):**
  - These are used to derive data from the props and reactive state. They are cached and update automatically.
  - **Order Processing:** `processedOrders`, `newPositionOrdersProcessed`, `newPositionsBySymbol`.
  - **Metric Calculation:** `totalStopLossRisk`, `totalRiskPercent`, `totalAllocationPercent`, `totalPotentialProfit`.

- **Functions (24 total):**
  - **Data Handlers:** `getPositionType`, `togglePositionType`, `isNewPositionOrder`.
  - **Event Handlers:** `handleRefreshPrices`, `handleOrderReasonUpdate`, `handleCatalystSelected`.
  - **Database Integration:** `saveOrdersToMongoDB`, `loadOrdersFromMongoDB` (which call the `orderTableService`).
  - **Calculation Wrappers:** A series of functions that wrap utility calculators (e.g., `getStopLossRisk`, `getPotentialProfit`) to provide them with the necessary reactive state.

- **Watchers (3 total):**
  - The component uses `watch` to react to changes in `props.openOrders` and `props.stockHoldings`.
  - When these props change, the watchers trigger functions to re-process the data, classify orders, and fetch any additional required information (like saved order reasons from the database).

## 7. How New and Existing Position Orders are Divided

The component intelligently separates orders into two categories: those that establish a **new position** and those that modify or exit an **existing position**. This logic is crucial for accurate risk and allocation calculations.

The core of this functionality resides in the `isNewPositionOrder` helper function, which follows these steps:

1.  **Explicit Property Check**: It first checks if an order object has an `isExitPositionOrder` property. This provides a direct way to classify an order.
2.  **Holdings Matching**: If the property is not present, the function uses the `holdingsMatchService.findMatchingHolding()` utility. This service compares the order's symbol and action against the `stockHoldings` array (provided as a prop).
3.  **Classification**:
    - If a matching holding is found (e.g., a `BUY` order for a stock you already own, or a `SELL` order for a stock you are long), the order is classified as an **existing position order**.
    - If no matching holding is found, it is classified as a **new position order**.

The computed properties `newPositionOrdersProcessed` and `exitPositionOrdersProcessed` then use this function to create the final, filtered lists of orders that are passed to the child components.

## 8. How Multiple Orders (Sub-Orders) are Calculated

To provide a clear and consolidated view of trading positions, the component groups multiple orders for the same symbol. This is handled by the `newPositionsBySymbol` computed property.

Here’s how it works:

1.  **Grouping by Symbol**: All orders classified as "new positions" are grouped into a map where each key is a stock symbol.
2.  **Identifying the Main Order**: Within each symbol group, one order is designated as the `mainOrder`. This is determined by the `detectIfMainOrder` utility, which typically identifies the primary limit order intended to open the position. All other orders for that same symbol are placed in a `subOrders` array.
3.  **Hierarchical Structure**: This creates a hierarchical data structure for each symbol, with a main order and its associated sub-orders (e.g., stop-loss, take-profit).
4.  **Main Order Promotion Logic**: The component includes robust logic to handle cases where the `mainOrder` is canceled. If a main order's status becomes `PendingCancel` or `Cancelled`, the system attempts to "promote" a new main order from the `subOrders` list. The sub-order with the largest quantity is typically chosen as the new main order, ensuring that the position's calculations remain accurate.
5.  **Calculations**: All final calculations for risk, profit, and allocation are performed on these symbol groups. Functions like `calculateTotalRisk` and `calculateTotalProfit` iterate through the `mainOrder` and `subOrders` within each group to compute the final, aggregated metrics displayed in the UI.
