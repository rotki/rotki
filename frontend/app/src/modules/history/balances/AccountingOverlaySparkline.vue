<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { EChartsOption, LineSeriesOption } from 'echarts';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import VChart from 'vue-echarts';
import { useAmountDisplaySettings } from '@/modules/assets/amount-display';
import { injectAccountingOverlay } from '@/modules/history/balances/use-accounting-overlay-context';
import { useAccountingOverlaySparkline } from '@/modules/history/balances/use-accounting-overlay-sparkline';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { useGraph } from '@/modules/statistics/use-graph';

const { event, balance } = defineProps<{ event: HistoryEventEntry; balance: BigNumber }>();

const { t } = useI18n({ useScope: 'global' });

const context = injectAccountingOverlay();
// Graphs are a premium capability; non-premium tiers simply don't get the sparkline.
const { allowed } = useFeatureAccess(PremiumFeature.GRAPHS_VIEW);
// Respect privacy mode — a balance trend would otherwise leak shape while amounts are hidden.
const { shouldShowAmount } = useAmountDisplaySettings();
// baseColor/gradient match the app's other charts; useGraph also provides the echarts theme.
const { baseColor, gradient } = useGraph();

const eligible = computed<boolean>(() => !!context && get(allowed) && get(shouldShowAmount));

const { loading, points } = useAccountingOverlaySparkline(() => event, () => balance, {
  enabled: eligible,
  seriesFor: async (locationLabel, asset) => context?.series.seriesFor(locationLabel, asset),
});

/** Shown while loading too, so the chart's space is held and the breakdown does not jump when it lands. */
const visible = computed<boolean>(() => get(eligible) && (get(loading) || get(points).length >= 2));

const option = computed<EChartsOption>(() => {
  const data = get(points).map<[number, number]>(point => [point.time * 1000, point.value]);
  const lastIndex = data.length - 1;

  const series: LineSeriesOption = {
    areaStyle: get(gradient),
    data,
    itemStyle: { color: get(baseColor) },
    lineStyle: { color: get(baseColor), width: 1.5 },
    showSymbol: true,
    smooth: true,
    symbol: 'circle',
    // Only the final point (the "you are here" event) shows a dot.
    symbolSize: (_value, params) => (params.dataIndex === lastIndex ? 5 : 0),
    type: 'line',
  };

  return {
    backgroundColor: 'transparent',
    grid: { bottom: 4, left: 4, right: 8, top: 4 },
    series: [series],
    tooltip: {
      appendToBody: true,
      trigger: 'axis',
      valueFormatter: value => Number(value).toLocaleString(undefined, { maximumFractionDigits: 8 }),
    },
    xAxis: { show: false, type: 'time' },
    yAxis: { scale: true, show: false, type: 'value' },
  };
});
</script>

<template>
  <div
    v-if="visible"
    class="flex flex-col gap-1"
    data-testid="overlay-sparkline"
  >
    <div class="text-xs font-medium uppercase tracking-wide opacity-60">
      {{ t('accounting_overlay.over_time') }}
    </div>
    <RuiSkeletonLoader
      v-if="loading"
      class="w-full h-12"
      data-testid="overlay-sparkline-loading"
    />
    <VChart
      v-else
      :option="option"
      autoresize
      class="w-full h-12"
    />
  </div>
</template>
