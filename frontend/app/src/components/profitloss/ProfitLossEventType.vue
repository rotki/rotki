<template>
  <span class="d-flex align-center" :class="'flex-column'">
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
import { get } from '@vueuse/core';
import i18n from '@/i18n';
import { toCapitalCase } from '@/utils/text';

const TRADE = 'trade';
const FEE = 'fee';
const ASSET_MOVEMENT = 'asset movement';
const MARGIN_POSITION = 'margin position';
const LOAN = 'loan';
const PREFORK_ACQUISITION = 'prefork acquisition';
const LEDGER_ACTION = 'ledger action';
const STAKING = 'staking';
const HISTORY_BASE_ENTRY = 'history base entry';
export const TRANSACTION_EVENT = 'transaction event';

const EVENT_TYPES = [
  TRADE,
  FEE,
  ASSET_MOVEMENT,
  MARGIN_POSITION,
  LOAN,
  PREFORK_ACQUISITION,
  LEDGER_ACTION,
  STAKING,
  HISTORY_BASE_ENTRY,
  TRANSACTION_EVENT
] as const;

type EventTypes = typeof EVENT_TYPES[number];

type Resources = { [key in EventTypes]: string };

const icons: Resources = {
  [TRADE]: 'mdi-shuffle-variant',
  [FEE]: 'mdi-fire',
  [ASSET_MOVEMENT]: 'mdi-bank-transfer',
  [MARGIN_POSITION]: 'mdi-margin',
  [LOAN]: 'mdi-handshake',
  [PREFORK_ACQUISITION]: 'mdi-source-fork',
  [LEDGER_ACTION]: 'mdi-book-open-variant',
  [STAKING]: 'mdi-sprout',
  [HISTORY_BASE_ENTRY]: 'mdi-history',
  [TRANSACTION_EVENT]: 'mdi-swap-horizontal'
};

const names: Resources = {
  [TRADE]: i18n.t('profit_loss_event_type.trade').toString(),
  [FEE]: i18n.t('profit_loss_event_type.fee').toString(),
  [ASSET_MOVEMENT]: i18n.t('profit_loss_event_type.asset_movement').toString(),
  [MARGIN_POSITION]: i18n
    .t('profit_loss_event_type.margin_position')
    .toString(),
  [LOAN]: i18n.t('profit_loss_event_type.loan').toString(),
  [PREFORK_ACQUISITION]: i18n
    .t('profit_loss_event_type.prefork_acquisition')
    .toString(),
  [LEDGER_ACTION]: i18n.t('profit_loss_event_type.ledger_action').toString(),
  [STAKING]: i18n.t('profit_loss_event_type.staking').toString(),
  [HISTORY_BASE_ENTRY]: i18n
    .t('profit_loss_event_type.history_base_entry')
    .toString(),
  [TRANSACTION_EVENT]: i18n
    .t('profit_loss_event_type.transaction_event')
    .toString()
};

export default defineComponent({
  name: 'ProfitLossEventType',
  props: {
    type: { required: true, type: String as PropType<EventTypes> }
  },
  setup(props) {
    const { type } = toRefs(props);
    const icon = computed(() => icons[get(type)] ?? 'mdi-help');
    const name = computed(() => names[get(type)] ?? toCapitalCase(get(type)));
    return {
      icon,
      name
    };
  }
});
</script>
