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

<script setup lang="ts">
import { PropType } from 'vue';
import { ProfitLossEventTypeEnum } from '@/types/reports';
import { toCapitalCase } from '@/utils/text';

type Resources = { [key in ProfitLossEventTypeEnum]: string };

const { t } = useI18n();

const icons: Resources = {
  [ProfitLossEventTypeEnum.TRADE]: 'mdi-shuffle-variant',
  [ProfitLossEventTypeEnum.FEE]: 'mdi-fire',
  [ProfitLossEventTypeEnum.ASSET_MOVEMENT]: 'mdi-bank-transfer',
  [ProfitLossEventTypeEnum.MARGIN_POSITION]: 'mdi-margin',
  [ProfitLossEventTypeEnum.LOAN]: 'mdi-handshake',
  [ProfitLossEventTypeEnum.PREFORK_ACQUISITION]: 'mdi-source-fork',
  [ProfitLossEventTypeEnum.LEDGER_ACTION]: 'mdi-book-open-variant',
  [ProfitLossEventTypeEnum.STAKING]: 'mdi-sprout',
  [ProfitLossEventTypeEnum.HISTORY_BASE_ENTRY]: 'mdi-history',
  [ProfitLossEventTypeEnum.TRANSACTION_EVENT]: 'mdi-swap-horizontal'
};

const names: Resources = {
  [ProfitLossEventTypeEnum.TRADE]: t('profit_loss_event_type.trade').toString(),
  [ProfitLossEventTypeEnum.FEE]: t('profit_loss_event_type.fee').toString(),
  [ProfitLossEventTypeEnum.ASSET_MOVEMENT]: t(
    'profit_loss_event_type.asset_movement'
  ).toString(),
  [ProfitLossEventTypeEnum.MARGIN_POSITION]: t(
    'profit_loss_event_type.margin_position'
  ).toString(),
  [ProfitLossEventTypeEnum.LOAN]: t('profit_loss_event_type.loan').toString(),
  [ProfitLossEventTypeEnum.PREFORK_ACQUISITION]: t(
    'profit_loss_event_type.prefork_acquisition'
  ).toString(),
  [ProfitLossEventTypeEnum.LEDGER_ACTION]: t(
    'profit_loss_event_type.ledger_action'
  ).toString(),
  [ProfitLossEventTypeEnum.STAKING]: t(
    'profit_loss_event_type.staking'
  ).toString(),
  [ProfitLossEventTypeEnum.HISTORY_BASE_ENTRY]: t(
    'profit_loss_event_type.history_base_entry'
  ).toString(),
  [ProfitLossEventTypeEnum.TRANSACTION_EVENT]: t(
    'profit_loss_event_type.transaction_event'
  ).toString()
};

const props = defineProps({
  type: { required: true, type: String as PropType<ProfitLossEventTypeEnum> }
});

const { type } = toRefs(props);
const icon = computed(() => icons[get(type)] ?? 'mdi-help');
const name = computed(() => names[get(type)] ?? toCapitalCase(get(type)));
</script>
