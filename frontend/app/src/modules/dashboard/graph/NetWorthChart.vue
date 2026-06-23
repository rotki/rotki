<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { NetValueZoomRange } from '@/modules/dashboard/graph/net-value-stats';
import type { NetValueChartData } from '@/modules/dashboard/graph/types';
import { startPromise } from '@shared/utils';
import VChart from 'vue-echarts';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useNetValueChartConfig } from '@/modules/dashboard/graph/use-net-value-chart-config';
import { useNetValueEventHandlers } from '@/modules/dashboard/graph/use-net-value-event-handlers';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import NewGraphTooltipWrapper from '@/modules/statistics/NewGraphTooltipWrapper.vue';

const zoomRange = defineModel<NetValueZoomRange | undefined>('zoomRange');

const { chartData } = defineProps<{
  chartData: NetValueChartData;
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const chartContainer = useTemplateRef<HTMLElement>('chartContainer');
const chartInstance = useTemplateRef<InstanceType<typeof VChart>>('chartInstance');

const { isDark } = useRotkiTheme();

const { chartOption } = useNetValueChartConfig(() => chartData, zoomRange);

// datazoom fires on every drag frame; debounce the model write so consumers
// only recompute once the user settles on a range.
const updateZoomRange = useDebounceFn((range: NetValueZoomRange | undefined) => {
  set(zoomRange, range);
}, 100);

const { setupChartEventHandlers, setupZoomToolHandler, tooltipData } = useNetValueEventHandlers({
  chartContainer,
  chartData: () => chartData,
  chartInstance,
  // Clicking a snapshot point opens the snapshot editor page for that timestamp.
  onHover: (timestamp: number, _balance: BigNumber) => {
    startPromise(router.push({ name: 'statistics-snapshot-detail', params: { timestamp: timestamp.toString() } }));
  },
  onZoomChange: (range: NetValueZoomRange | undefined) => {
    updateZoomRange(range);
  },
});

watchImmediate(isDark, () => {
  nextTick(setupChartEventHandlers);
});

watchImmediate(chartOption, () => {
  setupZoomToolHandler();
});

function resetZoom(): void {
  get(chartInstance)?.chart?.dispatchAction({ end: 100, start: 0, type: 'dataZoom' });
}

defineExpose({ resetZoom });
</script>

<template>
  <div
    ref="chartContainer"
    class="relative w-full h-full"
    data-testid="net-worth-chart"
  >
    <VChart
      ref="chartInstance"
      class="flex-grow w-full h-[18rem] [&>div:last-child]:!hidden"
      :option="chartOption"
      :update-options="{ notMerge: false }"
      autoresize
    />
  </div>

  <NewGraphTooltipWrapper :tooltip-option="tooltipData">
    <div class="text-rui-text-secondary text-xs mb-1">
      <DateDisplay
        v-if="!tooltipData.currentBalance"
        :timestamp="tooltipData.timestamp"
        milliseconds
      />
      <template v-else>
        {{ t('net_worth_chart.current_balance') }}
      </template>
    </div>
    <FiatDisplay
      class="font-bold"
      :value="tooltipData.value"
    />
  </NewGraphTooltipWrapper>
</template>
