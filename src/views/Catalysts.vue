<template>
  <div class="content-container">
    <div class="page-title">
      <h1>Market Catalysts</h1>
    </div>
    
    <div class="card">
      <div class="card-body">
        <catalyst-manager />
      </div>
    </div>
  </div>
</template>

<script>
import { onMounted } from 'vue';
import { pageId } from '../stores/globals';
import CatalystManager from '../components/CatalystManager.vue';

export default {
  name: 'Catalysts',
  components: {
    CatalystManager
  },
  setup() {
    // Set pageId for sidebar highlighting
    pageId.value = 'catalysts';
    
    return {};
  }
}
</script>

<style scoped>
.content-container {
  padding: 20px;
  max-width: 100%;
  background-color: #121212;
  color: #e0e0e0;
  min-height: 100vh;
}

.page-title {
  margin-bottom: 20px;
  color: #ffffff;
}

.card {
  background-color: #1e1e1e;
  border-radius: 5px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
  margin-bottom: 20px;
  overflow: hidden;
  border: 1px solid #2a2a2a;
}

.card-body {
  padding: 20px;
  color: #e0e0e0;
}

/* Ensure the styles are consistent with other pages */
:deep(.nav-tabs) {
  border-bottom-color: #3a3a3a;
}

:deep(.nav-link) {
  color: #e0e0e0;
}

:deep(.nav-link.active) {
  background-color: transparent;
  border-color: #3a3a3a #3a3a3a #1e1e1e;
  color: #4a6cf7;
}

:deep(.tab-content) {
  background-color: #1e1e1e;
  color: #e0e0e0;
}

:deep(table) {
  color: #e0e0e0;
}

:deep(table thead th) {
  border-bottom-color: #3a3a3a;
  background-color: #2a2a2a;
}

:deep(table tbody td) {
  border-top-color: #3a3a3a;
}
</style> 