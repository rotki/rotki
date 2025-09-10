<script setup lang="ts">
import { get } from '@vueuse/shared';
import { usePremium } from '@/composables/premium';
import { useWrappedDateRange } from '../composables/use-wrapped-date-range';
import { useWrappedGnosisPay } from '../composables/use-wrapped-gnosis-pay';
import { useWrappedHistoryEvents } from '../composables/use-wrapped-history-events';
import { useWrappedStatistics } from '../composables/use-wrapped-statistics';
import WrappedExchangeCard from './cards/WrappedExchangeCard.vue';
import WrappedGasCard from './cards/WrappedGasCard.vue';
import WrappedGnosisPayCard from './cards/WrappedGnosisPayCard.vue';
import WrappedProtocolCard from './cards/WrappedProtocolCard.vue';
import WrappedTopDaysCard from './cards/WrappedTopDaysCard.vue';
import WrappedTransactionsCard from './cards/WrappedTransactionsCard.vue';
import WrappedAlerts from './WrappedAlerts.vue';
import WrappedDateFilter from './WrappedDateFilter.vue';
import WrappedHeader from './WrappedHeader.vue';
import WrappedSkeletonCards from './WrappedSkeletonCards.vue';

const props = defineProps<{
  highlightedYear?: number;
}>();

const { t } = useI18n({ useScope: 'global' });
const premium = usePremium();

const {
  end,
  getYearRange,
  initializeEndDate,
  invalidRange,
  start,
} = useWrappedDateRange();

const {
  isFirstLoad,
  refreshing,
} = useWrappedHistoryEvents(start);

const {
  fetchData,
  loading,
  summary,
} = useWrappedStatistics(start, end, refreshing);

const {
  gnosisPayResult,
  showGnosisData,
} = useWrappedGnosisPay(summary);

const isHighlightedYear = computed<boolean>(() => {
  if (!isDefined(props.highlightedYear))
    return false;

  const range = getYearRange(props.highlightedYear);
  return get(start) === range.start && get(end) === range.end;
});

onBeforeMount(async () => {
  initializeEndDate();
  await fetchData();
});

defineExpose({
  isHighlightedYear,
  loading,
});
</script>

<template>
  <div class="flex flex-col gap-6 py-4 px-2">
    <WrappedHeader
      :highlighted-year="highlightedYear"
      :is-highlighted-year="isHighlightedYear"
    />

    <WrappedAlerts
      :is-first-load="isFirstLoad()"
      :refreshing="refreshing"
      :premium="premium"
    />

    <WrappedDateFilter
      v-model:start="start"
      v-model:end="end"
      :loading="loading"
      :refreshing="refreshing"
      :invalid-range="invalidRange"
      @fetch="fetchData()"
    />

    <template v-if="loading">
      <WrappedSkeletonCards />
    </template>
    <div
      v-else-if="!summary"
      class="p-4 text-center"
    >
      {{ t('data_table.no_data') }}
    </div>
    <template v-else>
      <WrappedGasCard
        :eth-on-gas="summary.ethOnGas"
        :eth-on-gas-per-address="summary.ethOnGasPerAddress"
      />

      <WrappedExchangeCard
        :trades-by-exchange="summary.tradesByExchange"
      />

      <WrappedTransactionsCard
        :transactions-per-chain="summary.transactionsPerChain"
      />

      <WrappedGnosisPayCard
        :gnosis-pay-result="gnosisPayResult"
        :show-gnosis-data="showGnosisData"
      />

      <WrappedTopDaysCard
        :top-days-by-number-of-transactions="summary.topDaysByNumberOfTransactions"
      />

      <WrappedProtocolCard
        :transactions-per-protocol="summary.transactionsPerProtocol"
      />
    </template>
  </div>
</template>
