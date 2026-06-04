<script setup lang="ts">
import type { EChartsOption, LineSeriesOption } from 'echarts';
import type { SparklinePoint } from '@/modules/history/balances/use-accounting-overlay';
import VChart from 'vue-echarts';
import { useAmountDisplaySettings } from '@/modules/assets/amount-display';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { useGraph } from '@/modules/statistics/use-graph';

const { points } = defineProps<{ points: SparklinePoint[] }>();

const { t } = useI18n({ useScope: 'global' });

// Graphs are a premium capability; non-premium tiers simply don't get the sparkline.
const { allowed } = useFeatureAccess(PremiumFeature.GRAPHS_VIEW);
// Respect privacy mode — a balance trend would otherwise leak shape while amounts are hidden.
const { shouldShowAmount } = useAmountDisplaySettings();
// baseColor/gradient match the app's other charts; useGraph also provides the echarts theme.
const { baseColor, gradient } = useGraph();

const visible = computed<boolean>(() => get(allowed) && get(shouldShowAmount) && points.length >= 2);

const option = computed<EChartsOption>(() => {
  const data = points.map<[number, number]>(point => [point.time * 1000, point.value]);
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
      // The chart lives inside a teleported RuiMenu; render the tooltip on <body> so the menu's
      // bounds don't clip it.
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
    <VChart
      :option="option"
      autoresize
      class="w-full h-12"
    />
  </div>
</template>
