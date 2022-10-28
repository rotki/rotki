<template>
  <div :class="$style.wrapper">
    <div :class="$style.canvas">
      <canvas
        :id="chartId"
        @mousedown="canvasMouseDown"
        @mouseup="canvasMouseUp"
        @dblclick.stop="resetZoom"
      />
      <graph-tooltip-wrapper :tooltip-option="tooltipDisplayOption">
        <template #content>
          <div>
            <div class="font-weight-bold text-center">
              <amount-display
                force-currency
                show-currency="symbol"
                :value="tooltipContent.value"
                :fiat-currency="currencySymbol"
              />
            </div>
            <div class="rotki-grey--text text-center">
              {{ tooltipContent.time }}
            </div>
          </div>
        </template>
      </graph-tooltip-wrapper>
    </div>

    <div
      v-if="showGraphRangeSelector"
      ref="rangeRef"
      :class="$style.range"
      @mousemove="rangeButtonMouseMove($event)"
      @dblclick="resetZoom"
    >
      <canvas :id="rangeId" />

      <div
        :class="{
          [$style['range__marker']]: true,
          [$style['range__marker--dark']]: dark
        }"
        :style="rangeMarkerStyle"
        @mousedown="rangeButtonMouseDown('both', $event)"
      >
        <div
          :class="{
            [$style['range__marker__limit']]: true,
            [$style['range__marker__limit--start']]: true
          }"
        >
          <v-btn
            :color="dark ? 'black' : 'white'"
            :ripple="false"
            :class="$style['range__marker__limit__button']"
            elevation="1"
            @mousedown.stop="rangeButtonMouseDown('start', $event)"
          >
            <v-icon :class="$style['range__marker__limit__button__icon']">
              mdi-equal
            </v-icon>
          </v-btn>
        </div>
        <div
          :class="{
            [$style['range__marker__limit']]: true,
            [$style['range__marker__limit--end']]: true
          }"
        >
          <v-btn
            :color="dark ? 'black' : 'white'"
            :ripple="false"
            :class="$style['range__marker__limit__button']"
            elevation="1"
            @mousedown.stop="rangeButtonMouseDown('end', $event)"
          >
            <v-icon :class="$style['range__marker__limit__button__icon']">
              mdi-equal
            </v-icon>
          </v-btn>
        </div>
      </div>
    </div>

    <export-snapshot-dialog
      v-model="showExportSnapshotDialog"
      :timestamp="selectedTimestamp"
      :balance="selectedBalance"
    />
  </div>
</template>

<script setup lang="ts">
import {
  getTimeframeByRange,
  Timeframe,
  TimeFramePeriod,
  Timeframes
} from '@rotki/common/lib/settings/graphs';
import { NetValue } from '@rotki/common/lib/statistics';
import {
  Chart,
  ChartConfiguration,
  ChartOptions,
  TooltipOptions
} from 'chart.js';
import dayjs from 'dayjs';
import { PropType } from 'vue';
import { useTheme } from '@/composables/common';
import { useGraph, useTooltip } from '@/composables/graphs';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { ValueOverTime } from '@/types/graphs';
import { assert } from '@/utils/assertions';
import { bigNumberify } from '@/utils/bignumbers';

const GraphTooltipWrapper = defineAsyncComponent(
  () => import('@/components/graphs/GraphTooltipWrapper.vue')
);
const ExportSnapshotDialog = defineAsyncComponent(
  () => import('@/components/dashboard/ExportSnapshotDialog.vue')
);

const props = defineProps({
  timeframe: {
    required: true,
    type: String as PropType<TimeFramePeriod>,
    validator: (value: TimeFramePeriod) =>
      Object.values(TimeFramePeriod).includes(value)
  },
  timeframes: { required: true, type: Object as PropType<Timeframes> },
  chartData: { required: true, type: Object as PropType<NetValue> }
});

const { chartData } = toRefs(props);
const { graphZeroBased, showGraphRangeSelector } = storeToRefs(
  useFrontendSettingsStore()
);
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { dark } = useTheme();

const selectedTimestamp = ref<number>(0);
const selectedBalance = ref<number>(0);
const showExportSnapshotDialog = ref<boolean>(false);
const isDblClick = ref<boolean>(false);

const chartId = 'net-worth-chart__chart';
const tooltipId = 'net-worth-chart__tooltip';
const rangeId = 'net-worth-chart__range';

const { tooltipContent, tooltipDisplayOption, calculateTooltipPosition } =
  useTooltip(tooltipId);

