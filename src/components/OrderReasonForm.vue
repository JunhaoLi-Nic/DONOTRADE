<template>
  <div>
    <a-button v-if="showButton" type="text" size="small" @click="visible = true" :class="[
      'checklist-btn',
      { 'checklist-btn-completed': order.reasonCompleted || !!order.reasonData }
    ]">
      <template #icon>
        <check-circle-outlined v-if="order.reasonCompleted || !!order.reasonData" />
        <form-outlined v-else />
      </template>
      {{ (order.reasonCompleted || !!order.reasonData) ? 'View/Edit Checklist' : 'Add Checklist' }}
    </a-button>

    <a-modal :title="`Trade Checklist - ${order.symbol} ${order.action}`" :visible="visible" @cancel="onClose"
      :width="800" :footer="null" class="dark-modal">
      <a-form ref="formRef" :model="formState" layout="vertical" :required-mark="false" class="dark-form">
        <!-- Show relevant catalysts if we have a symbol -->
        <a-card v-if="order.symbol" size="small" style="margin-bottom: 16px;" class="dark-card">
          <template #title>
            <a-space>
              <file-text-outlined />
              <span class="dark-text">Relevant Market Catalysts</span>
            </a-space>
          </template>
          <template #extra>
            <a-button size="small" @click="checkCatalysts" class="check-catalysts-btn">
              Check Catalysts
            </a-button>
          </template>
          <relevant-catalysts :symbol="order.symbol" />
        </a-card>

        <!-- Trade Reasoning -->
        <a-card title="1. Trade Reasoning" size="small" style="margin-bottom: 16px;" class="dark-card">
          <template #title>
            <span class="dark-text">1. Trade Reasoning</span>
          </template>
          <a-form-item name="buyReason" label="My reason for buying this stock is:"
            :rules="[{ required: true, message: 'Please enter your reason' }]" class="dark-form-item">
            <a-textarea v-model:value="formState.buyReason" :rows="2"
              placeholder="Enter your primary reason for this trade..." class="dark-input" />
          </a-form-item>

          <a-form-item name="catalysts" label="The catalyst/driver for this stock is:" :rules="[{
            required: true,
            message: 'Please identify the catalyst or select None'
          }]" class="dark-form-item">
            <a-auto-complete v-model:value="formState.catalysts" placeholder="Select a catalyst or type custom reason"
              style="width: 100%;" :options="catalystOptions" :filter-option="filterCatalystOption"
              @change="handleCatalystChange" @select="handleCatalystSelect" class="dark-select" />
          </a-form-item>

          <a-form-item name="sector" label="Which sectors are in focus? This stock belongs to:"
            :rules="[{ required: true, message: 'Please specify the sector' }]" class="dark-form-item">
            <a-select v-model:value="formState.sector" :options="sectorOptions" placeholder="Select or type sector"
              show-search allow-clear
              :filter-option="(input, option) => option.label.toLowerCase().includes(input.toLowerCase())"
              :not-found-content="'Type to add custom sector'" class="dark-select" mode="combobox" />
          </a-form-item>

          <a-form-item name="timeframe" label="Expected timeframe for this trade:" class="dark-form-item">
            <a-radio-group v-model:value="formState.timeframe" class="dark-radio-group">
              <a-radio value="short-term" class="dark-radio">Short-term (1-5 days)</a-radio>
              <a-radio value="swing" class="dark-radio">Swing (1-3 weeks)</a-radio>
              <a-radio value="position" class="dark-radio">Medium-term</a-radio>
            </a-radio-group>
          </a-form-item>

          <a-form-item name="strategy" label="My trading strategy is:" class="dark-form-item">
            <a-radio-group v-model:value="formState.strategy" class="dark-radio-group">
              <a-radio value="pullback" class="dark-radio">Pullback Entry</a-radio>
              <a-radio value="breakout" class="dark-radio">Breakout Entry</a-radio>
              <a-radio value="vcp" class="dark-radio">VCP</a-radio>
              <a-radio value="reversal" class="dark-radio">ICT Reversal </a-radio>
              <a-radio value="reversal" class="dark-radio">ICT Expand </a-radio>
              <a-radio value="other" class="dark-radio">Other</a-radio>
            </a-radio-group>
          </a-form-item>

          <a-form-item name="marketTrend" label="Current market (index) trend is:" class="dark-form-item">
            <a-radio-group v-model:value="formState.marketTrend" class="dark-radio-group">
              <a-radio value="uptrend" class="dark-radio">Uptrend</a-radio>
              <a-radio value="choppy" class="dark-radio">Sideways/Choppy</a-radio>
              <a-radio value="downtrend" class="dark-radio">Downtrend</a-radio>
            </a-radio-group>
          </a-form-item>

          <a-form-item name="marketSentiment" label="Current market sentiment is:" class="dark-form-item">
            <a-input v-model:value="formState.marketSentiment" placeholder="e.g., Bullish, Cautious, Fearful"
              class="dark-input" />
          </a-form-item>
        </a-card>

        <!-- Technical Analysis & Risk Control -->
        <a-card title="2. Technical Analysis & Risk Control" size="small" style="margin-bottom: 16px;"
          class="dark-card">
          <template #title>
            <span class="dark-text">2. Technical Analysis & Risk Control</span>
          </template>
          <a-form-item name="entryBasis" label="My entry point is based on:"
            :rules="[{ required: true, message: 'Please specify your entry basis' }]" class="dark-form-item">
            <a-input v-model:value="formState.entryBasis"
              placeholder="Support level? Key moving average? Breakout pattern?" class="dark-input" />
          </a-form-item>

          <a-form-item name="stopLoss" label="My stop loss is set at:"
            :rules="[{ required: true, message: 'Please specify your stop loss logic' }]" class="dark-form-item">
            <a-input v-model:value="formState.stopLoss"
              placeholder="Is the stop loss a strong support? level 2 market price evaluation, volume, etc."
              class="dark-input" />
          </a-form-item>

          <a-form-item name="riskRewardRatio" label="My risk-reward ratio is:"
            :rules="[{ required: true, message: 'Please specify risk-reward ratio' }]" class="dark-form-item">
            <a-tooltip title="This value is automatically calculated from your entry, target, and stop loss prices">
              <a-input v-model:value="formState.riskRewardRatio" placeholder="Ideal value ≥ 3:1"
                :value="formState.riskRewardRatio || '3:1'" :disabled="true" class="dark-input calculated-field">
                <template #prefix>
                  <calculator-outlined style="color: #4a6cf7" />
                </template>
              </a-input>
            </a-tooltip>
          </a-form-item>

          <a-form-item name="onWatchlist" label="Is this stock on my planned trade list (e.g., trade tonight)?"
            class="dark-form-item">
            <a-radio-group v-model:value="formState.onWatchlist" class="dark-radio-group">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
          </a-form-item>

          <a-form-item name="positionSizing" label="My current position distribution is:" class="dark-form-item">
            <a-input v-model:value="formState.positionSizing" placeholder="Large cap/growth/thematic stock ratios"
              class="dark-input" />
          </a-form-item>

          <a-form-item label="Current account risk control:" class="dark-form-item">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-form-item name="positionSize" label="Position size:" style="margin-bottom: 0" class="dark-form-item">
                  <a-tooltip title="Automatically calculated as: (Price × Quantity) ÷ Account Balance">
                    <a-input v-model:value="formState.positionSize" :value="formState.positionSize || '0.00'"
                      style="width: 100%" :disabled="true" class="dark-input calculated-field">
                      <template #addonAfter>%</template>
                      <template #prefix>
                        <calculator-outlined style="color: #4a6cf7" />
                      </template>
                    </a-input>
                  </a-tooltip>
                </a-form-item>
                <div v-if="accountBalance && orderValue" style="font-size: 12px; color: #888; margin-top: 4px"
                  class="dark-text-secondary">
                  Order value: ${{ orderValueFormatted }} / Account: ${{ accountBalanceFormatted }}
                </div>
              </a-col>
              <a-col :span="12">
                <a-form-item name="maxDrawdown" label="Total drawdown manageable:" style="margin-bottom: 0"
                  class="dark-form-item">
                  <a-input v-model:value="formState.maxDrawdown" class="dark-input">
                    <template #addonAfter>%</template>
                  </a-input>
                </a-form-item>
              </a-col>
            </a-row>
          </a-form-item>

          <a-form-item name="riskAcceptable" label="Is the risk of this trade within my acceptable range?"
            class="dark-form-item">
            <a-radio-group v-model:value="formState.riskAcceptable" class="dark-radio-group">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
          </a-form-item>
        </a-card>

        <!-- Psychological & Discipline Checks -->
        <a-card title="3. Psychological & Discipline Checks" size="small" style="margin-bottom: 16px;"
          class="dark-card">
          <template #title>
            <span class="dark-text">3. Psychological & Discipline Checks</span>
          </template>
          <a-form-item name="checkFomo"
            label="Am I buying because I saw others making money (FOMO)? And I want to chase the uptrend? Check out the market breadth and see how likely the market can keep going"
            class="dark-form-item">
            <a-radio-group v-model:value="formState.checkFomo" class="dark-radio-group" @change="val => {
              if (val === true) {
                message.warning('Trading based on FOMO is dangerous. Please reconsider your decision.');
              }
            }">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
            <div v-if="formState.checkFomo === true" class="warning-message">
              <a-alert message="FOMO Warning"
                description="Trading based on FOMO (Fear of Missing Out) often leads to poor decisions and losses. You should have a solid strategy rather than chasing trends."
                type="error" show-icon />
            </div>
          </a-form-item>

          <a-form-item name="checkLossFear" label="Am I buying because I'm afraid of missing the bottom?"
            class="dark-form-item">
            <a-radio-group v-model:value="formState.checkLossFear" class="dark-radio-group" @change="val => {
              if (val === true) {
                message.warning('Fear-based trading decisions often lead to poor outcomes.');
              }
            }">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
            <div v-if="formState.checkLossFear === true" class="warning-message">
              <a-alert message="Fear Warning"
                description="Trading out of fear of missing the bottom is not a sound strategy. Wait for confirmation signals rather than trying to catch a falling knife."
                type="error" show-icon />
            </div>
          </a-form-item>

          <a-form-item name="checkPriceBottom" label="Am I aware that price may not have bottomed out yet?"
            class="dark-form-item">
            <a-radio-group v-model:value="formState.checkPriceBottom" class="dark-radio-group" @change="val => {
              if (val === false) {
                message.warning('Always be aware that prices can continue to fall after your entry.');
              }
            }">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
            <div v-if="formState.checkPriceBottom === false" class="warning-message">
              <a-alert message="Risk Awareness Warning"
                description="You should always be aware that prices may continue to fall after your entry. Not acknowledging this risk can lead to poor position sizing and risk management."
                type="error" show-icon />
            </div>
          </a-form-item>

          <a-form-item name="checkProveRight" label="Am I just trying to prove myself right or beat the clock?"
            class="dark-form-item">
            <a-radio-group v-model:value="formState.checkProveRight" class="dark-radio-group" @change="val => {
              if (val === true) {
                message.warning('Trading to prove yourself right is emotionally-driven and risky.');
              }
            }">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
            <div v-if="formState.checkProveRight === true" class="warning-message">
              <a-alert message="Ego Warning"
                description="Trading to prove yourself right or beat the clock is driven by ego, not strategy. This approach typically leads to poor decision-making and losses."
                type="error" show-icon />
            </div>
          </a-form-item>

          <a-form-item name="checkFollowingStrategy"
            label="Am I following my pre-defined strategy (WRITTEN IN PLAYBOOK?) rather than improvising?" class="dark-form-item">
            <a-radio-group v-model:value="formState.checkFollowingStrategy" class="dark-radio-group" @change="val => {
              if (val === false) {
                message.warning('Deviating from your strategy increases risk. Stick to your plan.');
              }
            }">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
            <div v-if="formState.checkFollowingStrategy === false" class="warning-message">
              <a-alert message="Strategy Warning"
                description="Improvising rather than following your pre-defined strategy leads to inconsistent results and emotional decision-making. Stick to your trading plan."
                type="error" show-icon />
            </div>
          </a-form-item>

          <a-form-item name="checkEmotionalTrading"
            label="If 'trade1' lost money, am I emotionally stable for 'trade2'? If account start to be profitable and market is in resistance then dont go or use half portion" class="dark-form-item">
            <a-radio-group v-model:value="formState.checkEmotionalTrading" class="dark-radio-group" @change="val => {
              if (val === false) {
                message.warning('Trading after a loss without emotional stability often leads to revenge trading and compounding losses. Consider taking a break to regain emotional balance.');
              }
            }">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
            <div v-if="formState.checkEmotionalTrading === false" class="warning-message">
              <a-alert message="Emotional Stability Warning"
                description="Trading after a loss without emotional stability often leads to revenge trading and compounding losses. Consider taking a break to regain emotional balance."
                type="error" show-icon />
            </div>
          </a-form-item>

          <a-form-item name="checkOvertrading" label="Am I overtrading today causing emotional volatility?"
            class="dark-form-item">
            <a-radio-group v-model:value="formState.checkOvertrading" class="dark-radio-group" @change="val => {
              if (val === true) {
                message.warning('Overtrading can lead to emotional decisions and increased losses.');
              }
            }">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
            <div v-if="formState.checkOvertrading === true" class="warning-message">
              <a-alert message="Overtrading Warning"
                description="Overtrading often leads to emotional volatility, poor decision-making, and increased losses. Consider taking a break or reducing your trading frequency."
                type="error" show-icon />
            </div>
          </a-form-item>

          <a-form-item name="checkStopLossSet" label="If I'm wrong, have I accepted and set a proper stop loss?"
            class="dark-form-item">
            <a-radio-group v-model:value="formState.checkStopLossSet" class="dark-radio-group" @change="val => {
              if (val === false) {
                message.warning('Trading without a proper stop loss greatly increases risk.');
              }
            }">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
            <div v-if="formState.checkStopLossSet === false" class="warning-message">
              <a-alert message="Stop Loss Warning"
                description="Trading without a proper stop loss exposes your account to unlimited risk. Always set and honor your stop losses to protect your capital."
                type="error" show-icon />
            </div>
          </a-form-item>

          <a-form-item name="checkMentalState" label="Am I mentally focused and emotionally stable right now?"
            class="dark-form-item">
            <a-radio-group v-model:value="formState.checkMentalState" class="dark-radio-group" @change="val => {
              if (val === false) {
                message.warning('Trading requires mental focus and emotional stability.');
              }
            }">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
            <div v-if="formState.checkMentalState === false" class="warning-message">
              <a-alert message="Mental State Warning"
                description="Trading requires mental focus and emotional stability. Consider taking a break and returning when you're in a better mental state."
                type="error" show-icon />
            </div>
          </a-form-item>

          <a-form-item name="checkAcceptLoss" label="If this trade fails, can I accept it calmly? Can't be unhappy if trade fails, it is part of the game."
            :rules="[{ required: true, message: 'You must be able to accept the loss to proceed' }]"
            class="dark-form-item">
            <a-radio-group v-model:value="formState.checkAcceptLoss" class="dark-radio-group" @change="val => {
              if (val === false) {
                message.warning('If you cannot accept the loss, you should not trade. Please reconsider before proceeding.');
              }
            }">
              <a-radio :value="true" class="dark-radio">Yes</a-radio>
              <a-radio :value="false" class="dark-radio">No</a-radio>
            </a-radio-group>
            <div v-if="formState.checkAcceptLoss === false" class="warning-message">
              <a-alert message="Trading Warning"
                description="If you cannot accept potential losses, you should not proceed with this trade. Risk management requires emotional preparedness for losses."
                type="error" show-icon />
            </div>
          </a-form-item>
        </a-card>

        <a-card title="4. Self-reflection" size="small" style="margin-bottom: 16px;" class="dark-card">
          <a-form-item name="whatCanGoWrong" label="What can go wrong with this trade?" class="dark-form-item">
            <a-textarea v-model:value="formState.whatCanGoWrong" class="dark-input"
              placeholder="Is this a common sense? Or base on niche information? Common sense is a mistake for the market." />
          </a-form-item>
        </a-card>

        <!-- Risk/Reward info -->
        <div style="margin-top: 16px; margin-bottom: 16px">
          <a-typography-text type="secondary" class="dark-text-secondary">
            <info-circle-outlined /> The risk/reward ratio for this trade is {{ riskRewardDisplay }}
          </a-typography-text>
        </div>

        <!-- Add explicit footer with buttons -->
        <div class="form-footer">
          <a-button @click="onClose">Cancel</a-button>
          <a-button type="primary" :loading="submitting" @click="handleSubmit" class="save-btn">
            Save
          </a-button>
        </div>
      </a-form>

    </a-modal>
  </div>
