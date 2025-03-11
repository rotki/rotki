<script setup lang="ts">
import type { ValueOverTime } from '@/types/graphs';
import ExportSnapshotDialog from '@/components/dashboard/ExportSnapshotDialog.vue';
import SnapshotActionButton from '@/components/dashboard/SnapshotActionButton.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import GraphTooltipWrapper from '@/components/graphs/GraphTooltipWrapper.vue';
import { useGraph, useTooltip } from '@/composables/graphs';
import { displayDateFormatter } from '@/data/date-formatter';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { assert, bigNumberify, getTimeframeByRange, type NetValue, type Timeframe, type TimeFramePeriod, type Timeframes } from '@rotki/common';
import { Chart, type ChartConfiguration, type ChartOptions, type TooltipOptions } from 'chart.js';

type ActiveRangeButton = 'start' | 'end' | 'both';

const props = defineProps<{
  timeframe: TimeFramePeriod;
  timeframes: Timeframes;
  chartData: NetValue;
}>();

const { t } = useI18n();

const { chartData } = toRefs(props);
const { graphZeroBased, showGraphRangeSelector } = storeToRefs(useFrontendSettingsStore());
const { currencySymbol, dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());
const { isDark } = useRotkiTheme();

const selectedTimestamp = ref<number>(0);
const selectedBalance = ref<number>(0);
const showExportSnapshotDialog = ref<boolean>(false);
const isDblClick = ref<boolean>(false);

const activeRangeButton = ref<ActiveRangeButton>();
const rangeLastX = ref<number>(0);
const rangeRef = ref<any>();

const chartId = 'net-worth-chart__chart';
const tooltipId = 'net-worth-chart__tooltip';
const rangeId = 'net-worth-chart__range';

const { calculateTooltipPosition, tooltipContent, tooltipDisplayOption } = useTooltip(tooltipId);

const balanceData = ref<ValueOverTime[]>([]);
const showVirtualCurrentData = ref<boolean>(true);

let chart: Chart | null = null;
let range: Chart | null = null;

function getChart(): Chart {
  assert(chart, 'chart was null');
  return chart;
}

function getRange(): Chart {
  assert(range, 'range chart was null');
  return range;
}

function updateChart(updateRange = true, calculate = true) {
  chart?.update('resize');
  if (updateRange)
    range?.update('resize');

  if (calculate)
    calculateXRange();
}

interface Bound {
  min: number;
  max: number;
  range: number;
}

const displayedXRange = ref<Bound>({
  max: 0,
  min: 0,
  range: 0,
});

function calculateXRange() {
  if (!chart) {
    set(displayedXRange, {
      max: 0,
      min: 0,
      range: 0,
    });
    return;
  }

  const xAxis = chart.options!.scales!.x!;

  const min = +xAxis.min!;
  const max = +xAxis.max!;

  set(displayedXRange, {
    max,
    min,
    range: max - min,
  });
}

const dataTimeRange = computed<Bound>(() => {
  const data = get(balanceData);
  if (data.length === 0) {
    return {
      max: 0,
      min: 0,
      range: 0,
    };
  }

  const first = data[0];
  const last = data.at(-1);

  if (!last) {
    return {
      max: first.x,
      min: 0,
      range: first.x,
    };
  }

  return {
    max: last.x,
    min: first.x,
    range: last.x - first.x,
  };
});

const dataValueRange = computed<Bound>(() => {
  const data = get(balanceData);
  if (data.length === 0) {
    return {
      max: 0,
      min: 0,
      range: 0,
    };
  }

  const min = Math.min(...data.map(item => item.y));
  const max = Math.max(...data.map(item => item.y));

  return {
    max,
    min,
    range: max - min,
  };
});

const activeTimeframe = computed<Timeframe>(() => {
  const { max, min } = get(displayedXRange);
  return getTimeframeByRange(min, max);
});

const rangeTimeframe = computed<Timeframe>(() => {
  const range = get(dataTimeRange);
  const { max, min } = range;
  return getTimeframeByRange(min, max);
});

watch(activeTimeframe, () => updateChart(true, false));

function transformData({ data, times }: NetValue) {
  const newBalances: ValueOverTime[] = [];

  let showVirtual = true;
  times.forEach((epoch, i) => {
    const value = data[i];

    if (i < times.length - 1 || value.gt(0)) {
      newBalances.push({
        x: epoch * 1000,
        y: value.toNumber(),
      });
    }
    else {
      showVirtual = false;
    }
  });

  set(balanceData, newBalances);
  set(showVirtualCurrentData, showVirtual);

  const chartVal = getChart();
  chartVal.data!.datasets![0].data = newBalances;

  if (get(showGraphRangeSelector)) {
    const rangeVal = getRange();
    rangeVal.data!.datasets![0].data = newBalances;
  }
  resetZoom(true);
}

