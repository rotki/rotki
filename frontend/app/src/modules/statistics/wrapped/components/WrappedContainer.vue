<script setup lang="ts">
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import { usePremium } from '@/modules/premium/use-premium';
import { useWrappedDateRange } from '../use-wrapped-date-range';
import { useWrappedGnosisPay } from '../use-wrapped-gnosis-pay';
import { useWrappedHistoryEvents } from '../use-wrapped-history-events';
import { useWrappedStatistics } from '../use-wrapped-statistics';
import WrappedExchangeCard from './cards/WrappedExchangeCard.vue';
import WrappedGasCard from './cards/WrappedGasCard.vue';
import WrappedGnosisPayCard from './cards/WrappedGnosisPayCard.vue';
import WrappedProtocolCard from './cards/WrappedProtocolCard.vue';
import WrappedTopDaysCard from './cards/WrappedTopDaysCard.vue';
import WrappedTransactionsCard from './cards/WrappedTransactionsCard.vue';
import WrappedAlerts from './WrappedAlerts.vue';
import WrappedDateFilter from './WrappedDateFilter.vue';
import WrappedHighlights from './WrappedHighlights.vue';
import WrappedSkeletonCards from './WrappedSkeletonCards.vue';

const { t } = useI18n({ useScope: 'global' });
const premium = usePremium();

const {
  end,
  initializeEndDate,
  invalidRange,
  start,
} = useWrappedDateRange();

const {
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

onBeforeMount(async () => {
  initializeEndDate();
  await fetchData();
});

// a new range applies once it settles; a history refresh refetches when it ends, so none is needed during it
watchDebounced([start, end], async () => {
  if (get(invalidRange) || get(refreshing))
    return;
  await fetchData();
}, { debounce: 400 });

/**
 * Whether a fetch has run long enough to say so. Most take well under half a second, and dimming
 * the figures for that long reads as a flicker; they swap in place instead.
 */
const slowFetch = ref<boolean>(false);

const { start: startSlowTimer, stop: stopSlowTimer } = useTimeoutFn(() => {
  set(slowFetch, true);
}, 500, { immediate: false });

watch(loading, (isLoading) => {
  if (isLoading) {
    startSlowTimer();
    return;
  }
  stopSlowTimer();
  set(slowFetch, false);
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <WrappedDateFilter
      v-model:start="start"
      v-model:end="end"
    />

    <WrappedAlerts
      :refreshing="refreshing"
      :premium="premium"
    />

    <WrappedSkeletonCards v-if="loading && summary === undefined" />
    <RuiCard v-else-if="!summary">
      <TableEmptyNotice
        icon="lu-chart-no-axes-column"
        :title="t('wrapped.empty.title')"
        :description="t('wrapped.empty.description')"
      />
    </RuiCard>
    <div
      v-else
      class="flex flex-col gap-4 transition-opacity"
      :class="{ 'opacity-60': slowFetch }"
      :aria-busy="loading"
    >
      <WrappedHighlights
        :eth-on-gas="summary.ethOnGas"
        :transactions="summary.transactionsPerChain"
        :trades="summary.tradesByExchange"
        :top-days="summary.topDaysByNumberOfTransactions"
      />

      <div class="grid gap-4 lg:grid-cols-2">
        <WrappedTransactionsCard :transactions-per-chain="summary.transactionsPerChain" />
        <WrappedProtocolCard :transactions-per-protocol="summary.transactionsPerProtocol" />
        <WrappedGasCard :eth-on-gas-per-address="summary.ethOnGasPerAddress" />
        <WrappedTopDaysCard :top-days-by-number-of-transactions="summary.topDaysByNumberOfTransactions" />
        <WrappedExchangeCard :trades-by-exchange="summary.tradesByExchange" />
        <WrappedGnosisPayCard
          :gnosis-pay-result="gnosisPayResult"
          :show-gnosis-data="showGnosisData"
        />
      </div>
    </div>
  </div>
</template>