</template>

<script>
import { ref, reactive, computed, watch, defineComponent, nextTick, onMounted } from 'vue';
import {
  Modal, Form, Input, Button, Select, Space, Typography, Checkbox,
  Divider, Card, Row, Col, Radio, InputNumber, Tooltip, Tag, Empty,
  message, AutoComplete, Alert
} from 'ant-design-vue';
import { InfoCircleOutlined, FormOutlined, CalculatorOutlined, FileTextOutlined, CheckCircleOutlined } from '@ant-design/icons-vue';
import axios from 'axios';
import dayjs from 'dayjs';
import RelevantCatalysts from './RelevantCatalystsVue.vue';
import orderSyncService from '../services/orderSyncService';

// Define the interface for CatalystData
const CatalystData = {
  date: String,
  keyFact: String,
  actualVsExpectation: String,
  currentMarketTheme: String,
  relatedSymbols: Array,
  marketPreAnnouncement: String,
  howCatalystAffects: String,
  technicalPosition: String,
  keyLevels: String,
  notes: String,
  importance: String
};

// Define the interface for OrderReasonData
const OrderReasonData = {
  // Trade reasoning
  buyReason: String,
  catalysts: String,
  sector: String,

  // Time frame and strategy
  timeframe: String,
  strategy: String,
  marketTrend: String,
  marketSentiment: String,

  // Technical analysis
  entryBasis: String,
  stopLoss: String,
  riskRewardRatio: String,
  onWatchlist: Boolean,
  positionSizing: String,

  // Risk management
  positionSize: String,
  maxDrawdown: String,
  riskAcceptable: Boolean,

  // Psychological checks
  checkFomo: Boolean,
  checkLossFear: Boolean,
  checkPriceBottom: Boolean,
  checkProveRight: Boolean,
  checkFollowingStrategy: Boolean,
  checkEmotionalTrading: Boolean,
  checkOvertrading: Boolean,
  checkStopLossSet: Boolean,
  checkMentalState: Boolean,
  checkAcceptLoss: Boolean
};

