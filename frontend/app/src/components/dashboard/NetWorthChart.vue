<template>
  <div :class="$style.wrapper">
    <div :class="$style.canvas">
      <canvas :id="canvasId" @click="canvasClicked" />
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

    <export-snapshot-dialog
      v-model="showExportSnapshotDialog"
      :timestamp="selectedTimestamp"
      :balance="selectedBalance"
    />
  </div>
</template>

<script lang="ts">
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
  ChartOptions,
  TooltipOptions,
  TimeUnit
} from 'chart.js';
import dayjs from 'dayjs';
import ExportSnapshotDialog from '@/components/dashboard/ExportSnapshotDialog.vue';
import GraphTooltipWrapper from '@/components/graphs/GraphTooltipWrapper.vue';
import { setupThemeCheck } from '@/composables/common';
import { useGraph, useTooltip } from '@/composables/graphs';
import { setupGeneralSettings } from '@/composables/session';
import { setupSettings } from '@/composables/settings';
import { assert } from '@/utils/assertions';
import { bigNumberify } from '@/utils/bignumbers';

export interface ValueOverTime {
  readonly x: number;
  readonly y: number;
}

export default defineComponent({
  name: 'NetWorthChart',
  components: { GraphTooltipWrapper, ExportSnapshotDialog },
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
    const { graphZeroBased } = setupSettings();
    const { currencySymbol } = setupGeneralSettings();
    const { dark } = setupThemeCheck();

    const selectedTimestamp = ref<number>(0);
    const selectedBalance = ref<number>(0);
    const showExportSnapshotDialog = ref<boolean>(false);

    const canvasId = 'net-worth-chart__chart';
    const tooltipId = 'net-worth-chart__tooltip';

    const { tooltipContent, tooltipDisplayOption, calculateTooltipPosition } =
      useTooltip(tooltipId);

    const balanceData = ref<ValueOverTime[]>([]);
    const showVirtualCurrentData = ref<boolean>(true);

    let chart: Chart | null = null;

    const getChart = (): Chart => {
      assert(chart, 'chart was null');
      return chart;
    };

    const activeTimeframe = computed<Timeframe>(() => {
      return get(timeframes)[get(timeframe)];
    });

    const xAxisStepSize = computed<number>(
      () => get(activeTimeframe).xAxisStepSize
    );

    const xAxisTimeUnit = computed<TimeUnit>(
      () => get(activeTimeframe).xAxisTimeUnit
    );

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
      chartVal.update('resize');
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
      useGraph(canvasId);

    const createDatasets = () => {
      const dataset = {
        data: [],
        tension: 0.1,
        fill: true,
        backgroundColor: () => get(gradient),
        borderColor: () => get(baseColor),
        borderWidth: 2,
        pointHoverBorderWidth: 2,
        pointHoverBorderColor: 'white',
        pointBackgroundColor: 'white',
        pointHoverBackgroundColor: () => get(baseColor)
      };

      return [dataset];
    };

    const createScales = () => {
      const labelFormat: (period: TimeFramePeriod) => string = period => {
        return get(timeframes)[period].xAxisLabelDisplayFormat;
      };

      const displayFormats = {
        month: labelFormat(TimeFramePeriod.ALL),
        week: labelFormat(TimeFramePeriod.MONTH),
        day: labelFormat(TimeFramePeriod.WEEK),
        hour: labelFormat(TimeFramePeriod.WEEK)
      };

      return {
        x: {
          type: 'time',
          grid: {
            display: false
          },
          ticks: {
            color: () => get(fontColor)
          },
          time: {
            unit: () => get(xAxisTimeUnit),
            stepSize: () => get(xAxisStepSize),
            displayFormats
          }
        },
        y: {
          display: false,
          grid: {
            color: () => get(gridColor),
            borderColor: () => get(gridColor)
          },
          beginAtZero: () => get(graphZeroBased)
        }
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

    const createChart = (): Chart => {
      const context = getCanvasCtx();
      const datasets = createDatasets();
      const scales = createScales();
      const tooltip = createTooltip();

      const options: ChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
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
          legend: {
            display: false
          },
          tooltip
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
      prepareData();
    };

    onMounted(() => {
      setup();
    });

    watch(dark, () => {
      chart?.update('resize');
    });

    const canvasClicked = (event: PointerEvent) => {
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
    };

    return {
      currencySymbol,
      dark,
      canvasId,
      canvasClicked,
      showExportSnapshotDialog,
      selectedTimestamp,
      selectedBalance,
      tooltipDisplayOption,
      tooltipContent
    };
  }
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
</style>
