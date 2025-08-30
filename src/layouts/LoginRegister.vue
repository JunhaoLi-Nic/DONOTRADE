<script setup>
// Import Vue lifecycle hooks
import { onBeforeMount, onMounted } from 'vue';
// Import utility functions for initialization and page tracking
import { useInitParse, useInitPostHog, usePageId } from '../utils/utils.js'

// Import axios for HTTP requests
import axios from 'axios'

// Run before the component is mounted
onBeforeMount(async () => {
  // Set the current page ID (for analytics or state)
  usePageId()
  // Fetch Parse App ID from backend and store in localStorage
  await getParseId()
  // Initialize Parse backend SDK
  await useInitParse()
})

// Run after the component is mounted (currently empty, but reserved for future use)
onMounted(async () => {
  // No logic here yet
})

// Initialize PostHog analytics (runs immediately)
useInitPostHog()

// Helper function to get Parse App ID from backend and store in localStorage
async function getParseId() {
  return new Promise((resolve, reject) => {
    console.log("\nGETTING APP ID")
    axios.post('/api/parseAppId')
      .then((response) => {
        // Store the received Parse App ID in localStorage
        const appId = response.data.toString();
        localStorage.setItem('parse_app_id', appId);
        console.log("  --> App id in localstorage: " + appId);
        resolve()
      })
      .catch((error) => {
        // Log error if request fails
        console.log(" -> Error getting app id " + error)
        reject(error)
      });
  })
}
</script>
<template>
  <header class="text-center">
    <!-- Fixed navbar -->
    <img class="navLogo" />
  </header>
  <slot />
</template>