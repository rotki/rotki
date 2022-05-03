<template>
  <div>
    <div class="net-worth-chart__chart">
      <canvas :id="canvasId" @click="canvasClicked" />
      <div
        id="net-worth-chart__tooltip"
        :class="{
          'theme--dark': dark
        }"
      >
        <div
          class="net-worth-chart__tooltip__value font-weight-bold text-center"
        />
        <div
          class="net-worth-chart__tooltip__time rotki-grey--text text-center"
        />
      </div>
    </div>

    <v-dialog v-model="showExportSnapshotDialog" max-width="600">
      <card>
        <template #title>
          {{ $t('dashboard.snapshot.export_database_snapshot') }}
        </template>
        <template #subtitle>
          {{ $t('dashboard.snapshot.subtitle') }}
        </template>
        <div class="mb-n4">
          <div>
            <div>
              {{ $t('dashboard.snapshot.time') }}
            </div>
            <div>
              <date-display
                class="font-weight-bold"
                :timestamp="selectedTimestamp"
              />
            </div>
          </div>
          <div class="pt-2">
            <div>
              {{ $t('dashboard.snapshot.balance') }}
            </div>
            <div>
              <amount-display
                :value="formattedSelectedBalance"
                :fiat-currency="currency.tickerSymbol"
                class="font-weight-bold"
              />
            </div>
          </div>
        </div>
        <template #buttons>
          <v-spacer />
          <v-btn depressed color="primary" @click="exportSnapshot">
            {{ $t('dashboard.snapshot.download_snapshot') }}
          </v-btn>
        </template>
      </card>
    </v-dialog>
  </div>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { Message } from '@rotki/common/lib/messages';