export default defineComponent({
  name: 'OrderReasonForm',
  components: {
    RelevantCatalysts,
    AModal: Modal,
    AForm: Form,
    AFormItem: Form.Item,
    AInput: Input,
    ATextarea: Input.TextArea,
    AButton: Button,
    ASelect: Select,
    AOption: Select.Option,
    ASpace: Space,
    ATypographyText: Typography.Text,
    ATypographyTitle: Typography.Title,
    ACheckbox: Checkbox,
    ADivider: Divider,
    ACard: Card,
    ARow: Row,
    ACol: Col,
    ARadio: Radio,
    ARadioGroup: Radio.Group,
    AInputNumber: InputNumber,
    ATooltip: Tooltip,
    ATag: Tag,
    AEmpty: Empty,
    AAutoComplete: AutoComplete,
    AAlert: Alert,
    InfoCircleOutlined,
    FormOutlined,
    CalculatorOutlined,
    FileTextOutlined,
    CheckCircleOutlined
  },
  props: {
    order: {
      type: Object,
      required: true
    },
    visible: {
      type: Boolean,
      default: false
    },
    onReasonUpdated: {
      type: Function,
      required: true
    },
    onClose: {
      type: Function,
      default: () => { }
    },
    accountBalance: {
      type: Number,
      default: 100000
    },
    showButton: {
      type: Boolean,
      default: true
    }
  },
  setup(props, { emit }) {
    const formRef = ref(null);
    const visible = ref(props.visible);
    const submitting = ref(false);
    const calculatedPositionSize = ref(null);
    const catalysts = ref([]);
    
    // Define emits
    const emits = ['update:visible', 'mounted'];

    const formState = reactive({
      buyReason: '',
      catalysts: '',
      sector: 'General Market',
      timeframe: 'short-term',
      strategy: 'momentum',
      marketTrend: 'uptrend',
      marketSentiment: '',
      entryBasis: '',
      stopLoss: '',
      riskRewardRatio: '',
      onWatchlist: false,
      positionSizing: '',
      positionSize: '',
      maxDrawdown: '',
      riskAcceptable: false,
      checkFomo: false,
      checkLossFear: false,
      checkPriceBottom: false,
      checkProveRight: false,
      checkFollowingStrategy: false,
      checkEmotionalTrading: false,
      checkOvertrading: false,
      checkStopLossSet: false,
      checkMentalState: false,
      checkAcceptLoss: false
    });

    // Calculate order value
    const orderValue = computed(() => {
      if (props.order.limitPrice && props.order.totalQuantity) {
        return props.order.limitPrice * props.order.totalQuantity;
      }
      return null;
    });

    // Formatted values for display
    const orderValueFormatted = computed(() => {
      return orderValue.value?.toFixed(2) || '0.00';
    });

    const accountBalanceFormatted = computed(() => {
      return props.accountBalance?.toFixed(2) || '0.00';
    });

    const riskRewardDisplay = computed(() => {
      return props.order.riskRewardRatio
        ? `1:${props.order.riskRewardRatio.toFixed(2)}`
        : 'not available';
    });

    const catalystOptions = computed(() => {
      return [
        { value: 'none', label: 'None' },
        ...catalysts.value
          .filter(catalyst => catalyst.keyFact)
          .map(catalyst => ({
            value: catalyst.keyFact || '',
            label: catalyst.keyFact || ''
          }))
      ];
    });

    // Update the watch function to use positionSizePercent from the order object
    watch(() => [props.order.limitPrice, props.order.totalQuantity, props.order.accountBalance, props.order.riskRewardRatio, props.order.positionSizePercent], () => {
      console.log("Watch triggered with values:", {
        limitPrice: props.order.limitPrice,
        totalQuantity: props.order.totalQuantity,
        accountBalance: props.accountBalance,
        riskRewardRatio: props.order.riskRewardRatio,
        positionSizePercent: props.order.positionSizePercent
      });

      // Use positionSizePercent from order if available
      if (props.order.positionSizePercent) {
        formState.positionSize = props.order.positionSizePercent.toFixed(2);
        console.log("Position size from order:", formState.positionSize);
      }
      // Otherwise calculate it if we have the necessary data
      else if (props.order.limitPrice && props.order.totalQuantity && props.accountBalance) {
        const positionValue = props.order.limitPrice * props.order.totalQuantity;
        const positionSizePercent = (positionValue / props.accountBalance) * 100;
        calculatedPositionSize.value = positionSizePercent;
        formState.positionSize = positionSizePercent.toFixed(2);
        console.log("Position size calculated:", formState.positionSize);
      }

      // Set risk-reward ratio from order prop if available
      if (props.order.riskRewardRatio) {
        formState.riskRewardRatio = `1:${props.order.riskRewardRatio.toFixed(2)}`;
        console.log("Risk-reward ratio set:", formState.riskRewardRatio);
      } else {
        // Set a default value if not available
        formState.riskRewardRatio = "3:1";
        console.log("Default risk-reward ratio set to 3:1");
      }
    }, { immediate: true });

    // Watch for changes in the order to update the form if needed
    watch(() => props.order, (newOrder) => {
      if (newOrder.reasonData && visible.value) {
        console.log(`Order updated with new reasonData for ${newOrder.symbol}, refreshing form`);
        
        // Update form state with the new reason data
        Object.keys(formState).forEach(key => {
          if (newOrder.reasonData[key] !== undefined) {
            formState[key] = newOrder.reasonData[key];
          }
        });
      }
    }, { deep: true });

    // Watch for changes in visibility
    watch(() => visible.value, async (isVisible) => {
      if (isVisible) {
        // Load catalysts when the modal opens
        await loadCatalysts();
        
        // If we have existing reason data from MongoDB or elsewhere, populate the form
        if (props.order.reasonData) {
          console.log(`Modal opened: Loading reason data for ${props.order.symbol}`);
          initializeFormWithReasonData(props.order.reasonData);
          logReasonData();
        } else {
          // No existing data, set defaults
          setDefaultFormValues();
          console.log(`Modal opened: No reason data for ${props.order.symbol}, using defaults`);
        }
      }
    });

    // Helper function to set default form values
    const setDefaultFormValues = () => {
      console.log("Setting default form values with order:", props.order);

      Object.assign(formState, {
        buyReason: '',
        catalysts: props.order.reasonData?.catalysts || '',
        sector: props.order.reasonData?.sector || 'General Market',
        stopLoss: props.order.stopPrice || '',
        riskRewardRatio: props.order.riskRewardRatio ? `1:${props.order.riskRewardRatio.toFixed(2)}` : '3:1',
        timeframe: 'short-term',
        strategy: 'momentum',
        marketTrend: 'uptrend',
        onWatchlist: false,
        riskAcceptable: false,
        // Set position size if calculated
        positionSize: calculatedPositionSize.value ? calculatedPositionSize.value.toFixed(2) : '',
        // Psychological checks all default to false
        checkFomo: false,
        checkLossFear: false,
        checkPriceBottom: false,
        checkProveRight: false,
        checkFollowingStrategy: false,
        checkEmotionalTrading: false,
        checkOvertrading: false,
        checkStopLossSet: false,
        checkMentalState: false,
        checkAcceptLoss: false
      });

      console.log("Default form values set:", {
        riskRewardRatio: formState.riskRewardRatio,
        positionSize: formState.positionSize
      });
    };

    // Load catalysts when component mounts or symbol changes
    const loadCatalysts = async () => {
      try {
        console.log('Loading catalysts...');

        // Try to load from localStorage first since it's faster
        const storedCatalysts = localStorage.getItem('marketCatalysts');
        if (storedCatalysts) {
          try {
            const allCatalysts = JSON.parse(storedCatalysts);
            console.log(`Loaded ${allCatalysts.length} catalysts from localStorage`);

            if (allCatalysts && allCatalysts.length > 0) {
              // Sort by date, most recent first
              const sortedCatalysts = [...allCatalysts].sort((a, b) => {
                if (!a.date) return 1;
                if (!b.date) return -1;
                return new Date(b.date).getTime() - new Date(a.date).getTime();
              });

              catalysts.value = sortedCatalysts;
              console.log('Catalysts set from localStorage:', catalysts.value);
              return;
            }
          } catch (parseError) {
            console.error('Error parsing catalysts from localStorage:', parseError);
          }
        }

        // If localStorage fails or is empty, try API
        try {
          const response = await axios.get('/api/catalysts');
          const allCatalysts = response.data;
          console.log(`Loaded ${allCatalysts.length} catalysts from API`);
          catalysts.value = allCatalysts;

          // Also save to localStorage for future use
          localStorage.setItem('marketCatalysts', JSON.stringify(allCatalysts));
        } catch (apiError) {
          console.error('Error loading catalysts from API:', apiError);

          // If no catalysts found anywhere, create sample ones
          if (!catalysts.value || catalysts.value.length === 0) {
            console.warn('No catalysts found - creating samples');
            createSampleCatalysts();

            // Load the newly created samples
            const samples = localStorage.getItem('marketCatalysts');
            if (samples) {
              catalysts.value = JSON.parse(samples);
              console.log('Loaded sample catalysts:', catalysts.value);
            }
          }
        }
      } catch (error) {
        console.error('Error in loadCatalysts:', error);
        createSampleCatalysts();
      }
    };

    // Close modal
    const onClose = () => {
      // Reset the form when closing the modal
      visible.value = false;
      
      // Call the parent's onClose function if provided
      if (props.onClose) {
        props.onClose();
      }
    };

    // Debug logging for form initialization
    const logReasonData = () => {
      if (props.order.reasonData) {
        console.log('===== CHECKLIST DATA DEBUG =====');
        console.log(`OrderReasonForm for ${props.order.symbol}: reasonData exists:`, props.order.reasonData);
        console.log('Form state after loading data:', formState);
        console.log('================================');
      } else {
        console.log(`OrderReasonForm for ${props.order.symbol}: NO reasonData found`);
      }
    };

    // Initialize with any existing data when component is mounted
    onMounted(async () => {
      // Load catalysts immediately when component mounts
      await loadCatalysts();
      
      console.log(`OrderReasonForm mounted for ${props.order.symbol}`, {
        hasReasonData: !!props.order.reasonData,
        orderProps: { ...props.order },
        reasonDataKeys: props.order.reasonData ? Object.keys(props.order.reasonData) : []
      });
      
      // Check for existing reason data
      if (props.order.reasonData) {
        console.log(`Mounting OrderReasonForm with existing data for ${props.order.symbol}`);
        initializeFormWithReasonData(props.order.reasonData);
        logReasonData();
      } else {
        setDefaultFormValues();
      }
      
      // Emit the mounted event
      emit('mounted');
    });

    // Helper function to initialize form with reason data
    const initializeFormWithReasonData = (reasonData) => {
      if (!reasonData) return;
      
      // Explicitly copy each field from reasonData to formState
      if (reasonData.buyReason !== undefined) formState.buyReason = reasonData.buyReason;
      if (reasonData.catalysts !== undefined) formState.catalysts = reasonData.catalysts;
      if (reasonData.sector !== undefined) formState.sector = reasonData.sector;
      if (reasonData.timeframe !== undefined) formState.timeframe = reasonData.timeframe;
      if (reasonData.strategy !== undefined) formState.strategy = reasonData.strategy;
      if (reasonData.marketTrend !== undefined) formState.marketTrend = reasonData.marketTrend;
      if (reasonData.marketSentiment !== undefined) formState.marketSentiment = reasonData.marketSentiment;
      if (reasonData.entryBasis !== undefined) formState.entryBasis = reasonData.entryBasis;
      if (reasonData.stopLoss !== undefined) formState.stopLoss = reasonData.stopLoss;
      if (reasonData.riskRewardRatio !== undefined) formState.riskRewardRatio = reasonData.riskRewardRatio;
      if (reasonData.onWatchlist !== undefined) formState.onWatchlist = reasonData.onWatchlist;
      if (reasonData.positionSizing !== undefined) formState.positionSizing = reasonData.positionSizing;
      if (reasonData.positionSize !== undefined) formState.positionSize = reasonData.positionSize;
      if (reasonData.maxDrawdown !== undefined) formState.maxDrawdown = reasonData.maxDrawdown;
      if (reasonData.riskAcceptable !== undefined) formState.riskAcceptable = reasonData.riskAcceptable;
      
      // Copy psychological checks
      if (reasonData.checkFomo !== undefined) formState.checkFomo = reasonData.checkFomo;
      if (reasonData.checkLossFear !== undefined) formState.checkLossFear = reasonData.checkLossFear;
      if (reasonData.checkPriceBottom !== undefined) formState.checkPriceBottom = reasonData.checkPriceBottom;
      if (reasonData.checkProveRight !== undefined) formState.checkProveRight = reasonData.checkProveRight;
      if (reasonData.checkFollowingStrategy !== undefined) formState.checkFollowingStrategy = reasonData.checkFollowingStrategy;
      if (reasonData.checkEmotionalTrading !== undefined) formState.checkEmotionalTrading = reasonData.checkEmotionalTrading;
      if (reasonData.checkOvertrading !== undefined) formState.checkOvertrading = reasonData.checkOvertrading;
      if (reasonData.checkStopLossSet !== undefined) formState.checkStopLossSet = reasonData.checkStopLossSet;
      if (reasonData.checkMentalState !== undefined) formState.checkMentalState = reasonData.checkMentalState;
      if (reasonData.checkAcceptLoss !== undefined) formState.checkAcceptLoss = reasonData.checkAcceptLoss;
      
      // Ensure UI reflects that this is an edit operation
      props.order.reasonCompleted = true;
    };

    // Form validation and submission
    const isFormValid = () => {
      const values = formState;
      console.log("Form values for validation:", values);

      // Extract the catalysts value
      const catalystValue = values.catalysts || '';

      // Basic required fields - be more lenient with catalysts
      const hasBasicInfo = Boolean(values.buyReason) &&
        (Boolean(catalystValue) || catalystValue.toLowerCase() === 'none') &&
        Boolean(values.sector) &&
        Boolean(values.timeframe);

      // Check if risk management is set
      const hasRiskManagement = Boolean(values.stopLoss) &&
        Boolean(values.riskRewardRatio);

      // At least some psychological checks should be marked
      const hasPsychChecks = values.checkFomo !== undefined ||
        values.checkLossFear !== undefined ||
        values.checkFollowingStrategy !== undefined ||
        values.checkEmotionalTrading !== undefined ||
        values.checkOvertrading !== undefined ||
        values.checkStopLossSet !== undefined ||
        values.checkMentalState !== undefined ||
        values.checkAcceptLoss !== undefined;

      console.log("Validation result:", {
        hasBasicInfo,
        hasRiskManagement,
        hasPsychChecks,
        buyReason: Boolean(values.buyReason),
        catalysts: Boolean(catalystValue) || catalystValue === 'none',
        sector: Boolean(values.sector),
        timeframe: Boolean(values.timeframe),
        stopLoss: Boolean(values.stopLoss),
        riskRewardRatio: Boolean(values.riskRewardRatio)
      });

      return hasBasicInfo && hasRiskManagement && hasPsychChecks;
    };

    const handleSubmit = async () => {
      try {
        submitting.value = true;
        await formRef.value.validate();

        // Check for critical warnings that should prevent submission
        const psychologicalWarnings = [];

        if (formState.checkAcceptLoss === false) {
          psychologicalWarnings.push("You must be able to accept potential losses");
        }

        if (formState.checkFomo === true) {
          psychologicalWarnings.push("Trading based on FOMO is not recommended");
        }

        if (formState.checkLossFear === true) {
          psychologicalWarnings.push("Trading out of fear of missing the bottom is not sound");
        }

        if (formState.checkPriceBottom === false) {
          psychologicalWarnings.push("You must be aware that prices may continue to fall");
        }

        if (formState.checkProveRight === true) {
          psychologicalWarnings.push("Trading to prove yourself right is emotionally-driven");
        }

        if (formState.checkFollowingStrategy === false) {
          psychologicalWarnings.push("You should follow your pre-defined strategy");
        }

        if (formState.checkEmotionalTrading === false) {
          psychologicalWarnings.push("You should be emotionally stable before trading");
        }

        if (formState.checkOvertrading === true) {
          psychologicalWarnings.push("Overtrading leads to poor decision-making");
        }

        if (formState.checkStopLossSet === false) {
          psychologicalWarnings.push("You must set a proper stop loss");
        }

        if (formState.checkMentalState === false) {
          psychologicalWarnings.push("Trading requires mental focus and emotional stability");
        }

        // If any psychological warnings exist, prevent submission
        if (psychologicalWarnings.length > 0) {
          message.error(`Cannot save checklist: ${psychologicalWarnings[0]}. Please correct your answers.`);
          submitting.value = false;
          return;
        }

        // Continue with normal submission
        const reasonData = { ...formState };

        // Set completion timestamp
        reasonData.completedAt = new Date().toISOString();

        // Update the order with reason data
        const updatedOrder = {
          ...props.order,
          reasonData,
          reasonCompleted: true
        };

        console.log("Saving order with reasonData:", updatedOrder);

        // Check if this is an update (we have mongoDbId or _id) or a new insert
        let mongoId = null;
        
        // Check for MongoDB ID in different possible fields
        if (props.order.mongoDbId) {
          mongoId = props.order.mongoDbId;
          console.log(`Using mongoDbId: ${mongoId}`);
        } else if (props.order._id) {
          mongoId = props.order._id;
          console.log(`Using _id: ${mongoId}`);
        } else if (props.order.orderId) {
          // Safely check if orderId starts with "missing-"
          const orderId = props.order.orderId;
          console.log(`Checking orderId: ${orderId} (type: ${typeof orderId})`);
          
          if (typeof orderId === 'string' && orderId.startsWith("missing-")) {
            mongoId = orderId;
            console.log(`Using orderId with missing- prefix: ${mongoId}`);
          }
        }
        
        // Check if this is an existing order in MongoDB
        const isExistingOrder = !!mongoId || (props.order._id !== undefined);
        
        if (isExistingOrder) {
          console.log(`Updating existing order ${props.order.symbol} with ID ${mongoId || props.order._id}`);
          try {
            // Ensure the MongoDB ID is properly set
            if (mongoId) {
              updatedOrder.mongoDbId = mongoId;
            }
            if (props.order._id) {
              updatedOrder._id = props.order._id;
            }
            
            // Use the dedicated update method
            const result = await orderSyncService.updateOrderReasonData(updatedOrder);
            if (result && result.success) {
              console.log(`Order ${props.order.symbol} updated successfully:`, result);
              message.success(`Checklist for ${props.order.symbol} updated`);
            } else {
              console.error(`Failed to update order ${props.order.symbol}:`, result);
              message.error(`Failed to update checklist: ${result?.message || 'Unknown error'}`);
            }
          } catch (updateError) {
            console.error(`Error updating order ${props.order.symbol}:`, updateError);
            message.error(`Failed to update checklist: ${updateError.message}`);
          }
        } else {
          // Call the parent's update function for new inserts
          console.log(`Creating new order for ${props.order.symbol}`);
          props.onReasonUpdated(props.order.orderId, true, reasonData);
        }

        // Also update the local state to show "View/Edit" immediately
        props.order.reasonCompleted = true;

        // Close the modal
        visible.value = false;

      } catch (error) {
        console.error('Validation failed:', error);
      } finally {
        submitting.value = false;
      }
    };

    // Helper functions
    const validateStopLoss = () => {
      if (formRef.value) {
        formRef.value.validateFields(['stopLoss']);
      }
    };

    const validateRiskReward = () => {
      if (formRef.value) {
        formRef.value.validateFields(['riskRewardRatio']);
      }
    };

    const validateSector = () => {
      if (formRef.value) {
        formRef.value.validateFields(['sector']);
      }
    };

    const handleSectorBlur = (e) => {
      if (!formState.sector.trim()) {
        formState.sector = 'General Market';
        if (formRef.value) {
          formRef.value.validateFields(['sector']);
        }
      }
    };

    const handleCatalystChange = (value) => {
      console.log("Selected/entered catalyst:", value);
      formState.catalysts = value;

      // Validate the field after change - use nextTick to ensure value is updated
      if (formRef.value) {
        nextTick(() => {
          formRef.value.validateFields(['catalysts']);
        });
      }
    };

    const handleCatalystSelect = (value) => {
      console.log("Selected catalyst from dropdown:", value);
      formState.catalysts = value;

      // Force immediate validation on select - use nextTick to ensure value is updated
      if (formRef.value) {
        nextTick(() => {
          formRef.value.validateFields(['catalysts']);
        });
      }
    };

    const filterCatalystOption = (inputValue, option) => {
      if (!inputValue || !option?.label) return true;
      return option.label.toString().toLowerCase().includes(inputValue.toLowerCase());
    };

    const checkCatalysts = async () => {
      const storedCatalysts = localStorage.getItem('marketCatalysts');
      if (storedCatalysts) {
        try {
          const catalystsData = JSON.parse(storedCatalysts);
          message.info(`Found ${catalystsData.length} catalysts in localStorage`);
          console.log("Catalysts in localStorage:", catalystsData);

          // Create sample data if none exists
          if (catalystsData.length === 0) {
            const samples = createSampleCatalysts();
            catalysts.value = samples;
          } else {
            catalysts.value = catalystsData;
          }
        } catch (e) {
          console.error('Error parsing catalysts:', e);
          message.error('Error parsing catalysts - creating new samples');
          const samples = createSampleCatalysts();
          catalysts.value = samples;
        }
      } else {
        message.warning('No catalysts found in localStorage - creating samples');
        const samples = createSampleCatalysts();
        catalysts.value = samples;
      }

      // Force a refresh of catalyst options
      nextTick(() => {
        console.log("Updated catalysts:", catalysts.value);
        console.log("Updated catalyst options:", catalystOptions.value);
        message.success(`Catalysts refreshed: ${catalysts.value.length} available`);
      });
    };

    const createSampleCatalysts = () => {
      // Generate more comprehensive sample data
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(today.getDate() - 1);
      const lastWeek = new Date(today);
      lastWeek.setDate(today.getDate() - 7);

      const sampleCatalysts = [
        {
          date: today.toISOString(),
          keyFact: "Fed announces rate hold",
          actualVsExpectation: "met",
          currentMarketTheme: "Monetary Policy",
          importance: "high"
        },
        {
          date: yesterday.toISOString(),
          keyFact: "Strong tech earnings",
          actualVsExpectation: "exceeded",
          currentMarketTheme: "Earnings",
          importance: "high"
        },
        {
          date: lastWeek.toISOString(),
          keyFact: "Inflation data released",
          actualVsExpectation: "below",
          currentMarketTheme: "Economic Data",
          importance: "medium"
        },
        {
          date: lastWeek.toISOString(),
          keyFact: "New AI product announcement",
          actualVsExpectation: "exceeded",
          currentMarketTheme: "Technology",
          importance: "high"
        },
        {
          date: today.toISOString(),
          keyFact: "Semiconductor shortage update",
          actualVsExpectation: "met",
          currentMarketTheme: "Supply Chain",
          importance: "medium"
        }
      ];

      localStorage.setItem('marketCatalysts', JSON.stringify(sampleCatalysts));
      message.success('Added sample catalysts');
      console.log('Created sample catalysts:', sampleCatalysts);
      return sampleCatalysts;
    };

    const sectorOptions = [
      { value: 'Energy', label: 'Energy' },
      { value: 'Materials', label: 'Materials' },
      { value: 'Industrials', label: 'Industrials' },
      { value: 'Consumer Discretionary', label: 'Consumer Discretionary' },
      { value: 'Consumer Staples', label: 'Consumer Staples' },
      { value: 'Health Care', label: 'Health Care' },
      { value: 'Financials', label: 'Financials' },
      { value: 'Information Technology', label: 'Information Technology' },
      { value: 'Communication Services', label: 'Communication Services' },
      { value: 'Utilities', label: 'Utilities' },
      { value: 'Real Estate', label: 'Real Estate' },
    ];

    return {
      formRef,
      formState,
      visible,
      submitting,
      calculatedPositionSize,
      orderValue,
      orderValueFormatted,
      accountBalanceFormatted,
      riskRewardDisplay,
      catalystOptions,
      handleSubmit,
      onClose,
      validateStopLoss,
      validateRiskReward,
      validateSector,
      handleSectorBlur,
      handleCatalystChange,
      handleCatalystSelect,
      filterCatalystOption,
      checkCatalysts,
      sectorOptions
    };
  }
});
</script>

