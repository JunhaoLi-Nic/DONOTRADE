<script setup>
import { onBeforeMount, onMounted, ref, onBeforeUnmount } from 'vue';
import { selectedBroker, spinnerLoadingPage, brokers, stepper, executions, currentUser, uploadMfePrices, existingImports, queryLimit, blotter, pAndL, gotExistingTradesArray, existingTradesArray, brokerData, tradovateTiers, selectedTradovateTier, deviceTimeZone, timeZoneTrade } from '../stores/globals';
import { useCheckCloudPayment, useDecimalsArithmetic } from '../utils/utils';
import { useImportTrades, useGetExistingTradesArray, useUploadTrades } from '../utils/addTrades'
import { useCreatedDateFormat, useDateCalFormat, useGetCurrentUser } from '../utils/utils';
import SpinnerLoadingPage from '../components/SpinnerLoadingPage.vue';
import ApiDebugConsole from '../components/ApiDebugConsole.vue';
import { DirectUpload } from '../utils/direct-upload.js';

spinnerLoadingPage.value = false

// Timezone handling
const showTimezoneConfirmation = ref(false);
const fileTimezone = ref('America/New_York'); // Default or detected from file
const selectedTimezone = ref(timeZoneTrade.value);
const csvDateTimeFormat = ref('YYYYMMDD;HHMMSS'); // Default format

// Add reactive refs for local trades count and upload status
const localTradesCount = ref(0);
const uploadStatus = ref(null);

onBeforeMount(async () => {
        
})

onMounted(async () => {
    await useGetExistingTradesArray()
    await useGetCurrentUser()
    
    // Check for local trades
    checkLocalTrades();
    
    // Set up interval to check for local trades
    const interval = setInterval(checkLocalTrades, 5000);
    
    // Clean up interval on component unmount
    onBeforeUnmount(() => {
        clearInterval(interval);
    });
})

// Function to handle file selection
const onFileSelected = (event) => {
  const files = event.target.files || event.dataTransfer.files;
  
  // Attempt to detect timezone from file
  if (files && files.length > 0) {
    // First store the file event
    selectedFile.value = event;
    
    // Detect file format and possible timezone
    detectFileTimezone(files[0]).then(() => {
      // Always show the confirmation dialog when file contains date/time info
      // This ensures the user makes a conscious choice about timezone
      showTimezoneConfirmation.value = true;
    });
  }
}

// Detect timezone from file content (if possible)
const detectFileTimezone = async (file) => {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target.result;
      
      // Try to detect date format from the file content
      if (content.includes('Date/Time') && content.match(/\d{8};\d{6}/)) {
        // Interactive Brokers format: "20250602;103135"
        csvDateTimeFormat.value = 'YYYYMMDD;HHMMSS';
      } else if (content.match(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)) {
        // ISO format: "2025-06-02T10:31:35"
        csvDateTimeFormat.value = 'YYYY-MM-DDTHH:mm:ss';
      } else if (content.match(/\d{2}\/\d{2}\/\d{4}\s+\d{2}:\d{2}:\d{2}/)) {
        // US format: "06/02/2025 10:31:35"
        csvDateTimeFormat.value = 'MM/DD/YYYY HH:mm:ss';
      } else if (content.match(/\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2}:\d{2}/)) {
        // ISO-like format: "2025/06/02 10:31:35"
        csvDateTimeFormat.value = 'YYYY/MM/DD HH:mm:ss';
      }
      
      // For specific brokers, set known timezone and format defaults
      if (selectedBroker.value === 'interactiveBrokers' || content.includes('ClientAccountID')) {
        csvDateTimeFormat.value = 'YYYYMMDD;HHMMSS';
        fileTimezone.value = 'America/New_York';
      } else if (selectedBroker.value === 'tdAmeritrade' || content.includes('TD Ameritrade')) {
        fileTimezone.value = 'America/New_York';
      } else {
        // Default to device timezone if not specifically detected
        fileTimezone.value = deviceTimeZone.value;
      }
      
      console.log(`Detected file format: ${csvDateTimeFormat.value}, presumed timezone: ${fileTimezone.value}`);
      resolve();
    };
    reader.readAsText(file);
  });
}

// Store the selected file event
const selectedFile = ref(null);

// Handle timezone confirmation
const confirmTimezone = (choice) => {
  if (choice === 'device') {
    // Use the device's timezone (user's local timezone) as the source timezone
    console.log(`Setting source timezone to device timezone: ${deviceTimeZone.value}`);
    window.localStorage.setItem('sourceTimezone', deviceTimeZone.value);
  } else if (choice === 'selected') {
    // Use the file's detected timezone as the source timezone
    console.log(`Using detected file timezone: ${fileTimezone.value}`);
    window.localStorage.setItem('sourceTimezone', fileTimezone.value);
  }
  
  // Always store the target timezone (TradeNote's timezone)
  window.localStorage.setItem('targetTimezone', timeZoneTrade.value);
  
  showTimezoneConfirmation.value = false;
  
  // Process the import with the selected file
  if (selectedFile.value) {
    processImport(selectedFile.value);
    selectedFile.value = null;
  }
}

