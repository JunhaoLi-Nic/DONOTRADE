<template>
  <div>
    <a-button 
      type="text" 
      size="small" 
      @click="isModalVisible = true"
      class="catalyst-btn"
    >
      <template #icon><file-text-outlined /></template>
      {{ currentCatalyst ? 'Change Catalyst' : 'Select Catalyst' }}
    </a-button>
    
    <a-modal
      title="Select Market Catalyst"
      :open="isModalVisible"
      @cancel="closeModal"
      :footer="null"
      width="600"
      class="dark-modal"
    >
      <div v-if="isCreatingNew">
        <catalyst-checklist
          :visible="true"
          :onClose="() => isCreatingNew = false"
          :onSave="handleCatalystSave"
          :initialData="undefined"
        />
      </div>
      <div v-else>
        <div style="margin-bottom: 16px">
          <a-typography-text class="dark-text">Select a catalyst for {{ symbol }}:</a-typography-text>
        </div>
        
        <div v-if="loading" style="text-align: center; padding: 20px">
          <a-spin />
          <div style="margin-top: 8px">
            <a-typography-text type="secondary" class="dark-text-secondary">Loading catalysts...</a-typography-text>
          </div>
        </div>
        <div v-else-if="catalysts.length > 0">
          <div>
            <a-select 
              style="width: 100%; margin-bottom: 16px"
              placeholder="Select a catalyst"
              @change="handleSelectChange"
              :defaultValue="currentCatalyst?.keyFact"
              class="dark-select"
            >
              <a-select-option 
                v-for="(catalyst, index) in catalysts" 
                :key="index" 
                :value="catalyst.keyFact"
              >
                <a-tooltip :title="catalyst.keyFact">
                  {{ catalyst.keyFact.length > 50 ? `${catalyst.keyFact.substring(0, 50)}...` : catalyst.keyFact }}
                </a-tooltip>
              </a-select-option>
            </a-select>
            
            <a-card v-if="selectedCatalyst" size="small" style="margin-bottom: 16px" class="dark-card">
              <a-typography-text strong class="dark-text">{{ selectedCatalyst.keyFact }}</a-typography-text>
              <div style="margin-top: 8px">
                <a-space>
                  <a-tag :color="getImportanceColor(selectedCatalyst.importance)">
                    {{ selectedCatalyst.importance.toUpperCase() }}
                  </a-tag>
                  <a-tag :color="getExpectationColor(selectedCatalyst.actualVsExpectation)">
                    {{ getExpectationText(selectedCatalyst.actualVsExpectation) }}
                  </a-tag>
                </a-space>
              </div>
            </a-card>
            
            <div style="display: flex; justify-content: space-between">
              <a-button @click="isCreatingNew = true" class="dark-button">
                Create New Catalyst
              </a-button>
              <a-button 
                type="primary" 
                :disabled="!selectedCatalyst"
                @click="selectAndClose"
              >
                Select
              </a-button>
            </div>
          </div>
        </div>
        <div v-else>
          <a-empty 
            description="No relevant catalysts found for this symbol" 
            style="margin-bottom: 16px"
            class="dark-empty"
          />
          <a-button 
            type="primary" 
            @click="isCreatingNew = true"
          >
            Create New Catalyst
          </a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script>
import { defineComponent, ref, watch, onMounted } from 'vue';
import { Button, Modal, Select, Spin, Empty, Card, Tag, Space, Tooltip, message, Typography } from 'ant-design-vue';
import { FileTextOutlined } from '@ant-design/icons-vue';
import axios from 'axios';
import CatalystChecklist from './CatalystChecklist.vue';