<style>
/* Global styles for Ant Design components in dark mode */
.dark-select input {
  color: #e0e0e0 !important;
}

.dark-select .ant-select-selection-placeholder {
  color: #e0e0e0 !important;
}

.dark-select .ant-select-selector {
  background-color: #1e1e1e !important;
  border-color: #3a3a3a !important;
  color: #e0e0e0 !important;
}

.dark-select .ant-select-arrow {
  color: rgba(255, 255, 255, 0.45) !important;
}

.dark-select .ant-select-dropdown {
  background-color: #2a2a2a !important;
  border: 1px solid #3a3a3a !important;
}

.dark-select .ant-select-item {
  color: #e0e0e0 !important;
}

.dark-select .ant-select-item-option-active:not(.ant-select-item-option-disabled) {
  background-color: rgba(74, 108, 247, 0.2) !important;
}

.dark-select .ant-select-item-option-selected:not(.ant-select-item-option-disabled) {
  background-color: rgba(74, 108, 247, 0.4) !important;
  color: #ffffff !important;
}
</style>

<style scoped>
.checklist-btn {
  background-color: transparent;
  border: 1px solid #4a6cf7;
  color: #4a6cf7;
  font-size: 12px;
  padding: 4px 8px;
  height: auto;
  line-height: 1.2;
  position: relative;
  /* Make sure button is clickable */
  z-index: 5;
  /* Ensure button is above other elements */
  cursor: pointer;
}