import {
  Timeframe,
  TimeFramePeriod,
  Timeframes
} from '@rotki/common/lib/settings/graphs';
import { NetValue } from '@rotki/common/lib/statistics';
import {
  computed,
  defineComponent,
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
import { setupThemeCheck } from '@/composables/common';
import { setupGeneralSettings } from '@/composables/session';
import { setupSettings } from '@/composables/settings';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/store';
import { assert } from '@/utils/assertions';
import { bigNumberify, bigNumberifyFromRef } from '@/utils/bignumbers';
import { downloadFileByUrl } from '@/utils/download';

export interface ValueOverTime {
  readonly x: Date;
  readonly y: number;
}

export default defineComponent({
  name: 'NetWorthChart',
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

    const formattedSelectedBalance = computed<BigNumber | null>(() => {
      if (get(selectedBalance)) {
        return get(bigNumberifyFromRef(selectedBalance));
      }

      return null;
    });

    const canvasId = 'net-worth-chart__chart';
    const chart = ref<Chart | null>(null);
    const times = ref<number[]>([]);
    const data = ref<number[]>([]);
    const filteredData = ref<ValueOverTime[]>([]);

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
      for (let i = 0; i < get(times).length; i++) {
        const epoch = get(times)[i];
        newData.push({
          x: new Date(epoch * 1000),
          y: get(data)[i]
        });
      }
      set(filteredData, newData);

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

    const createDatasets = (
      canvas: CanvasRenderingContext2D
    ): ChartDataSets[] => {
      const { theme } = setupThemeCheck();
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
      const symbol = () => get(currency).unicodeSymbol;

      const setCaretPosition = (
        classList: DOMTokenList,
        tooltipModel: Chart.ChartTooltipModel
      ) => {
        classList.remove('above', 'below', 'no-transform');
        if (tooltipModel.yAlign) {
          classList.add(tooltipModel.yAlign);
        } else {
          classList.add('no-transform');
        }
      };

      function updateTooltip(
        element: HTMLElement,
        netWorth: string,
        time: string
      ) {
        const tooltipValue = element.querySelector(
          '.net-worth-chart__tooltip__value'
        );
        const tooltipTime = element.querySelector(
          '.net-worth-chart__tooltip__time'
        );

        assert(tooltipValue, 'tooltip value element was not found');
        assert(tooltipTime, 'tooltip time element was not found');

        tooltipValue!.innerHTML = `${netWorth} ${symbol()}`;
        tooltipTime!.innerHTML = `${time}`;
      }

      function displayTooltip(
        style: CSSStyleDeclaration,
        tooltipModel: Chart.ChartTooltipModel
      ) {
        const tooltipXOffset = -130;
        const tooltipYOffset = -20;

        style.opacity = '0.9';
        style.position = 'absolute';
        style.left = `${tooltipModel.caretX + tooltipXOffset}px`;
        style.top = `${tooltipModel.caretY + tooltipYOffset}px`;
      }

      const custom: (
        tooltipModel: ChartTooltipModel
      ) => void = tooltipModel => {
        const element = document.getElementById('net-worth-chart__tooltip');
        assert(element, 'No tooltip element found');

        if (tooltipModel.opacity === 0) {
          element.style.opacity = '0';
          return;
        }

        setCaretPosition(element.classList, tooltipModel);

        const item = tooltipModel.dataPoints[0];
        const netWorth = bigNumberify(item.value!).toFormat(
          2,
          BigNumber.ROUND_DOWN
        );

        const time = dayjs(item.label).format(
          get(activeTimeframe).tooltipTimeFormat
        );

        updateTooltip(element, netWorth, time);
        displayTooltip(element.style, tooltipModel);
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

        set(selectedTimestamp, get(times)[index]);
        set(selectedBalance, get(data)[index]);

        set(showExportSnapshotDialog, true);
      }
    };

    const downloadSnapshot = async () => {
      const resp = await api.downloadSnapshot({
        timestamp: get(selectedTimestamp)
      });

      const blob = new Blob([resp.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);

      const date = dayjs(get(selectedTimestamp) * 1000).format(
        'YYYYDDMMHHmmss'
      );
      const fileName = `${date}-snapshot.zip`;

      downloadFileByUrl(url, fileName);

      set(showExportSnapshotDialog, false);
    };

    const exportSnapshotCSV = async () => {
      const { setMessage } = useMainStore();
      let message: Message | null = null;

      try {
        if (interop.isPackaged && api.defaultBackend) {
          const path = await interop.openDirectory(
            i18n.t('dashboard.snapshot.select_directory').toString()
          );

          if (!path) {
            return;
          }

          const success = await api.exportSnapshotCSV({
            path,
            timestamp: get(selectedTimestamp)
          });

          message = {
            title: i18n.t('dashboard.snapshot.message.title').toString(),
            description: success
              ? i18n.t('dashboard.snapshot.message.success').toString()
              : i18n.t('dashboard.snapshot.message.failure').toString(),
            success
          };

          set(showExportSnapshotDialog, false);
        } else {
          await downloadSnapshot();
        }
      } catch (e: any) {
        message = {
          title: i18n.t('dashboard.snapshot.message.title').toString(),
          description: e.message,
          success: false
        };
      }

      if (message) {
        setMessage(message);
      }
    };

    const exportSnapshot = () => {
      if (interop.isPackaged) {
        exportSnapshotCSV();
      } else {
        downloadSnapshot();
      }
    };

    return {
      dark,
      canvasId,
      canvasClicked,
      showExportSnapshotDialog,
      selectedTimestamp,
      formattedSelectedBalance,
      currency,
      exportSnapshot
    };
  }
});
</script>
<style scoped lang="scss">
.theme {
  &--dark {
    color: black;
  }
}

#net-worth-chart__tooltip {
  opacity: 0;
  background-color: white;
  padding: 8px 15px;
  font-family: 'Roboto', sans-serif;
  font-size: 14px;
  border-radius: 15px;
  box-shadow: 0 0 8px var(--v-rotki-grey-base);
  pointer-events: none;
}

.net-worth-chart {
  &__tooltip {
    margin-top: -10px;
  }

  &__chart {
    position: relative;
    height: 200px;
    width: 100%;
  }
}
</style>
