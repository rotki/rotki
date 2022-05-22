<template>
  <div :class="$style.wrapper">
    <div :class="$style.canvas">
      <canvas :id="canvasId" @click="canvasClicked" />
      <div
        v-if="tooltipOption"
        :id="tooltipOption.id"
        :class="{
          [$style.tooltip]: true,
          [$style['tooltip-dark']]: dark,
          [$style['tooltip-show']]: tooltipOption.visible
        }"
        :data-align-x="tooltipOption.xAlign"
        :data-align-y="tooltipOption.yAlign"
        :style="{
          left: `${tooltipOption.left}px`,
          top: `${tooltipOption.top}px`
        }"
      >
        <div>
          <div class="font-weight-bold text-center">
            {{ tooltip.value }}
          </div>
          <div class="rotki-grey--text text-center">
            {{ tooltip.time }}
          </div>
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

<script lang="ts">
import { BigNumber } from '@rotki/common';
import {
  Timeframe,
  TimeFramePeriod,
  Timeframes
} from '@rotki/common/lib/settings/graphs';
import { NetValue } from '@rotki/common/lib/statistics';
import {
  computed,
  defineComponent,
  nextTick,
  onMounted,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import {
  Chart,
  ChartConfiguration,
  ChartDataSets,
  ChartElementsOptions,
  ChartOptions,
  ChartTooltipModel,
  ChartTooltipOptions,
  ChartXAxe,
  ChartYAxe,
  LinearScale,
  TimeDisplayFormat,
  TimeScale,
  TimeUnit
} from 'chart.js';
import dayjs from 'dayjs';
import ExportSnapshotDialog from '@/components/dashboard/ExportSnapshotDialog.vue';
import { setupThemeCheck } from '@/composables/common';
import { setupGeneralSettings } from '@/composables/session';
import { setupSettings } from '@/composables/settings';
import { assert } from '@/utils/assertions';
import { bigNumberify } from '@/utils/bignumbers';

export interface ValueOverTime {
  readonly x: Date;
  readonly y: number;
}

const useTooltip = (id: string) => {
  type TooltipOption = {
    visible: boolean;
    id: string;
    left: number;
    top: number;
    xAlign: string;
    yAlign: string;
  };

  const getDefaultTooltipOption = (id: string): TooltipOption => {
    return {
      visible: false,
      left: 0,
      top: 0,
      xAlign: 'left',
      yAlign: 'center',
      id
    };
  };

  type ChartTooltip = {
    readonly time: string;
    readonly value: string;
  };

  const defaultTooltip = (): ChartTooltip => ({
    time: '',
    value: ''
  });

  const tooltipOption = ref(getDefaultTooltipOption(id));
  const tooltip = ref(defaultTooltip());

  const calculateTooltipPosition = (
    element: HTMLElement,
    tooltipModel: Chart.ChartTooltipModel
  ): Partial<TooltipOption> => {
    let { x, y } = tooltipModel;
    const { xAlign, yAlign } = tooltipModel;

    const elemWidth = element.clientWidth;
    const elemHeight = element.clientHeight;

    if (tooltipModel.xAlign === 'center') {
      x += (tooltipModel.width - elemWidth) / 2;
    } else if (tooltipModel.xAlign === 'right') {
      x += tooltipModel.width - elemWidth;
    }

    if (tooltipModel.yAlign === 'center') {
      y += (tooltipModel.height - elemHeight) / 2;
    } else if (tooltipModel.yAlign === 'bottom') {
      y += tooltipModel.height - elemHeight;
    }

    return {
      xAlign,
      yAlign,
      left: x,
      top: y,
      visible: true
    };
  };

  return {
    tooltipOption,
    tooltip,
    calculateTooltipPosition
  };
};

export default defineComponent({
  name: 'NetWorthChart',
  components: { ExportSnapshotDialog },
  props: {
    timeframe: {
      required: true,
      type: String as PropType<TimeFramePeriod>,
      validator: (value: TimeFramePeriod) =>
        Object.values(TimeFramePeriod).includes(value)
    },
    timeframes: { required: true, type: Object as PropType<Timeframes> },
    chartData: { required: true, type: Object as PropType<NetValue> }
  },
  setup(props) {
    const { timeframe, timeframes, chartData } = toRefs(props);
    const { graphZeroBased, nftsInNetValue } = setupSettings();
    const { currency } = setupGeneralSettings();
    const { dark } = setupThemeCheck();

    const selectedTimestamp = ref<number>(0);
    const selectedBalance = ref<number>(0);
    const showExportSnapshotDialog = ref<boolean>(false);

    const canvasId = 'net-worth-chart__chart';
    const tooltipId = 'net-worth-chart__tooltip';

    const { tooltip, tooltipOption, calculateTooltipPosition } =
      useTooltip(tooltipId);
    const chart = ref<Chart | null>(null);
    const times = ref<number[]>([]);
    const data = ref<number[]>([]);
    const filteredData = ref<ValueOverTime[]>([]);
    const showVirtualCurrentData = ref<boolean>(true);

    const activeTimeframe = computed<Timeframe>(() => {
      return get(timeframes)[get(timeframe)];
    });

    const xAxisStepSize = computed<number>(
      () => get(activeTimeframe).xAxisStepSize
    );

    const xAxisTimeUnit = computed<TimeUnit>(
      () => get(activeTimeframe).xAxisTimeUnit
    );

    const clearData = () => {
      set(data, []);
      set(times, []);
      set(filteredData, []);
    };

    const updateChart = () => {
      set(times, [...get(chartData).times]);
      set(data, [...get(chartData).data]);
      transformData();
    };

    watch(chartData, () => {
      clearData();
      updateChart();
    });

    const transformData = () => {
      const chartVal = get(chart);
      assert(chartVal, 'chart was null');
      const options = chartVal.options!;
      const scales: LinearScale = options.scales!;
      const chartXAx = scales.xAxes![0];
      const time = chartXAx.time;
      assert(time, 'time was null');
      time.unit = get(xAxisTimeUnit);
      time.stepSize = get(xAxisStepSize);

      // set the data
      const newData = [];
      const timesVal = get(times);
      const dataVal = get(data);
      let showVirtual = true;

      for (let i = 0; i < timesVal.length; i++) {
        const epoch = timesVal[i];
        const value = dataVal[i];

        if (i < timesVal.length - 1 || value > 0) {
          newData.push({
            x: new Date(epoch * 1000),
            y: value
          });
        } else {
          showVirtual = false;
        }
      }
      set(filteredData, newData);
      set(showVirtualCurrentData, showVirtual);

      chartVal.data.datasets![0].data = get(filteredData);
      chartVal.update();
    };

    const canvasContext = (elementId: string): CanvasRenderingContext2D => {
      const canvas = document.getElementById(elementId);
      assert(
        canvas && canvas instanceof HTMLCanvasElement,
        'Canvas could not be found'
      );
      const context = canvas.getContext('2d');
      assert(context, 'Context could not be found');
      return context;
    };

    const { theme } = setupThemeCheck();

    const createDatasets = (
      canvas: CanvasRenderingContext2D
    ): ChartDataSets[] => {
      const color = get(theme).currentTheme['graph'] as string;
      const secondaryColor = get(theme).currentTheme['graphFade'] as string;

      const areaGradient = canvas.createLinearGradient(0, 0, 0, 160);
      areaGradient.addColorStop(0, color);
      areaGradient.addColorStop(1, secondaryColor);

      const dataset: ChartDataSets = {
        data: get(filteredData),
        lineTension: 0,
        backgroundColor: areaGradient,
        borderColor: color,
        borderWidth: 2,
        pointHoverBorderWidth: 2,
        pointHoverBorderColor: 'white',
        pointBackgroundColor: 'white',
        pointHoverBackgroundColor: color
      };

      return [dataset];
    };

    const createScales = (): LinearScale => {
      const labelFormat: (period: TimeFramePeriod) => string = period => {
        return get(timeframes)[period].xAxisLabelDisplayFormat;
      };

      const displayFormats: TimeDisplayFormat = {
        month: labelFormat(TimeFramePeriod.ALL),
        week: labelFormat(TimeFramePeriod.MONTH),
        day: labelFormat(TimeFramePeriod.WEEK),
        hour: labelFormat(TimeFramePeriod.WEEK)
      };

      const time: TimeScale = {
        unit: get(xAxisTimeUnit),
        stepSize: get(xAxisStepSize),
        displayFormats: displayFormats
      };

      const xAxes: ChartXAxe = {
        type: 'time',
        gridLines: { display: false },
        time: time
      };

      const yAxes: ChartYAxe = {
        display: false,
        ticks: {
          beginAtZero: get(graphZeroBased)
        }
      };

      return {
        xAxes: [xAxes],
        yAxes: [yAxes]
      };
    };

    const tooltipOptions = (): ChartTooltipOptions => {
      const custom: (
        tooltipModel: ChartTooltipModel
      ) => void = tooltipModel => {
        const element = document.getElementById(tooltipId);
        assert(element, 'No tooltip element found');

        if (tooltipModel.opacity === 0) {
          tooltipOption.value = {
            ...tooltipOption.value,
            visible: false
          };
          return;
        }

        const item = tooltipModel.dataPoints[0];
        const netWorth = bigNumberify(item.value!).toFormat(
          2,
          BigNumber.ROUND_DOWN
        );

        const time = dayjs(item.label).format(
          get(activeTimeframe).tooltipTimeFormat
        );

        tooltip.value = {
          value: `${netWorth} ${get(currency).unicodeSymbol}`,
          time: `${time}`
        };

        nextTick(() => {
          tooltipOption.value = {
            ...tooltipOption.value,
            ...calculateTooltipPosition(element, tooltipModel)
          };
        });
      };

      return {
        enabled: false,
        mode: 'index',
        intersect: false,
        custom
      };
    };

    const createChart = (): Chart => {
      const canvas = canvasContext(canvasId);
      const elements: ChartElementsOptions = {
        point: {
          radius: 0,
          hoverRadius: 6,
          pointStyle: 'circle'
        }
      };
      const datasets = createDatasets(canvas);
      const scales = createScales();
      const tooltips = tooltipOptions();

      const options: ChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        hover: { intersect: false },
        legend: { display: false },
        elements,
        tooltips,
        scales
      };

      const config: ChartConfiguration = {
        type: 'line',
        data: {
          datasets
        },
        options
      };

      return new Chart(canvas, config);
    };

    const setup = () => {
      if (get(chart)) {
        get(chart)!.destroy();
      }
      Chart.defaults.global.defaultFontFamily = 'Roboto';
      clearData();
      set(chart, createChart());
      updateChart();
    };

    watch([dark, nftsInNetValue], () => {
      setup();
    });

    onMounted(() => {
      setup();
    });

    watch(timeframe, () => {
      clearData();
      set(times, [...get(chartData).times]);
      set(data, [...get(chartData).data]);
      transformData();
    });

    const canvasClicked = (event: PointerEvent) => {
      const axisData = get(chart)?.getElementsAtXAxis(event);

      if (axisData && axisData.length > 0) {
        // @ts-ignore
        const index = axisData[0]._index;

        if (
          get(times)[index] &&
          get(data)[index] &&
          !(
            get(showVirtualCurrentData) &&
            index === get(chartData).data.length - 1
          )
        ) {
          set(selectedTimestamp, get(times)[index]);
          set(selectedBalance, get(data)[index]);

          set(showExportSnapshotDialog, true);
        }
      }
    };

    return {
      dark,
      canvasId,
      canvasClicked,
      showExportSnapshotDialog,
      selectedTimestamp,
      selectedBalance,
      tooltip,
      tooltipOption
    };
  }
});
</script>
<style module lang="scss">
.tooltip {
  position: absolute;
  opacity: 0;
  visibility: hidden;
  background-color: white;
  padding: 8px 12px;
  font-family: 'Roboto', sans-serif;
  font-size: 16px;
  border-radius: 6px;
  filter: drop-shadow(0 0 8px var(--v-rotki-grey-base));
  pointer-events: none;
  transition: 0.3s all;
  white-space: nowrap;
  line-height: 1.2rem;

  &::before {
    content: '';
    width: 0;
    height: 0;
    position: absolute;
    border-width: 6px;
    border-style: solid;
    border-color: transparent;
  }

  &[data-align-x='left'],
  &[data-align-x='right'] {
    &::before {
      border-top-color: transparent;
      border-bottom-color: transparent;
    }
  }

  &[data-align-x='left'] {
    &::before {
      border-right-color: white;
      right: 100%;
    }

    &:not([data-align-y='center']) {
      &::before {
        border-right-color: transparent;
        right: calc(100% - 16px);
      }
    }
  }

  &[data-align-x='right'] {
    &::before {
      border-left-color: white;
      left: 100%;
    }

    &:not([data-align-y='center']) {
      &::before {
        border-left-color: transparent;
        left: calc(100% - 16px);
      }
    }
  }

  &[data-align-y='top'],
  &[data-align-y='bottom'] {
    &::before {
      border-left-color: transparent;
      border-right-color: transparent;
    }
  }

  &[data-align-y='top'] {
    &::before {
      border-bottom-color: white;
      bottom: 100%;
    }
  }

  &[data-align-y='bottom'] {
    &::before {
      border-top-color: white;
      top: 100%;
    }
  }

  &[data-align-x='center'] {
    &::before {
      left: 50%;
      transform: translateX(-50%);
    }
  }

  &[data-align-y='center'] {
    &::before {
      top: 50%;
      transform: translateY(-50%);
    }
  }

  &-show {
    opacity: 0.9;
    visibility: visible;
  }

  &-dark {
    color: black;
  }
}

.wrapper {
  width: 100%;
  position: relative;
}

.canvas {
  position: relative;
  height: 200px;
  width: 100%;
}
</style>