.checklist-btn:hover {
  background-color: rgba(74, 108, 247, 0.1);
  border-color: #3a5cd8;
  color: #3a5cd8;
}

.check-catalysts-btn {
  background-color: #4a6cf7 !important;
  border-color: #4a6cf7 !important;
  color: #ffffff !important;
  cursor: pointer;
}

.check-catalysts-btn:hover {
  background-color: #3a5cd8 !important;
  border-color: #3a5cd8 !important;
}

.checklist-btn-completed {
  background-color: rgba(76, 175, 80, 0.1);
  border: 1px solid #4caf50;
  color: #4caf50;
}

.checklist-btn-completed:hover {
  background-color: rgba(76, 175, 80, 0.2);
  border-color: #388e3c;
  color: #388e3c;
}

.dark-modal {
  color: #e0e0e0 !important;
}

.dark-modal :deep(.ant-modal-content) {
  background-color: #1c1c1c !important;
  border: 1px solid #303030;
}

.dark-modal :deep(.ant-modal-header) {
  background-color: #1c1c1c !important;
  border-bottom: 1px solid #303030;
}

.dark-modal :deep(.ant-modal-title) {
  color: #e0e0e0 !important;
}

.dark-modal :deep(.ant-modal-close) {
  color: #e0e0e0 !important;
}

