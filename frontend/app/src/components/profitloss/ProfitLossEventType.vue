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
import { ProfitLossEventTypeEnum } from '@/types/reports';
import { toCapitalCase } from '@/utils/text';

type Resources = { [key in ProfitLossEventTypeEnum]: string };

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
  [ProfitLossEventTypeEnum.TRADE]: i18n
    .t('profit_loss_event_type.trade')
    .toString(),
  [ProfitLossEventTypeEnum.FEE]: i18n
    .t('profit_loss_event_type.fee')
    .toString(),
  [ProfitLossEventTypeEnum.ASSET_MOVEMENT]: i18n
    .t('profit_loss_event_type.asset_movement')
    .toString(),
  [ProfitLossEventTypeEnum.MARGIN_POSITION]: i18n
    .t('profit_loss_event_type.margin_position')
    .toString(),
  [ProfitLossEventTypeEnum.LOAN]: i18n
    .t('profit_loss_event_type.loan')
    .toString(),
  [ProfitLossEventTypeEnum.PREFORK_ACQUISITION]: i18n
    .t('profit_loss_event_type.prefork_acquisition')
    .toString(),
  [ProfitLossEventTypeEnum.LEDGER_ACTION]: i18n
    .t('profit_loss_event_type.ledger_action')
    .toString(),
  [ProfitLossEventTypeEnum.STAKING]: i18n
    .t('profit_loss_event_type.staking')
    .toString(),
  [ProfitLossEventTypeEnum.HISTORY_BASE_ENTRY]: i18n
    .t('profit_loss_event_type.history_base_entry')
    .toString(),
  [ProfitLossEventTypeEnum.TRANSACTION_EVENT]: i18n
    .t('profit_loss_event_type.transaction_event')
    .toString()
};

export default defineComponent({
  name: 'ProfitLossEventType',
  props: {
    type: { required: true, type: String as PropType<ProfitLossEventTypeEnum> }
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