export default defineComponent({
  name: 'CatalystSelector',
  components: {
    AButton: Button,
    AModal: Modal,
    ASelect: Select,
    ASelectOption: Select.Option,
    ASpin: Spin,
    AEmpty: Empty,
    ACard: Card,
    ATag: Tag,
    ASpace: Space,
    ATooltip: Tooltip,
    ATypographyText: Typography.Text,
    FileTextOutlined,
    CatalystChecklist
  },
  props: {
    symbol: String,
    onCatalystSelected: Function,
    currentCatalyst: Object
  },
  setup(props, { emit }) {
    const isModalVisible = ref(false);
    const catalysts = ref([]);
    const loading = ref(false);
    const selectedCatalyst = ref(props.currentCatalyst);
    const isCreatingNew = ref(false);

    const loadCatalysts = async () => {
      loading.value = true;
      try {
        const response = await axios.get('/api/catalysts');
        const allCatalysts = response.data;
        catalysts.value = allCatalysts.filter(c =>
          c.relatedSymbols?.includes(props.symbol) ||
          c.keyFact?.toLowerCase().includes(props.symbol.toLowerCase()) ||
          c.currentMarketTheme?.toLowerCase().includes(props.symbol.toLowerCase())
        );
      } catch (error) {
        console.error('Error loading catalysts from API, falling back to localStorage', error);
        try {
          const storedCatalysts = localStorage.getItem('marketCatalysts');
          if (storedCatalysts) {
            const allCatalysts = JSON.parse(storedCatalysts);
            catalysts.value = allCatalysts.filter(c =>
              c.relatedSymbols?.includes(props.symbol) ||
              c.keyFact?.toLowerCase().includes(props.symbol.toLowerCase()) ||
              c.currentMarketTheme?.toLowerCase().includes(props.symbol.toLowerCase())
            );
          }
        } catch (localError) {
          console.error('Error loading catalysts from localStorage:', localError);
        }
      } finally {
        loading.value = false;
      }
    };

    const handleCatalystSave = async (catalyst) => {
      loading.value = true;
      if (!catalyst.relatedSymbols) {
        catalyst.relatedSymbols = [];
      }
      if (!catalyst.relatedSymbols.includes(props.symbol)) {
        catalyst.relatedSymbols.push(props.symbol);
      }

      try {
        await axios.post('/api/catalysts', catalyst);
        selectedCatalyst.value = catalyst;
        updateLocalStorage(catalyst);
        props.onCatalystSelected(catalyst);
        message.success('New catalyst created and saved');
      } catch (error) {
        console.error('Error saving catalyst to API, saving to localStorage', error);
        updateLocalStorage(catalyst);
        props.onCatalystSelected(catalyst);
        message.success('Catalyst saved locally (API connection failed)');
      } finally {
        loading.value = false;
        isCreatingNew.value = false;
        isModalVisible.value = false;
      }
    };
    
    const updateLocalStorage = (catalyst) => {
        try {
            const storedCatalysts = localStorage.getItem('marketCatalysts');
            let allCatalysts = storedCatalysts ? JSON.parse(storedCatalysts) : [];
            allCatalysts.push(catalyst);
            localStorage.setItem('marketCatalysts', JSON.stringify(allCatalysts));
        } catch (localError) {
            console.error('Error saving to localStorage:', localError);
        }
    };

    const handleSelectChange = (value) => {
      selectedCatalyst.value = catalysts.value.find(c => c.keyFact === value);
    };
    
    const selectAndClose = () => {
        if (selectedCatalyst.value) {
            props.onCatalystSelected(selectedCatalyst.value);
            isModalVisible.value = false;
        }
    };
    
    const closeModal = () => {
        isModalVisible.value = false;
        isCreatingNew.value = false;
    };

    watch(isModalVisible, (visible) => {
      if (visible) {
        loadCatalysts();
      }
    });

    onMounted(loadCatalysts);
    
    const getImportanceColor = (importance) => {
        if (importance === 'high') return 'red';
        if (importance === 'medium') return 'orange';
        return 'green';
    };

    const getExpectationColor = (expectation) => {
        if (expectation === 'exceeded') return 'green';
        if (expectation === 'missed') return 'red';
        return 'blue';
    };

    const getExpectationText = (expectation) => {
        if (expectation === 'exceeded') return 'Exceeded';
        if (expectation === 'missed') return 'Missed';
        return 'Met';
    };

    return {
      isModalVisible,
      catalysts,
      loading,
      selectedCatalyst,
      isCreatingNew,
      closeModal,
      handleCatalystSave,
      handleSelectChange,
      selectAndClose,
      getImportanceColor,
      getExpectationColor,
      getExpectationText
    };
  }
});
</script>

<style scoped>
.catalyst-btn {
  background-color: transparent;
  border: 1px solid #4a6cf7;
  color: #4a6cf7;
  font-size: 12px;
  padding: 4px 8px;
  height: auto;
  line-height: 1.2;
}

.catalyst-btn:hover {
  background-color: rgba(74, 108, 247, 0.1);
  border-color: #3a5cd8;
  color: #3a5cd8;
}

.dark-modal :deep(.ant-modal-content) {
  background-color: #1c1c1c !important;
  border: 1px solid #303030;
  width: 100%;
}

.dark-modal :deep(.ant-modal-header) {
  background-color: #1c1c1c !important;
  border-bottom: 1px solid #303030;
}

.dark-modal :deep(.ant-modal-title) {
  color: #e0e0e0;
}

.dark-modal :deep(.ant-modal-close) {
  color: #e0e0e0;
}

.dark-modal :deep(.ant-modal-body) {
  background-color: #1c1c1c !important;
  color: #e0e0e0;
}

.dark-text {
  color: #e0e0e0;
}

.dark-text-secondary {
  color: #a0a0a0;
}

.dark-card {
  background-color: #262626 !important;
  border: 1px solid #303030;
}

.dark-card :deep(.ant-card-body) {
  background-color: #262626 !important;
}

.dark-select :deep(.ant-select-selector) {
  background-color: #262626 !important;
  border-color: #303030 !important;
  color: #e0e0e0;
}

.dark-select :deep(.ant-select-arrow) {
  color: #e0e0e0;
}

.dark-select :deep(.ant-select-dropdown) {
  background-color: #262626 !important;
  color: #e0e0e0;
}

.dark-select :deep(.ant-select-item) {
  color: #e0e0e0;
}

.dark-button {
  background-color: #4a6cf7 !important;
  border-color: #4a6cf7 !important;
  color: #ffffff !important;
}

.dark-button:hover {
  background-color: #3a5cd8 !important;
  border-color: #3a5cd8 !important;
  color: #ffffff !important;
}

.dark-empty :deep(.ant-empty-description) {
  color: #a0a0a0;
}
</style> 