function clearData() {
  set(balanceData, []);
}

function prepareData() {
  clearData();
  transformData(get(chartData));
}

watch(chartData, () => {
  if (chart) {
    prepareData();
  }
});

const { backgroundColor, baseColor, fontColor, getCanvasCtx, gradient, gridColor } = useGraph(chartId);
const { getCanvasCtx: getRangeCanvasCtx } = useGraph(rangeId);

function createDatasets(isRange = false) {
  const borderColor = () => get(baseColor);

  const dataset = {
    backgroundColor: () => (!isRange ? get(gradient) : 'transparent'),
    borderColor,
    borderWidth: 2,
    cubicInterpolationMode: 'monotone',
    data: [],
    fill: true,
    pointBackgroundColor: 'transparent',
    pointBorderColor: 'transparent',
    pointHoverBackgroundColor: () => get(backgroundColor),
    pointHoverBorderColor: borderColor,
    pointHoverBorderWidth: !isRange ? 2 : 0,
    pointHoverRadius: !isRange ? 6 : 0,
    pointRadius: 1,
    tension: 0.1,
  };

  return [dataset];
}

function createScales(isRange = false) {
  const x: any = {
    border: {
      color: () => get(gridColor),
      display: true,
    },
    grid: {
      display: false,
      drawBorder: !isRange,
    },
    ticks: {
      autoSkip: true,
      color: () => get(fontColor),
      crossAlign: isRange ? 'center' : 'near',
      display: isRange || !get(showGraphRangeSelector),
      maxRotation: 0,
    },
    time: {
      displayFormats: () => {
        const format = isRange
          ? get(rangeTimeframe).xAxisLabelDisplayFormat
          : get(activeTimeframe).xAxisLabelDisplayFormat;

        return {
          day: format,
          month: format,
          week: format,
        };
      },
      stepSize: () => (isRange ? get(rangeTimeframe).xAxisStepSize : get(activeTimeframe).xAxisStepSize),
      unit: () => (isRange ? get(rangeTimeframe).xAxisTimeUnit : get(activeTimeframe).xAxisTimeUnit),
    },
    type: 'time',
  };

  const y: any = {
    beginAtZero: () => (isRange ? false : get(graphZeroBased)),
    display: false,
  };

  if (isRange) {
    y.ticks = {
      stepSize: () => {
        const { range } = get(dataValueRange);

        return range / 100;
      },
    };
  }

  return {
    x,
    y,
  };
}

function createTooltip(): Partial<TooltipOptions> {
  const external = ({ tooltip: tooltipModel }: any) => {
    const element = document.getElementById(tooltipId);
    assert(element, 'No tooltip element found');

    if (tooltipModel.opacity === 0) {
      set(tooltipDisplayOption, {
        ...get(tooltipDisplayOption),
        visible: false,
      });
      return;
    }

    const item = tooltipModel.dataPoints[0];

    const { x, y } = item.parsed;

    const time = displayDateFormatter.format(new Date(x), get(dateDisplayFormat));

    set(tooltipContent, {
      currentBalance: get(showVirtualCurrentData) && item.dataIndex === get(balanceData).length - 1,
      time: `${time}`,
      value: bigNumberify(y),
    });

    nextTick(() => {
      set(tooltipDisplayOption, {
        ...get(tooltipDisplayOption),
        ...calculateTooltipPosition(element, tooltipModel),
      });
    });
  };

  return {
    enabled: false,
    external,
    intersect: false,
    mode: 'index',
  };
}

const oneHourTimestamp = 24 * 60 * 1000;

function createChart(): Chart {
  const context = getCanvasCtx();
  const datasets = createDatasets();
  const scales = createScales();
  const tooltip = createTooltip();

  const options: ChartOptions = {
    animation: (() => !get(activeRangeButton)) as any,
    clip: 8,
    hover: { intersect: false },
    interaction: {
      intersect: false,
      mode: 'index',
    },
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip,
      zoom: {
        limits: {
          x: {
            max: 'original',
            min: 'original',
            minRange: oneHourTimestamp,
          },
        },
        zoom: {
          drag: {
            enabled: get(dataTimeRange).range > oneHourTimestamp,
          },
          mode: 'x',
          onZoomComplete: () => {
            calculateXRange();
          },
        },
      },
    },
    scales: scales as any,
  };

  const config: ChartConfiguration = {
    data: { datasets },
    options,
    type: 'line',
  };

  return new Chart(context, config);
}

watch(dataTimeRange, (dataTimeRange) => {
  if (!chart)
    return;

  chart.options.plugins!.zoom!.zoom!.drag!.enabled = dataTimeRange.range > oneHourTimestamp;
  updateChart(false, false);
});

