<template>
  <div :class="$style.wrapper">
    <div class="d-flex justify-end">
      <chart-shortcut-hint />
    </div>
    <div :class="$style.canvas">
      <canvas
        :id="canvasId"
        @click.stop="canvasClicked"
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

    <export-snapshot-dialog
      v-model="showExportSnapshotDialog"
      :timestamp="selectedTimestamp"
      :balance="selectedBalance"
    />
  </div>
</template>

<script lang="ts">
import {
  getTimeframeByRange,
  Timeframe,
  TimeFramePeriod,
  Timeframes
} from '@rotki/common/lib/settings/graphs';
import { NetValue } from '@rotki/common/lib/statistics';
import { get, set } from '@vueuse/core';
import {
  Chart,
  ChartConfiguration,
  ChartOptions,
  TooltipOptions,
  TimeUnit
} from 'chart.js';
import dayjs from 'dayjs';
import {
  computed,
  defineComponent,
  nextTick,
  onMounted,
  PropType,
  ref,
  toRefs,
  watch
} from 'vue';
import ChartShortcutHint from '@/components/ChartShortcutHint.vue';
import ExportSnapshotDialog from '@/components/dashboard/ExportSnapshotDialog.vue';
import GraphTooltipWrapper from '@/components/graphs/GraphTooltipWrapper.vue';
import { setupThemeCheck } from '@/composables/common';
import { useGraph, useTooltip } from '@/composables/graphs';
import { setupGeneralSettings } from '@/composables/session';
import { setupSettings } from '@/composables/settings';
import { interop } from '@/electron-interop';
import { assert } from '@/utils/assertions';
import { bigNumberify } from '@/utils/bignumbers';

export interface ValueOverTime {
  readonly x: number;
  readonly y: number;
}

export default defineComponent({
  name: 'NetWorthChart',
  components: { ChartShortcutHint, GraphTooltipWrapper, ExportSnapshotDialog },
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
    const { chartData } = toRefs(props);
    const { graphZeroBased } = setupSettings();
    const { currencySymbol } = setupGeneralSettings();
    const { dark } = setupThemeCheck();

    const selectedTimestamp = ref<number>(0);
    const selectedBalance = ref<number>(0);
    const showExportSnapshotDialog = ref<boolean>(false);
    const isDblClick = ref<boolean>(false);

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

    const updateChart = () => {
      chart?.update('resize');
      calculateXRange();
    };

    const displayedXMin = ref<number>(0);
    const displayedXMax = ref<number>(0);

    const calculateXRange = () => {
      if (!chart) {
        set(displayedXMin, 0);
        set(displayedXMax, 0);
        return;
      }

      const xAxis = chart.options!.scales!.x!;

      set(displayedXMin, xAxis.min);
      set(displayedXMax, xAxis.max);
    };

    const dataTimeRange = computed<{ min: number; max: number } | null>(() => {
      const data = get(balanceData);
      if (data.length === 0) return null;

      const first = data[0];
      const last = data[data.length - 1];

      return {
        min: first.x,
        max: last.x
      };
    });

    const activeTimeframe = computed<Timeframe>(() => {
      return getTimeframeByRange(get(displayedXMin), get(displayedXMax));
    });

    watch(activeTimeframe, () => chart?.update('resize'));

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
      setZoomLevel();
      updateChart();
    };

    const setZoomLevel = () => {
      const chartVal = getChart();

      const range = get(dataTimeRange);
      if (!range) return;

      const { min, max } = range;
      const xAxis = chartVal.options!.scales!.x!;
      xAxis.min = min;
      xAxis.max = max;

      const zoom = chartVal.options!.plugins!.zoom!;
      zoom.limits = {
        x: {
          min: 'original',
          max: 'original',
          minRange: 28 * 60 * 60 * 1000
        }
      };
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
            displayFormats: () => {
              const format = get(activeTimeframe).xAxisLabelDisplayFormat;
              return {
                month: format,
                week: format,
                day: format
              };
            }
          }
        },
        y: {
          display: false,
          grid: {
            color: () => get(gridColor),
            borderColor: () => get(gridColor)
          },
          suggestedMin: () => {
            const data = get(balanceData);
            if (data.length === 0) return 0;

            let min = Math.min(...data.map(datum => datum.y));
            if (get(graphZeroBased)) {
              min = Math.min(0, min);
            }
            return min;
          },
          suggestedMax: () => {
            const data = get(balanceData);
            if (data.length === 0) return 0;

            return Math.max(...data.map(datum => datum.y));
          }
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

    const createChart = (modifierKey: 'ctrl' | 'meta'): Chart => {
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
          tooltip,
          zoom: {
            zoom: {
              wheel: {
                enabled: true,
                modifierKey
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

    const setup = async () => {
      chart?.destroy();
      clearData();
      const modifierKey = (await interop.isMac()) ? 'meta' : 'ctrl';
      chart = createChart(modifierKey);
      prepareData();
    };

    onMounted(() => {
      setup();
    });

    watch(dark, () => {
      updateChart();
    });

    const canvasClicked = (event: PointerEvent) => {
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
            !(
              showVirtualCurrentData.value &&
              index === balanceDataVal.length - 1
            )
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
      chart?.resetZoom();
    };

    return {
      resetZoom,
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
