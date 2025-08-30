<script setup>
import SideMenu from '../components/SideMenu.vue'
import Nav from '../components/Nav.vue'
import Screenshot from '../components/Screenshot.vue'
import ReturnToTopButton from '../components/ReturnToTopButton.vue'
import { onBeforeMount, onMounted, onBeforeUnmount, ref } from 'vue'
import { useInitParse, usePageId, useScreenType, useGetTimeZone, useGetPeriods, useInitPostHog, useCreatedDateFormat, useTimeFormat, useHourMinuteFormat } from '../utils/utils.js'
import { screenType, sideMenuMobileOut, screenshots, pageId, screenshot, selectedScreenshot, selectedScreenshotIndex, getMore } from '../stores/globals'
import { useSelectedScreenshotFunction } from '../utils/screenshots'

// Add state for sidebar collapsed
const sidebarCollapsed = ref(false);

// Function to handle sidebar toggle
const handleSidebarToggle = (event) => {
  sidebarCollapsed.value = event.detail.collapsed;
  // Update body class to help with content layout adjustments
  if (sidebarCollapsed.value) {
    document.body.classList.add('sidebar-collapsed');
  } else {
    document.body.classList.remove('sidebar-collapsed');
  }
};

/*========================================
  Functions used on all Dashboard components
========================================*/
onBeforeMount(async () => {
  usePageId()
  useInitParse()
  useGetTimeZone()
  useGetPeriods()
  useScreenType()
})

onMounted(() => {
  // Add event listener for sidebar toggle
  window.addEventListener('sidebar-toggle', handleSidebarToggle);
})

onBeforeUnmount(() => {
  // Remove event listener for sidebar toggle
  window.removeEventListener('sidebar-toggle', handleSidebarToggle);
})

useInitPostHog()
</script>
<template>
  <ReturnToTopButton />
  <div v-cloak class="container-fluid g-0">
    <div class="row g-0">
      <!-- Sidebar -->
      <div id="sideMenu" :class="['sidebar-column', {'collapsed': sidebarCollapsed}]">
        <SideMenu />
      </div>
      
      <!-- Main content area -->
      <div :class="['main-content', {'expanded': sidebarCollapsed}]">
        <div v-if="screenType === 'mobile' && sideMenuMobileOut" class="sideMenuMobileOut position-absolute" v-on:click="toggleMobileMenu"></div>
        <Nav />
        <main>
          <slot />
        </main>
      </div>
      <!--footer-->
    </div>
  </div>
  <!-- Modal -->
  <div class="modal fade" id="fullScreenModal" tabindex="-1" aria-labelledby="fullScreenModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-fullscreen">
      <div class="modal-content">
        <div class="modal-body">
          <Screenshot :index="selectedScreenshotIndex" source="fullScreen" :screenshot-data="selectedScreenshot" />
        </div>
        <div class="modal-footer">
          <!-- NEXT / PREVIOUS -->
          
            <div class="text-start">
              <button v-if="selectedScreenshotIndex - 1 >= 0" class="btn btn-outline-primary btn-sm ms-3 mb-2"
                v-on:click="useSelectedScreenshotFunction((selectedScreenshotIndex - 1), 'fullScreen')">
                <i class="fa fa-chevron-left me-2"></i></button>
            </div>
            <div v-if="selectedScreenshotIndex + 1 > 0 && screenshots[selectedScreenshotIndex + 1]"
              class="ms-auto text-end">
              <button class="btn btn-outline-primary btn-sm me-3 mb-2"
                v-on:click="useSelectedScreenshotFunction((selectedScreenshotIndex + 1), 'fullScreen')"
                :disabled="getMore"><span v-if="!getMore"><i class="fa fa-chevron-right ms-2"></i></span>
                <span v-else>
                  <div class="spinner-border spinner-border-sm" role="status">
                  </div>
                </span>
              </button>
            </div>
          
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sidebar-column {
  position: fixed;
  height: 100vh;
  width: 250px;
  transition: width 0.3s ease;
  z-index: 990; /* High but below navbar and dropdowns */
}

.sidebar-column.collapsed {
  width: 60px;
}

.main-content {
  margin-left: 250px;
  width: calc(100% - 250px);
  transition: margin-left 0.3s ease, width 0.3s ease;
  min-width: 0; /* Prevent flex items from overflowing */
  z-index: 1; /* Ensure main content is below the sidebar */
  position: relative;
}

.main-content.expanded {
  margin-left: 60px;
  width: calc(100% - 60px);
}

main {
  width: 100%;
  overflow-x: hidden; /* Prevent horizontal scrolling */
  position: relative;
  z-index: 1;
}

/* Mobile adjustments */
@media (max-width: 992px) {
  .sidebar-column {
    position: fixed;
    z-index: 1050;
  }
  
  .main-content {
    margin-left: 0;
    width: 100%;
  }
  
  .main-content.expanded {
    margin-left: 0;
    width: 100%;
  }
}
</style>