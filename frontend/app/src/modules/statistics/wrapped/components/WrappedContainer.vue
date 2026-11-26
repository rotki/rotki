<script setup lang="ts">
import { RuiCard } from '@rotki/ui-library';
import { useTimeoutFn } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { onBeforeMount, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { watchDebounced } from '@/modules/core/common/async/scoped-timers';
import TableEmptyNotice from '@/modules/core/table/TableEmptyNotice.vue';
import { usePremium } from '@/modules/premium/use-premium';
import { useWrappedDateRange } from '../use-wrapped-date-range';
import { useWrappedGnosisPay } from '../use-wrapped-gnosis-pay';
import { useWrappedHistoryEvents } from '../use-wrapped-history-events';
import { useWrappedStatistics } from '../use-wrapped-statistics';
import WrappedAlerts from './WrappedAlerts.vue';
import WrappedDateFilter from './WrappedDateFilter.vue';
import WrappedSkeletonCards from './WrappedSkeletonCards.vue';
import WrappedSummary from './WrappedSummary.vue';

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
      v-model:end="end"
      :start="start"
      @update:start="start = $event ?? 0"
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
      <WrappedSummary
        :summary="summary"
        :gnosis-pay-result="gnosisPayResult"
        :show-gnosis-data="showGnosisData"
      />
    </div>
  </div>
</template>