.dark-modal :deep(.ant-modal-body) {
  background-color: #1c1c1c !important;
  color: #e0e0e0 !important;
}

.dark-modal :deep(.ant-modal-footer) {
  background-color: #1c1c1c !important;
  border-top: 1px solid #303030;
}

/* Fix rule validation error messages */
.dark-modal :deep(.ant-form-item-explain-error) {
  color: #ff4d4f !important;
}

.dark-text {
  color: #e0e0e0 !important;
}

.dark-text-secondary {
  color: #a0a0a0 !important;
}

.dark-card {
  background-color: #262626 !important;
  border: 1px solid #303030;
  margin-bottom: 16px;
}

.dark-card :deep(.ant-card-head) {
  background-color: #1c1c1c !important;
  border-bottom: 1px solid #303030;
}

.dark-card :deep(.ant-card-head-title) {
  color: #e0e0e0 !important;
}

.dark-card :deep(.ant-card-body) {
  background-color: #262626 !important;
  color: #e0e0e0 !important;
}

.dark-form {
  color: #e0e0e0 !important;
}

.dark-form-item {
  color: #e0e0e0 !important;
}

.dark-form-item :deep(.ant-form-item-label > label) {
  color: #e0e0e0 !important;
}

.dark-input {
  background-color: #262626 !important;
  border-color: #303030 !important;
  color: #e0e0e0 !important;
}