function createRange() {
  const context = getRangeCanvasCtx();
  const datasets = createDatasets(true);
  const scales = createScales(true);

  const options: ChartOptions = {
    animation: false,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        enabled: false,
      },
    },
    responsive: true,
    scales: scales as any,
  };

  const config: ChartConfiguration = {
    data: { datasets },
    options,
    type: 'line',
  };

  return new Chart(context, config);
}

function setup() {
  chart?.destroy();
  clearData();
  chart = createChart();
  if (get(showGraphRangeSelector)) {
    range?.destroy();
    range = createRange();
  }

  prepareData();
}

onMounted(() => {
  setup();
});

watch(isDark, () => {
  updateChart(true, false);
});

const mouseDownCoor = ref<{ x: number; y: number }>({ x: 0, y: 0 });

function canvasMouseDown(event: MouseEvent) {
  set(mouseDownCoor, {
    x: event.x,
    y: event.y,
  });
}

function canvasMouseUp(event: MouseEvent) {
  const { x, y } = get(mouseDownCoor);

  if (event.x === x && event.y === y)
    canvasClicked(event);
}

function canvasClicked(event: MouseEvent) {
  set(isDblClick, false);
  setTimeout(() => {
    if (get(isDblClick))
      return;

    const axisData = chart?.getElementsAtEventForMode(event, 'index', { intersect: false }, false);

    if (axisData && axisData.length > 0) {
      const index = axisData[0].index;
      const balanceDataVal = get(balanceData);
      const data = balanceDataVal[index];

      if (data.x && data.y && !(get(showVirtualCurrentData) && index === balanceDataVal.length - 1)) {
        set(selectedTimestamp, data.x / 1000);
        set(selectedBalance, data.y);

        set(showExportSnapshotDialog, true);
      }
    }
  }, 200);
}

function resetZoom(updateRange = false) {
  set(isDblClick, true);

  const chart = getChart();
  if (!chart)
    return;

  const xAxis = chart.options!.scales!.x!;

  const { max, min } = get(dataTimeRange);

  xAxis.min = min;
  xAxis.max = max;
  updateChart(updateRange, true);
}

const rangeMarkerStyle = computed<Record<string, string>>(() => {
  const { min: displayedMin, range: displayedRange } = get(displayedXRange);
  const { min, range } = get(dataTimeRange);

  const left = (displayedMin - min) / range;

  const length = displayedRange / range;

  return {
    left: `${left * 100}%`,
    transition: get(activeRangeButton) ? 'none' : '0.3s all',
    width: `${length * 100}%`,
  };
});

function rangeButtonMouseDown(selectedButton: ActiveRangeButton, event: MouseEvent) {
  set(activeRangeButton, selectedButton);
  set(rangeLastX, Math.round(event.pageX));
}

function rangeButtonMouseMove(event: MouseEvent) {
  const activeRangeButtonVal = get(activeRangeButton);
  const rangeElem = get(rangeRef);

  if (!activeRangeButtonVal || !rangeElem)
    return;

  const { width, x: elemX } = rangeElem.getBoundingClientRect();
  const x = Math.round(event.pageX) - elemX;
  const scale = x / width;

  const { max, min, range } = get(dataTimeRange);
  if (range < oneHourTimestamp)
    return;

  const { max: displayedMax, min: displayedMin } = get(displayedXRange);

  const chart = getChart();
  if (!chart)
    return;

  const xAxis = chart.options!.scales!.x!;

  // Drag the start button
  if (activeRangeButtonVal === 'start') {
    const newMin = scale * range + min;
    const leapMax = displayedMax + oneHourTimestamp;

    if (newMin >= leapMax && leapMax <= max) {
      set(activeRangeButton, 'end');
      xAxis.min = displayedMax;
      xAxis.max = leapMax;
    }
    else {
      const closestMin = displayedMax - oneHourTimestamp;
      xAxis.min = Math.min(Math.max(newMin, min), closestMin);
    }
  }
  // Drag the end button
  else if (activeRangeButtonVal === 'end') {
    const newMax = scale * range + min;
    const leapMin = displayedMin - oneHourTimestamp;

    if (newMax <= leapMin && leapMin >= min) {
      set(activeRangeButton, 'start');
      xAxis.max = displayedMin;
      xAxis.min = leapMin;
    }
    else {
      const closestMax = displayedMin + oneHourTimestamp;
      xAxis.max = Math.max(Math.min(newMax, max), closestMax);
    }
  }
  // Drag the area, move both button
  else if (activeRangeButtonVal === 'both') {
    const dist = event.pageX - get(rangeLastX);
    const distScale = dist / width;
    set(rangeLastX, event.pageX);

    const newMin = distScale * range + displayedMin;
    const newMax = distScale * range + displayedMax;

    let limitedMin = Math.max(min, newMin);
    let limitedMax = Math.min(max, newMax);

    if (limitedMin === min)
      limitedMax = Math.min(max, Math.max(limitedMax, limitedMin + oneHourTimestamp));

    if (limitedMax === max)
      limitedMin = Math.max(min, Math.min(limitedMin, limitedMax - oneHourTimestamp));

    xAxis.min = limitedMin;
    xAxis.max = limitedMax;
  }

  updateChart(false, true);
}

