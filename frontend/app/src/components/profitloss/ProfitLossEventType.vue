<template>
  <span class="d-flex align-center py-4" :class="'flex-column'">
    <span>
      <v-icon color="accent"> {{ icon }} </v-icon>
    </span>
    <span class="mt-2 text-no-wrap">
      {{ name }}
    </span>
  </span>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import i18n from '@/i18n';

const BUY = 'buy';
const SELL = 'sell';
const GAS_COST = 'tx_gas_cost';
const ASSET_MOVEMENT = 'asset_movement';
const LOAN_SETTLEMENT = 'loan_settlement';
const INTEREST_RATE_PAYMENT = 'interest_rate_payment';
const MARGIN_POSITION_CLOSE = 'margin_position_close';
const DEFI_EVENT = 'defi_event';
const LEDGER_ACTION = 'ledger_action';

const EVENT_TYPES = [
  BUY,
  SELL,
  GAS_COST,
  ASSET_MOVEMENT,
  LOAN_SETTLEMENT,
  INTEREST_RATE_PAYMENT,
  MARGIN_POSITION_CLOSE,
  DEFI_EVENT,
  LEDGER_ACTION
] as const;

type EventTypes = typeof EVENT_TYPES[number];

type Resources = { [key in EventTypes]: string };

const icons: Resources = {
  [BUY]: 'mdi-arrow-down',
  [SELL]: 'mdi-arrow-up',
  [GAS_COST]: 'mdi-gas-station',
  [ASSET_MOVEMENT]: 'mdi-swap-horizontal',
  [LOAN_SETTLEMENT]: 'mdi-handshake',
  [INTEREST_RATE_PAYMENT]: 'bank-transfer-in',
  [MARGIN_POSITION_CLOSE]: 'mdi-margin',
  [DEFI_EVENT]: 'mdi-finance',
  [LEDGER_ACTION]: 'mdi-book-open-variant'
};

const names: Resources = {
  [BUY]: i18n.t('profit_loss_event_type.buy').toString(),
  [SELL]: i18n.t('profit_loss_event_type.sell').toString(),
  [GAS_COST]: i18n.t('profit_loss_event_type.gas_cost').toString(),
  [ASSET_MOVEMENT]: i18n.t('profit_loss_event_type.asset_movement').toString(),
  [LOAN_SETTLEMENT]: i18n
    .t('profit_loss_event_type.loan_settlement')
    .toString(),
  [INTEREST_RATE_PAYMENT]: i18n
    .t('profit_loss_event_type.interest_rate_payment')
    .toString(),
  [MARGIN_POSITION_CLOSE]: i18n
    .t('profit_loss_event_type.margin_position_close')
    .toString(),
  [DEFI_EVENT]: i18n.t('profit_loss_event_type.defi_event').toString(),
  [LEDGER_ACTION]: i18n.t('profit_loss_event_type.ledger_action').toString()
};

export default defineComponent({
  name: 'ProfitLossEventType',
  props: {
    type: { required: true, type: String as PropType<EventTypes> }
  },
  setup(props) {
    const { type } = toRefs(props);
    const icon = computed(() => icons[type.value] ?? '');
    const name = computed(() => names[type.value] ?? '');
    return {
      icon,
      name
    };
  }
});
</script>