// Process the actual import
const processImport = (event) => {
  if (selectedBroker.value === "") {
    alert("Please select your broker");
    return;
  }
  
  useImportTrades(event, "file")
    .then(() => {
      // Don't automatically upload trades - user will click Submit button when ready
      console.log("File imported successfully. Click Submit to upload trades to server.");
    })
    .catch(error => {
      console.error("Import failed:", error);
      alert("Import failed: " + error.message);
    })
    .finally(() => {
      // Clear timezone settings after import completes
      window.localStorage.removeItem('sourceTimezone');
      window.localStorage.removeItem('targetTimezone');
    });
}

function inputChooseBroker(param) {
    localStorage.setItem('selectedBroker', param)
    selectedBroker.value = param
}

// Function to check for local trades
const checkLocalTrades = () => {
  const trades = DirectUpload.getLocalTrades();
  localTradesCount.value = trades.length;
};

// Function to open trade manager
const openTradeManager = () => {
  // Find the TradeUploadManager component and toggle its visibility
  const event = new CustomEvent('trade-manager:open');
  window.dispatchEvent(event);
};
</script>
<template>
    <SpinnerLoadingPage />
    {{ currentUser.value }}
    <p class="txt-small">See export instructions for your broker on <a
            href="https://tradenote.co/brokers.html" target="_blank">Brokers Page</a>. <span v-if="!(currentUser.hasOwnProperty('apis') && currentUser.apis.length>0 && currentUser.apis.findIndex(obj => obj.provider === 'polygon' || obj.provider === 'databento') !=-1)">To add MFE prices automatically, insert your API key in <a href="/settings">settings</a>.</span>
    </p>
    <!--DROPDOWN LIST-->
    <div class="form-floating">
        <select id="brokerSelect" v-on:input="inputChooseBroker($event.target.value)" class="form-select">
            <option v-for="item in brokers" v-bind:value="item.value" v-bind:selected="item.value == selectedBroker">
                {{ item.label }}</option>
        </select>
        <label for="brokerSelect">Select your broker or trading platform</label>
    </div>
    <p class="mt-2" v-show="selectedBroker && brokers.filter(f => f.value == selectedBroker).length > 0">
        Supported asset types: <span
            v-for="(item, index) in brokers.filter(f => f.value == selectedBroker)[0]?.assetTypes || []">{{ item }}<span
                v-show="brokers.filter(f => f.value == selectedBroker)[0]?.assetTypes?.length > 1 && (index + 1) < (brokers.filter(f => f.value == selectedBroker)[0]?.assetTypes?.length || 0)">,
            </span></span>
    </p>
    <p v-show="selectedBroker == 'tradovate'">
        Commisssion Plan: <span>
            <div class="form-check form-check-inline" v-for="item in tradovateTiers" :key="item.value">
                <input class="form-check-input" type="radio" :value="item.value" v-model="selectedTradovateTier">
                {{ item.label }}
            </div>

        </span>
    </p>

    <!--MFE-->
    <div class="mt-4" v-if="currentUser.hasOwnProperty('apis') && (currentUser.apis.findIndex(obj => obj.provider === 'polygon' || obj.provider === 'databento') > -1)">
        <div class="form-check form-switch">
            <label>Add MFE prices automatically</label>
            <input class="form-check-input" type="checkbox" role="switch" v-model="uploadMfePrices"
                v-on:click="uploadMfePrices = !uploadMfePrices">
        </div>
    </div>

    <!--IMPORT-->
    <div class="mt-3">

        <div v-if="selectedBroker != 'tradeStation'" class="input-group mb-3">
            <input id="tradesInput" type="file" v-on:change="onFileSelected" />
        </div>

        <div v-else>

            <div class="form-floating">
                <textarea id="tradesInputText" class="form-control" style="height: 100px"
                    v-on:change="brokerData = $event.target.value"></textarea>
                <label for="tradesInputText">Paste your data</label>
            </div>

            <button type="button" v-on:click="useImportTrades('', 'text')" class="btn btn-success mt-3 mb-3">Load</button>
        </div>
        
        <div v-if="existingImports.length != 0">
            Following dates are already imported: <span v-for="(item, index) in existingImports">
                <span v-if="index > 0">, </span>{{ useDateCalFormat(item) }}</span>
        </div>
        
        <!-- Upload status notification -->
        <div v-if="uploadStatus" :class="`alert ${uploadStatus.success ? 'alert-success' : 'alert-danger'} mt-3`">
            <div class="d-flex align-items-center">
                <i :class="`uil ${uploadStatus.success ? 'uil-check-circle' : 'uil-exclamation-triangle'} me-2`" style="font-size: 1.5rem;"></i>
                <div>
                    <strong>{{ uploadStatus.title }}</strong>
                    <p class="mb-0">{{ uploadStatus.message }}</p>
                </div>
            </div>
        </div>

        <div v-if="Object.keys(blotter).length > 0 && Object.keys(pAndL).length > 0"
            v-for="(execution, index) in executions">
            <div v-if="blotter[index]">
                <h3 class="ml-2 mt-2 text-blue">{{ useCreatedDateFormat(index) }}</h3>
                <table class="table">
                    <thead>
                        <tr>
                            <th scope="col">Symbol</th>
                            <th scope="col">Vol</th>
                            <th scope="col">P/L gross</th>
                            <th scope="col">Comm</th>
                            <th scope="col">Tot Fees</th>
                            <th scope="col">P/L net</th>
                            <th scope="col">Wins(g)</th>
                            <th scope="col">Loss(g)</th>
                            <th scope="col">Trades</th>
                            <th scope="col">Executions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="blot in blotter[index]">
                            <td>{{ blot.symbol }}</td>
                            <td>{{ useDecimalsArithmetic(blot.buyQuantity, blot.sellQuantity) }}</td>
                            <td v-bind:class="[blot.grossProceeds > 0 ? 'greenTrade' : 'redTrade']">
                                {{ (blot.grossProceeds).toFixed(2) }}</td>
                            <td>{{ (blot.commission).toFixed(2) }}</td>
                            <td>{{ (blot.fees).toFixed(2) }}</td>
                            <td v-bind:class="[blot.netProceeds > 0 ? 'greenTrade' : 'redTrade']">
                                {{ (blot.netProceeds).toFixed(2) }}</td>
                            <td>{{ blot.grossWinsCount }}</td>
                            <td>{{ blot.grossLossCount }}</td>
                            <td>{{ blot.trades }}</td>
                            <td>{{ blot.executions }}</td>
                        </tr>
                        <tr v-if="index != null" class="sumRow">
                            <td>Total</td>
                            <td>{{ useDecimalsArithmetic(pAndL[index].buyQuantity, pAndL[index].sellQuantity) }}</td>
                            <td v-bind:class="[pAndL[index].grossProceeds > 0 ? 'greenTrade' : 'redTrade']">
                                {{ (pAndL[index].grossProceeds).toFixed(2) }}</td>
                            <td>{{ (pAndL[index].commission).toFixed(2) }}</td>
                            <td>{{ (pAndL[index].fees).toFixed(2) }}</td>
                            <td v-bind:class="[pAndL[index].netProceeds > 0 ? 'greenTrade' : 'redTrade']">
                                {{ (pAndL[index].netProceeds).toFixed(2) }}</td>
                            <td>{{ pAndL[index].grossWinsCount }}</td>
                            <td>{{ pAndL[index].grossLossCount }}</td>
                            <td>{{ pAndL[index].trades }}</td>
                            <td>{{ pAndL[index].executions }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!--BUTTONS-->
    <div>
        <button v-show="Object.keys(executions).length > 0 && !spinnerLoadingPage" type="button"
            v-on:click="useUploadTrades" class="btn btn-success btn-lg me-3">Submit</button>

        <button type="cancel" onclick="location.href = 'dashboard';"
            class="btn btn-outline-secondary btn-sm me-2">Cancel</button>

    </div>

    <!-- Timezone confirmation modal -->
    <div v-if="showTimezoneConfirmation" class="position-fixed top-0 start-0 w-100 h-100" style="background-color: rgba(0,0,0,0.5); z-index: 1050; display: flex; align-items: center; justify-content: center;">
      <div class="card border-primary" style="max-width: 600px; width: 90%;">
        <div class="card-header bg-primary text-white">
          <strong>Timezone Confirmation</strong>
        </div>
        <div class="card-body">
          <div class="mb-3">
            <i class="uil uil-clock me-2"></i> 
            <strong>Your file contains date and time information</strong>
          </div>
          <p>TradeNote needs to know which timezone your file's dates and times are in:</p>
          <div class="d-flex mb-2 align-items-center">
            <div class="badge bg-primary me-2">File Format</div>
            <code>{{ csvDateTimeFormat }}</code>
          </div>
          <div class="alert alert-info">
            <p class="mb-1"><strong>Your device timezone:</strong> {{ deviceTimeZone }}</p>
            <p class="mb-0"><strong>Your selected TradeNote timezone:</strong> {{ timeZoneTrade }}</p>
          </div>
          <p><strong>Which timezone are the dates and times in your file using?</strong></p>
          <div class="d-flex justify-content-between mt-4">
            <button class="btn btn-outline-secondary" @click="confirmTimezone('device')">
              <i class="uil uil-globe me-1"></i>
              File Times are in {{ deviceTimeZone.split('/').pop().replace('_', ' ') }}
              <small class="d-block">(Your device timezone)</small>
            </button>
            <button class="btn btn-primary" @click="confirmTimezone('selected')">
              <i class="uil uil-check me-1"></i>
              File Times are in {{ fileTimezone.split('/').pop().replace('_', ' ') }}
              <small class="d-block">(File's detected timezone)</small>
            </button>
          </div>
          <div class="alert alert-secondary mt-3 small">
            <i class="uil uil-info-circle me-1"></i> 
            <strong>Note:</strong> Your trades will be stored in your selected TradeNote timezone ({{ timeZoneTrade.split('/').pop().replace('_', ' ') }}). 
            TradeNote will automatically convert the times from your file's timezone.
          </div>
        </div>
      </div>
    </div>
    
    <!-- API Debug Console -->
    <ApiDebugConsole />
</template>