function mouseup() {
  set(activeRangeButton, null);
  set(rangeLastX, 0);
}

onMounted(() => {
  window.addEventListener('mouseup', mouseup);
});

onBeforeUnmount(() => {
  window.removeEventListener('mouseup', mouseup);
  chart?.destroy();
  chart = null;
  range?.destroy();
  range = null;
});
</script>

<template>
  <div :class="$style.wrapper">
    <div :class="$style.canvas">
      <canvas
        :id="chartId"
        @mousedown="canvasMouseDown($event)"
        @mouseup="canvasMouseUp($event)"
        @dblclick.stop="resetZoom()"
      />
      <GraphTooltipWrapper :tooltip-option="tooltipDisplayOption">
        <template #content>
          <div class="py-1">
            <div
              class="text-rui-text-secondary text-xs mb-1"
            >
              {{ tooltipContent.currentBalance ? t('net_worth_chart.current_balance') : tooltipContent.time }}
            </div>
            <AmountDisplay
              class="font-bold"
              force-currency
              show-currency="symbol"
              :value="tooltipContent.value"
              :fiat-currency="currencySymbol"
            />
          </div>
        </template>
      </GraphTooltipWrapper>
    </div>

    <div :class="$style.range__wrapper">
      <div
        v-if="showGraphRangeSelector"
        ref="rangeRef"
        :class="$style.range"
        @mousemove="rangeButtonMouseMove($event)"
        @dblclick="resetZoom()"
      >
        <canvas :id="rangeId" />

        <div
          :class="[
            $style.range__marker,
            {
              [$style['range__marker--dark']]: isDark,
            },
          ]"
          :style="rangeMarkerStyle"
          @mousedown="rangeButtonMouseDown('both', $event)"
        >
          <div :class="[$style.range__marker__limit, $style['range__marker__limit--start']]">
            <RuiButton
              :class="$style.range__marker__limit__button"
              :color="isDark ? 'primary' : undefined"
              elevation="1"
              @mousedown.stop="rangeButtonMouseDown('start', $event)"
            >
              <RuiIcon
                :class="$style.range__marker__limit__button__icon"
                name="lu-equal"
              />
            </RuiButton>
          </div>
          <div :class="[$style.range__marker__limit, $style['range__marker__limit--end']]">
            <RuiButton
              :class="$style.range__marker__limit__button"
              :color="isDark ? 'primary' : undefined"
              elevation="1"
              @mousedown.stop="rangeButtonMouseDown('end', $event)"
            >
              <RuiIcon
                :class="$style.range__marker__limit__button__icon"
                name="lu-equal"
              />
            </RuiButton>
          </div>
        </div>
      </div>
      <div
        v-else
        class="grow"
      />

      <div :class="$style.snapshot">
        <SnapshotActionButton />
      </div>
    </div>

    <ExportSnapshotDialog
      v-model="showExportSnapshotDialog"
      :timestamp="selectedTimestamp"
      :balance="selectedBalance"
    />
  </div>
</template>

<style module lang="scss">
.wrapper {
  @apply w-full relative;
}

.canvas {
  @apply w-full relative h-[12.5rem];
}

.range {
  @apply relative mt-2 grow h-[3.75rem];

  max-width: calc(100% - 4rem);

  &__wrapper {
    @apply flex items-center;

    .snapshot {
      @apply shrink-0 w-16 flex justify-center;
    }
  }

  &__marker {
    @apply absolute w-full h-[90%] top-0 z-[2] cursor-all-scroll bg-black/[0.1];

    &__limit {
      @apply flex items-center absolute w-[0.625rem] h-full cursor-ew-resize;

      &--start {
        @apply left-0 -translate-x-1/2;
      }

      &--end {
        @apply right-0 translate-x-1/2;
      }

      &__button {
        @apply w-full h-[1.875rem] cursor-ew-resize;
        @apply min-w-0 p-0 #{!important};

        &:before {
          @apply hidden;
        }

        &__icon {
          @apply scale-50 scale-y-[0.5] rotate-90;
        }
      }
    }
  }
}

:global(.dark) {
  .range {
    &__marker {
      @apply bg-white/[0.1];
    }
  }
}
</style>