const balanceData = ref<ValueOverTime[]>([]);
const showVirtualCurrentData = ref<boolean>(true);

let chart: Chart | null = null;
let range: Chart | null = null;

const getChart = (): Chart => {
  assert(chart, 'chart was null');
  return chart;
};

const getRange = (): Chart => {
  assert(range, 'range chart was null');
  return range;
};

const updateChart = (
  updateRange: boolean = true,
  calculate: boolean = true
) => {
  chart?.update('resize');
  if (updateRange) {
    range?.update('resize');
  }

  if (calculate) {
    calculateXRange();
  }
};

type Bound = { min: number; max: number; range: number };

const displayedXRange = ref<Bound>({
  min: 0,
  max: 0,
  range: 0
});

const calculateXRange = () => {
  if (!chart) {
    set(displayedXRange, {
      min: 0,
      max: 0,
      range: 0
    });
    return;
  }

  const xAxis = chart.options!.scales!.x!;

  const min = +xAxis.min!;
  const max = +xAxis.max!;

  set(displayedXRange, {
    min,
    max,
    range: max - min
  });
};

const dataTimeRange = computed<Bound>(() => {
  const data = get(balanceData);
  if (data.length === 0)
    return {
      min: 0,
      max: 0,
      range: 0
    };

  const first = data[0];
  const last = data[data.length - 1];

  return {
    min: first.x,
    max: last.x,
    range: last.x - first.x
  };
});

const dataValueRange = computed<Bound>(() => {
  const data = get(balanceData);
  if (data.length === 0)
    return {
      min: 0,
      max: 0,
      range: 0
    };

  const min = Math.min(...data.map(item => item.y));
  const max = Math.max(...data.map(item => item.y));

  return {
    min,
    max,
    range: max - min
  };
});

const activeTimeframe = computed<Timeframe>(() => {
  const { min, max } = get(displayedXRange);
  return getTimeframeByRange(min, max);
});

const rangeTimeframe = computed<Timeframe>(() => {
  const range = get(dataTimeRange);
  const { min, max } = range;
  return getTimeframeByRange(min, max);
});

watch(activeTimeframe, () => updateChart(true, false));