.dark-input:hover,
.dark-input:focus {
  border-color: #4a6cf7 !important;
}

.dark-input :deep(textarea) {
  background-color: #262626 !important;
  color: #e0e0e0 !important;
}

.dark-input :deep(.ant-input) {
  background-color: #262626 !important;
  color: #e0e0e0 !important;
}

.dark-input :deep(.ant-input-group-addon) {
  background-color: #303030 !important;
  border-color: #303030 !important;
  color: #e0e0e0 !important;
}

.dark-select :deep(.ant-select-selector) {
  background-color: #262626 !important;
  border-color: #303030 !important;
  color: #e0e0e0 !important;
}

.dark-select :deep(.ant-select-arrow) {
  color: #e0e0e0 !important;
}

.dark-select :deep(.ant-select-dropdown) {
  background-color: #262626 !important;
  color: #e0e0e0 !important;
}

.dark-select :deep(.ant-select-item) {
  color: #e0e0e0 !important;
}

.dark-select :deep(.ant-select-item-option-content) {
  color: #e0e0e0 !important;
}

.dark-select :deep(.ant-select-item-option-selected) {
  background-color: #303030 !important;
}

.dark-radio-group :deep(.ant-radio-wrapper) {
  color: #e0e0e0 !important;
}

.dark-radio-group :deep(.ant-radio-inner) {
  background-color: #1c1c1c !important;
  border-color: #303030 !important;
}

