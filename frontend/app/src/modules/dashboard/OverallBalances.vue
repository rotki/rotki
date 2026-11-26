<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { RuiButton, RuiCard, RuiIcon, RuiProgress } from '@rotki/ui-library';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { useBalanceView } from '@/modules/balances/view/use-balance-view';
import { computeNetValueDelta, type NetValueZoomRange } from '@/modules/dashboard/graph/net-value-stats';
import NetWorthChart from '@/modules/dashboard/graph/NetWorthChart.vue';
import { useNetValueTimeframe } from '@/modules/dashboard/graph/use-net-value-timeframe';
import AssetsBySource from '@/modules/dashboard/holdings/components/AssetsBySource.vue';
import NetWorthHeadline from '@/modules/dashboard/NetWorthHeadline.vue';
import SnapshotActionButton from '@/modules/dashboard/SnapshotActionButton.vue';
import { useNetWorthLoading } from '@/modules/dashboard/use-net-worth-loading';
import TimeframeSelector from '@/modules/statistics/TimeframeSelector.vue';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

const selectedKind = defineModel<SourceKind | undefined>('selectedKind');

const { t } = useI18n({ useScope: 'global' });

const netWorthChart = useTemplateRef<InstanceType<typeof NetWorthChart>>('netWorthChart');

const statisticsStore = useStatisticsStore();
const { netValueError, totalNetWorth } = storeToRefs(statisticsStore);

const { available: viewAvailable, isHistory } = useBalanceView();
const { loadingBlockchainBalances: isLoading } = useBalancesLoading();

const loadingNetWorth = useNetWorthLoading();

/**
 * Whether the delta and the chart have a total worth drawing.
 *
 * @remarks
 * Wider than the header's own latch, which waits for the first load only. A delta computed from a
 * half-loaded total is a number that is wrong while it moves, so these two wait for every load. The
 * latch is what carries them through the first frames, before any balance activity is submitted.
 */
const isBusy = computed<boolean>(() => get(loadingNetWorth) || get(isLoading));

const { fetchNetValue } = useStatisticsDataFetching();

const zoomRange = ref<NetValueZoomRange>();

const { setTimeframe, timeframe, timeframeData, visibleTimeframes } = useNetValueTimeframe({
  onTimeframeChange: () => get(netWorthChart)?.resetZoom(),
  zoomRange,
});

/** Some snapshots are converted at a stand-in rate while their own day's rate is not known yet. */
const hasEstimates = computed<boolean>(() => get(timeframeData).estimated?.some(Boolean) === true);

const stats = computed(() => {
  const { data, times } = get(timeframeData);
  return computeNetValueDelta(data, times, get(totalNetWorth), get(zoomRange));
});

const startingValue = computed<BigNumber>(() => get(stats).startingValue);
const balanceDelta = computed<BigNumber>(() => get(stats).balanceDelta);

const percentage = computed<string>(() => {
  const bigNumber = get(balanceDelta).div(get(startingValue)).multipliedBy(100);
  return bigNumber.isFinite() ? bigNumber.toFormat(2) : '-';
});
</script>

<template>
  <RuiCard
    class="overall-balances"
    :class="{ 'border-rui-primary!': isHistory }"
    :class-names="{ content: 'grid grid-cols-1 lg:grid-cols-12 p-2 gap-4 overflow-hidden' }"
  >
    <NetWorthHeadline
      class="lg:col-span-4 lg:px-4 lg:pt-4"
      :balance-delta="balanceDelta"
      :percentage="percentage"
      :loading-net-worth="loadingNetWorth"
      :busy="isBusy"
      :approximate="hasEstimates"
    />
    <div class="lg:col-span-8 lg:row-span-2 flex flex-col">
      <div class="flex justify-start lg:justify-end items-center md:pt-4 gap-4">
        <TimeframeSelector
          :model-value="timeframe"
          :visible-timeframes="visibleTimeframes"
          @update:model-value="setTimeframe($event)"
        />

        <SnapshotActionButton />
      </div>
      <div class="relative">
        <NetWorthChart
          ref="netWorthChart"
          v-model:zoom-range="zoomRange"
          :chart-data="timeframeData"
        />
        <div
          v-if="isBusy"
          class="absolute top-0 h-full w-full flex flex-col gap-3 items-center justify-center text-caption text-rui-text-secondary bg-rui-surface/80 dark:bg-rui-surface/90 z-6"
        >
          <RuiProgress
            circular
            variant="indeterminate"
            color="primary"
            size="24"
            thickness="2"
          />
          {{ t('overall_balances.loading') }}
        </div>
        <div
          v-else-if="netValueError"
          class="absolute top-0 h-full w-full flex flex-col gap-3 items-center justify-center px-4 text-center bg-rui-surface/80 dark:bg-rui-surface/90 z-6"
          data-testid="net-value-error"
        >
          <div class="text-rui-text-secondary text-caption">
            {{ t('overall_balances.net_value_error') }}
          </div>
          <div class="text-rui-text-secondary text-caption break-all">
            {{ netValueError }}
          </div>
          <RuiButton
            size="sm"
            color="primary"
            variant="outlined"
            data-testid="net-value-retry"
            @click="fetchNetValue()"
          >
            {{ t('common.actions.retry') }}
          </RuiButton>
        </div>
      </div>
      <p
        v-if="viewAvailable"
        class="flex items-center gap-1 px-2 text-xs text-rui-text-secondary"
        data-testid="overall-balances-chart-queried"
      >
        <RuiIcon
          name="lu-info"
          size="14"
        />
        {{ t('balance_view.chart_live') }}
      </p>
    </div>
    <AssetsBySource
      v-model:selected-kind="selectedKind"
      class="lg:col-span-4 lg:col-start-1 lg:row-start-2 lg:px-4 lg:pb-4 self-start"
    />
  </RuiCard>
</template>