const transformData = ({ times, data }: NetValue) => {
  const newBalances: ValueOverTime[] = [];

  let showVirtual = true;
  times.forEach((epoch, i) => {
    const value = data[i];

    if (i < times.length - 1 || value > 0) {
      newBalances.push({
        x: epoch * 1000,
        y: value
      });
    } else {
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
  resetZoom();
};

const clearData = () => {
  set(balanceData, []);
};

const prepareData = () => {
  clearData();
  transformData(get(chartData));
};

watch(chartData, () => {
  prepareData();
});

const { getCanvasCtx, baseColor, gradient, fontColor, gridColor } =
  useGraph(chartId);

const { getCanvasCtx: getRangeCanvasCtx } = useGraph(rangeId);

const createDatasets = (isRange: boolean = false) => {
  const dataset = {
    data: [],
    tension: 0.1,
    fill: true,
    backgroundColor: () => (!isRange ? get(gradient) : 'transparent'),
    borderColor: () => get(baseColor),
    borderWidth: 2,
    pointBorderWidth: 0,
    pointHoverBorderWidth: !isRange ? 2 : 0,
    pointBorderColor: () => get(baseColor),
    pointHoverBorderColor: 'white',
    pointBackgroundColor: !isRange ? 'white' : 'transparent',
    pointHoverBackgroundColor: () => (!isRange ? get(baseColor) : 'transparent')
  };

  return [dataset];
};

const createScales = (isRange: boolean = false) => {
  const x: any = {
    type: 'time',
    grid: {
      display: false,
      drawBorder: !isRange
    },
    ticks: {
      display: isRange || !get(showGraphRangeSelector),
      color: () => get(fontColor),
      autoSkip: true,
      maxRotation: 0,
      crossAlign: isRange ? 'center' : 'near'
    },
    time: {
      unit: () =>
        isRange
          ? get(rangeTimeframe).xAxisTimeUnit
          : get(activeTimeframe).xAxisTimeUnit,
      stepSize: () =>
        isRange
          ? get(rangeTimeframe).xAxisStepSize
          : get(activeTimeframe).xAxisStepSize,
      displayFormats: () => {
        const format = isRange
          ? get(rangeTimeframe).xAxisLabelDisplayFormat
          : get(activeTimeframe).xAxisLabelDisplayFormat;

        return {
          month: format,
          week: format,
          day: format
        };
      }
    }
  };

  const y: any = {
    display: false,
    grid: {
      color: () => get(gridColor),
      borderColor: () => get(gridColor)
    },
    beginAtZero: () => (isRange ? false : get(graphZeroBased))
  };

  if (isRange) {
    y.ticks = {
      stepSize: () => {
        const { range } = get(dataValueRange);

        return range / 100;
      }
    };
  }

  return {
    x,
    y
  };
};

const createTooltip = (): Partial<TooltipOptions> => {
  const external = ({ tooltip: tooltipModel }: any) => {
    const element = document.getElementById(tooltipId);
    assert(element, 'No tooltip element found');

    if (tooltipModel.opacity === 0) {
      tooltipDisplayOption.value = {
        ...get(tooltipDisplayOption),
        visible: false
      };
      return;
    }

    const item = tooltipModel.dataPoints[0];
    const { x, y } = item.parsed;

    const time = dayjs(x).format(get(activeTimeframe).tooltipTimeFormat);

    tooltipContent.value = {
      value: bigNumberify(y),
      time: `${time}`
    };

    nextTick(() => {
      tooltipDisplayOption.value = {
        ...get(tooltipDisplayOption),
        ...calculateTooltipPosition(element, tooltipModel)
      };
    });
  };

  return {
    enabled: false,
    mode: 'index',
    intersect: false,
    external
  };
};

const oneDayTimestamp = 24 * 60 * 60 * 1000;

const createChart = (): Chart => {
  const context = getCanvasCtx();
  const datasets = createDatasets();
  const scales = createScales();
  const tooltip = createTooltip();

  const options: ChartOptions = {
    animation: (() => !get(activeRangeButton)) as any,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false
    },
    hover: { intersect: false },
    elements: {
      point: {
        radius: 0,
        hoverRadius: 6,
        pointStyle: 'circle'
      }
    },
    scales: scales as any,
    plugins: {
      legend: { display: false },
      tooltip,
      zoom: {
        limits: {
          x: {
            min: 'original',
            max: 'original',
            minRange: oneDayTimestamp
          }
        },
        zoom: {
          drag: {
            enabled: get(dataTimeRange).range > oneDayTimestamp
          },
          mode: 'x',
          onZoomComplete: () => {
            calculateXRange();
          }
        }
      }
    }
  };

  const config: ChartConfiguration = {
    type: 'line',
    data: { datasets },
    options
  };

  return new Chart(context, config);
};

watch(dataTimeRange, dataTimeRange => {
  if (!chart) return;
  chart.options.plugins!.zoom!.zoom!.drag!.enabled =
    dataTimeRange.range > oneDayTimestamp;
  updateChart(false, false);
});

const createRange = () => {
  const context = getRangeCanvasCtx();
  const datasets = createDatasets(true);
  const scales = createScales(true);

  const options: ChartOptions = {
    animation: false,
    responsive: true,
    maintainAspectRatio: false,
    scales: scales as any,
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        enabled: false
      }
    }
  };

  const config: ChartConfiguration = {
    type: 'line',
    data: { datasets },
    options
  };

  return new Chart(context, config);
};

const setup = () => {
  chart?.destroy();
  clearData();
  chart = createChart();
  if (get(showGraphRangeSelector)) {
    range = createRange();
  }
  prepareData();
};

onMounted(() => {
  setup();
});

watch(dark, () => {
  updateChart(true, false);
});

const mouseDownCoor = ref<{ x: number; y: number }>({ x: 0, y: 0 });

const canvasMouseDown = (event: MouseEvent) => {
  set(mouseDownCoor, {
    x: event.x,
    y: event.y
  });
};

const canvasMouseUp = (event: MouseEvent) => {
  const { x, y } = get(mouseDownCoor);

  if (event.x === x && event.y === y) {
    canvasClicked(event);
  }
};

const canvasClicked = (event: MouseEvent) => {
  set(isDblClick, false);
  setTimeout(() => {
    if (get(isDblClick)) return;

    const axisData = chart?.getElementsAtEventForMode(
      event,
      'index',
      { intersect: false },
      false
    );

    if (axisData && axisData.length > 0) {
      const index = axisData[0].index;
      const balanceDataVal = get(balanceData);
      const data = balanceDataVal[index];

      if (
        data.x &&
        data.y &&
        !(showVirtualCurrentData.value && index === balanceDataVal.length - 1)
      ) {
        set(selectedTimestamp, data.x / 1000);
        set(selectedBalance, data.y);

        set(showExportSnapshotDialog, true);
      }
    }
  }, 200);
};