.dark-radio-group :deep(.ant-radio-checked .ant-radio-inner) {
  border-color: #4a6cf7 !important;
}

.dark-radio-group :deep(.ant-radio-checked .ant-radio-inner::after) {
  background-color: #4a6cf7 !important;
}

.dark-input-number {
  background-color: #262626 !important;
  border-color: #303030 !important;
  color: #e0e0e0 !important;
}

.dark-input-number :deep(.ant-input-number-input) {
  color: #e0e0e0 !important;
  background-color: #262626 !important;
}

.dark-input-number :deep(.ant-input-number-handler-wrap) {
  background-color: #303030 !important;
  border-color: #303030 !important;
}

.dark-input-number :deep(.ant-input-number-group-addon) {
  color: #e0e0e0 !important;
  background-color: #303030 !important;
  border-color: #303030 !important;
}

/* Fix for the addon after (% symbol) */
.dark-input-number :deep(.ant-input-number-addon-after) {
  color: #e0e0e0 !important;
  background-color: #303030 !important;
  border-color: #303030 !important;
}

.dark-button {
  background-color: #4a6cf7 !important;
  border-color: #4a6cf7 !important;
  color: #ffffff !important;
  cursor: pointer;
}

.dark-button:hover {
  background-color: #3a5cd8 !important;
  border-color: #3a5cd8 !important;
  color: #ffffff !important;
}

.dark-form :deep(.ant-form-item) {
  color: #e0e0e0 !important;
}

/* Fix placeholder text */
.dark-input :deep(::placeholder) {
  color: rgba(224, 224, 224, 0.5) !important;
}

/* Form footer styles */
.form-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #303030;
  gap: 12px;
}

.form-footer .save-btn {
  background-color: #4a6cf7 !important;
  border-color: #4a6cf7 !important;
  color: white !important;
}

.form-footer .save-btn:hover {
  background-color: #3a5cd8 !important;
  border-color: #3a5cd8 !important;
}
</style>