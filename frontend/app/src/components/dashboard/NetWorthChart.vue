<script setup lang="ts">
import ExportSnapshotDialog from '@/components/dashboard/ExportSnapshotDialog.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import NewGraphTooltipWrapper from '@/components/graphs/NewGraphTooltipWrapper.vue';
import { useGraphTooltip, useNewGraph } from '@/composables/graphs';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { type BigNumber, type NetValue, Zero } from '@rotki/common';
import VChart from 'vue-echarts';

const props = defineProps<{
  chartData: NetValue;
}>();

const { t } = useI18n({ useScope: 'global' });

const chartContainer = ref<HTMLElement>();
const chartInstance = ref<InstanceType<typeof VChart>>();

const selectedTimestamp = ref<number>(0);
const selectedBalance = ref<BigNumber>(Zero);
const showExportSnapshotDialog = ref<boolean>(false);

const lastHover = ref<{ timestamp: number; value: BigNumber } | null>(null);
const mousePos = ref({ x: 0, y: 0 });

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { graphZeroBased, showGraphRangeSelector } = storeToRefs(useFrontendSettingsStore());

const { resetTooltipData, tooltipData } = useGraphTooltip();
const { baseColor, gradient } = useNewGraph();

function resetTooltip() {
  resetTooltipData();
  set(lastHover, null);
}

const chartData = computed(() => {
  const { data, times } = get(props.chartData);
  if (!times || !data || times.length === 0 || data.length === 0) {
    return [];
  }
  return times.map((epoch, i) => [epoch * 1000, Number(data[i])]);
});

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  dataZoom: [
    ...(!get(showGraphRangeSelector)
      ? []
      : [{
          handleSize: 20,
          height: 30,
          rangeMode: ['value', 'value'],
          realtime: true,
          show: true,
          showDetail: false,
          type: 'slider',
          zoomOnMouseWheel: false,
        }]),
    {
      rangeMode: ['value', 'value'],
      showDetail: false,
      type: 'inside',
      zoomOnMouseDown: true,
    },
  ],
  grid: {
    bottom: get(showGraphRangeSelector) ? 56 : 16,
    containLabel: true,
    left: 16,
    right: 16,
    top: 16,
  },
  series: [
    {
      areaStyle: get(gradient),
      data: get(chartData),
      itemStyle: {
        color: get(baseColor),
      },
      lineStyle: {
        color: get(baseColor),
      },
      showSymbol: false,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      type: 'line',
    },
  ],
  tooltip: {
    trigger: 'axis',
  },
  xAxis: {
    axisLabel: { show: true },
    axisLine: { show: false },
    axisTick: { show: false },
    type: 'time',
  },
  yAxis: {
    axisLabel: { show: false },
    min: get(graphZeroBased) ? 0 : undefined,
    splitLine: { show: false },
    type: 'value',
  },
}));

const { isDark } = useRotkiTheme();

watchImmediate(isDark, () => {
  nextTick(() => {
    let clickTimer: ReturnType<typeof setTimeout> | null = null;

    const chartVal = get(chartInstance);
    const container = get(chartContainer);

    if (container && chartVal?.chart) {
      const instance = chartVal.chart;

      // Adjust the tooltip content and position
      instance.on('updateAxisPointer', (event: any) => {
        const { axesInfo, dataIndex } = event;
        const xAxisInfo = axesInfo?.[0];

        const netValues = props.chartData.data;
        const netValue = netValues[dataIndex];

        const currentBalance = dataIndex === netValues.length - 1;
        if (!xAxisInfo || !netValue) {
          resetTooltip();
          return;
        }

        const timestamp = xAxisInfo.value;

        // Start from the last known mouse coordinates
        const pos = get(mousePos);
        let cursorX = pos.x + 20;
        let cursorY = pos.y + 20;

        // Estimate tooltip size for boundary flipping
        const tooltipWidth = 150;
        const tooltipHeight = 60;

        const containerRect = container.getBoundingClientRect();
        if (containerRect) {
          // If overflowing to the right => flip to left
          if (cursorX + tooltipWidth > containerRect.width) {
            cursorX = pos.x - 20 - tooltipWidth;
          }
          // If overflowing bottom => flip up
          if (cursorY + tooltipHeight > containerRect.height) {
            cursorY = pos.y - 20 - tooltipHeight;
          }
        }

        set(tooltipData, {
          currentBalance,
          timestamp,
          value: netValue,
          visible: true,
          x: cursorX,
          y: cursorY,
        });

        if (currentBalance) {
          set(lastHover, null);
        }
        else {
          set(lastHover, {
            timestamp,
            value: netValue,
          });
        }
      });

      // Double-click => reset zoom
      instance.getZr().on('dblclick', () => {
        if (clickTimer) {
          clearTimeout(clickTimer);
          clickTimer = null;
        }
        instance.dispatchAction({ end: 100, start: 0, type: 'dataZoom' });
      });

      instance.getZr().on('mousemove', (event: MouseEvent) => {
        set(mousePos, {
          x: event.offsetX,
          y: event.offsetY,
        });
      });

      // Hide tooltip when pointer leaves the entire chart
      instance.getZr().on('globalout', () => {
        resetTooltip();
      });
    }

    if (container) {
      container.addEventListener('click', () => {
        if (clickTimer) {
          clearTimeout(clickTimer);
          clickTimer = null;
        }
        else {
          clickTimer = setTimeout(() => {
            clickTimer = null;
            const hover = get(lastHover);
            if (hover) {
              set(selectedTimestamp, hover.timestamp / 1000);
              set(selectedBalance, hover.value);
              set(showExportSnapshotDialog, true);
            }
          }, 200);
        }
      });
    }
  });
});
</script>

<template>
  <div
    ref="chartContainer"
    class="relative w-full h-full"
  >
    <VChart
      ref="chartInstance"
      class="flex-grow w-full h-[16rem] [&>div:last-child]:!hidden"
      :option="chartOption"
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
    <AmountDisplay
      class="font-bold"
      force-currency
      show-currency="symbol"
      :value="tooltipData.value"
      :fiat-currency="currencySymbol"
    />
  </NewGraphTooltipWrapper>

  <ExportSnapshotDialog
    v-if="selectedTimestamp && selectedBalance"
    v-model="showExportSnapshotDialog"
    :timestamp="selectedTimestamp"
    :balance="selectedBalance"
  />
</template>