const resetZoom = () => {
  set(isDblClick, true);

  const chart = getChart();
  if (!chart) return;
  const xAxis = chart.options!.scales!.x!;

  const { min, max } = get(dataTimeRange);

  xAxis.min = min;
  xAxis.max = max;
  updateChart(false, true);
};

type ActiveRangeButton = 'start' | 'end' | 'both';

const activeRangeButton = ref<ActiveRangeButton | null>(null);
const rangeLastX = ref<number>(0);

const rangeRef = ref<any>(null);

const rangeMarkerStyle = computed<Record<string, string>>(() => {
  const { min: displayedMin, range: displayedRange } = get(displayedXRange);
  const { min, range } = get(dataTimeRange);

  const left = (displayedMin - min) / range;

  const length = displayedRange / range;

  return {
    left: `${left * 100}%`,
    width: `${length * 100}%`,
    transition: get(activeRangeButton) ? 'none' : '0.3s all'
  };
});

const rangeButtonMouseDown = (
  selectedButton: ActiveRangeButton,
  event: MouseEvent
) => {
  set(activeRangeButton, selectedButton);
  set(rangeLastX, Math.round(event.pageX));
};

const rangeButtonMouseMove = (event: MouseEvent) => {
  const activeRangeButtonVal = get(activeRangeButton);
  const rangeElem = get(rangeRef);

  if (!activeRangeButtonVal || !rangeElem) return;

  const { x: elemX, width } = rangeElem.getBoundingClientRect();
  const x = Math.round(event.pageX) - elemX;
  const scale = x / width;

  const { min, max, range } = get(dataTimeRange);
  if (range < oneDayTimestamp) return;
  const { min: displayedMin, max: displayedMax } = get(displayedXRange);

  const chart = getChart();
  if (!chart) return;
  const xAxis = chart.options!.scales!.x!;

  // Drag the start button
  if (activeRangeButtonVal === 'start') {
    const newMin = scale * range + min;
    const leapMax = displayedMax + oneDayTimestamp;

    if (newMin >= leapMax && leapMax <= max) {
      set(activeRangeButton, 'end');
      xAxis.min = displayedMax;
      xAxis.max = leapMax;
    } else {
      const closestMin = displayedMax - oneDayTimestamp;
      xAxis.min = Math.min(Math.max(newMin, min), closestMin);
    }
  }
  // Drag the end button
  else if (activeRangeButtonVal === 'end') {
    const newMax = scale * range + min;
    const leapMin = displayedMin - oneDayTimestamp;

    if (newMax <= leapMin && leapMin >= min) {
      set(activeRangeButton, 'start');
      xAxis.max = displayedMin;
      xAxis.min = leapMin;
    } else {
      const closestMax = displayedMin + oneDayTimestamp;
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

    if (limitedMin === min) {
      limitedMax = Math.min(
        max,
        Math.max(limitedMax, limitedMin + oneDayTimestamp)
      );
    }

    if (limitedMax === max) {
      limitedMin = Math.max(
        min,
        Math.min(limitedMin, limitedMax - oneDayTimestamp)
      );
    }

    xAxis.min = limitedMin;
    xAxis.max = limitedMax;
  }

  updateChart(false, true);
};

const mouseup = () => {
  set(activeRangeButton, null);
  set(rangeLastX, 0);
};

onMounted(() => {
  window.addEventListener('mouseup', mouseup);
});

onBeforeUnmount(() => {
  window.removeEventListener('mouseup', mouseup);
});
</script>

<style module lang="scss">
.wrapper {
  width: 100%;
  position: relative;
}

.canvas {
  position: relative;
  height: 200px;
  width: 100%;
}

.range {
  margin-top: 0.5rem;
  height: 60px;
  position: relative;

  &__marker {
    height: 90%;
    background: rgba(0, 0, 0, 0.2);
    position: absolute;
    width: 100%;
    top: 0;
    z-index: 2;
    cursor: all-scroll;

    &--dark {
      background: rgba(255, 255, 255, 0.1);
    }

    &__limit {
      height: 100%;
      width: 10px;
      position: absolute;
      display: flex;
      align-items: center;
      cursor: ew-resize;

      &--start {
        left: 0;
        transform: translateX(-50%);
      }

      &--end {
        right: 0;
        transform: translateX(50%);
      }

      &__button {
        height: 30px;
        width: 100%;
        min-width: 0 !important;
        padding: 0 !important;
        cursor: ew-resize;

        &:before {
          display: none;
        }

        &__icon {
          transform: scaleX(0.5) scaleY(0.8) rotate(90deg);
        }
      }
    }
  }
}
</style>
