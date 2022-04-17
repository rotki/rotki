<template>
  <div>
    <div class="net-worth-chart__chart">
      <canvas id="net-worth-chart__chart" @click="canvasClicked" />
      <div
        id="net-worth-chart__tooltip"
        :class="{
          'theme--dark': $vuetify.theme.dark
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
              <b>{{ formattedSelectedTimestamp }}</b>
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
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import i18n from '@/i18n';
import { useMainStore } from '@/store/store';
import { Currency } from '@/types/currency';
import { assert } from '@/utils/assertions';
import { bigNumberify } from '@/utils/bignumbers';
import { downloadFileByUrl } from '@/utils/download';

export interface ValueOverTime {
  readonly x: Date;
  readonly y: number;
}

@Component({
  computed: {
    ...mapGetters('session', ['currency']),
    ...mapState('settings', ['graphZeroBased', 'nftsInNetValue'])
  }
})
export default class NetWorthChart extends Vue {
  @Prop({
    required: true,
    type: String,
    validator: value => Object.values(TimeFramePeriod).includes(value)
  })
  timeframe!: TimeFramePeriod;
  @Prop({ required: true, type: Object })
  timeframes!: Timeframes;
  @Prop({ required: true, type: Object })
  chartData!: NetValue;

  currency!: Currency;
  graphZeroBased!: boolean;
  nftsInNetValue!: boolean;
  selectedTimestamp: number = 0;
  selectedBalance: number = 0;
  showExportSnapshotDialog: boolean = false;

  get formattedSelectedTimestamp(): Date | null {
    if (this.selectedTimestamp) {
      return new Date(this.selectedTimestamp * 1000);
    }

    return null;
  }

  get formattedSelectedBalance(): BigNumber | null {
    if (this.selectedBalance) {
      return bigNumberify(this.selectedBalance);
    }

    return null;
  }

  get darkModeEnabled(): boolean {
    return this.$vuetify.theme.dark;
  }

  @Watch('darkModeEnabled')
  onDarkMode() {
    this.setup();
  }

  @Watch('nftsInNetValue')
  onIncludeNFTS() {
    this.setup();
  }

  chart: Chart | null = null;
  times: number[] = [];
  data: number[] = [];
  filteredData: ValueOverTime[] = [];

  @Watch('chartData')
  onData() {
    this.clearData();
    this.updateChart();
  }

  get activeTimeframe(): Timeframe {
    return this.timeframes[this.timeframe];
  }

  get xAxisStepSize(): number {
    return this.activeTimeframe.xAxisStepSize;
  }

  get xAxisTimeUnit(): TimeUnit {
    return this.activeTimeframe.xAxisTimeUnit;
  }

  clearData() {
    this.emptyArray(this.data);
    this.emptyArray(this.times);
    this.emptyArray(this.filteredData);
  }

  transformData() {
    const chart = this.chart;
    assert(chart, 'chart was null');
    const options = chart.options!;
    const scales: LinearScale = options.scales!;
    const chartXAx = scales.xAxes![0];
    const time = chartXAx.time;
    assert(time, 'time was null');
    time.unit = this.xAxisTimeUnit;
    time.stepSize = this.xAxisStepSize;

    // set the data
    for (let i = 0; i < this.times.length; i++) {
      const epoch = this.times[i];
      this.filteredData.push({
        x: new Date(epoch * 1000),
        y: this.data[i]
      });
    }

    chart.update();
  }

  canvasContext(elementId: string): CanvasRenderingContext2D {
    const canvas = document.getElementById(elementId);
    assert(
      canvas && canvas instanceof HTMLCanvasElement,
      'Canvas could not be found'
    );
    const context = canvas.getContext('2d');
    assert(context, 'Context could not be found');
    return context;
  }

  emptyArray(array: Array<any>) {
    const elements = array.length;
    for (let i = 0; i < elements; i++) {
      array.pop();
    }
  }

  createChart(): Chart {
    const chartCanvas = this.canvasContext('net-worth-chart__chart');
    const datasets = this.datasets(chartCanvas);
    const elements = this.elementOptions();
    const tooltips: ChartTooltipOptions = this.tooltipOptions();
    const scales: LinearScale = this.createScale();
    const chartOptions: ChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      hover: { intersect: false },
      legend: { display: false },
      elements: elements,
      tooltips: tooltips,
      scales: scales
    };
    const options: ChartConfiguration = {
      type: 'line',
      data: {
        datasets: datasets
      },
      options: chartOptions
    };
    return new Chart(chartCanvas, options);
  }

  private createScale(): LinearScale {
    const labelFormat: (period: TimeFramePeriod) => string = period => {
      return this.timeframes[period].xAxisLabelDisplayFormat;
    };

    const displayFormats: TimeDisplayFormat = {
      month: labelFormat(TimeFramePeriod.ALL),
      week: labelFormat(TimeFramePeriod.MONTH),
      day: labelFormat(TimeFramePeriod.WEEK),
      hour: labelFormat(TimeFramePeriod.WEEK)
    };

    const time: TimeScale = {
      unit: this.xAxisTimeUnit,
      stepSize: this.xAxisStepSize,
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
        beginAtZero: this.graphZeroBased
      }
    };

    return {
      xAxes: [xAxes],
      yAxes: [yAxes]
    };
  }

  private tooltipOptions(): ChartTooltipOptions {
    const symbol = () => this.currency.unicodeSymbol;

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

    const custom: (tooltipModel: ChartTooltipModel) => void = tooltipModel => {
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
        this.activeTimeframe.tooltipTimeFormat
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
  }

  private elementOptions = (): ChartElementsOptions => ({
    point: {
      radius: 0,
      hoverRadius: 6,
      pointStyle: 'circle'
    }
  });

  private datasets(chartCanvas: CanvasRenderingContext2D): ChartDataSets[] {
    const theme = this.$vuetify.theme;
    const color = theme.currentTheme['graph'] as string;
    const secondaryColor = theme.currentTheme['graphFade'] as string;

    const areaGradient = chartCanvas.createLinearGradient(0, 0, 0, 160);
    areaGradient.addColorStop(0, color);
    areaGradient.addColorStop(1, secondaryColor);

    const dataset: ChartDataSets = {
      data: this.filteredData,
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
  }

  @Watch('timeframe')
  timeframeChange() {
    this.clearData();
    this.times.push(...this.chartData.times);
    this.data.push(...this.chartData.data);
    this.transformData();
  }

  mounted() {
    this.setup();
  }

  private setup() {
    if (this.chart) {
      this.chart.destroy();
    }
    Chart.defaults.global.defaultFontFamily = 'Roboto';
    this.clearData();
    this.chart = this.createChart();
    this.updateChart();
  }

  private updateChart() {
    this.times.push(...this.chartData.times);
    this.data.push(...this.chartData.data);
    this.transformData();
  }

  canvasClicked(event: PointerEvent) {
    const data = this.chart?.getElementsAtXAxis(event);

    if (data && data.length > 0) {
      // @ts-ignore
      const index = data[0]._index;

      this.selectedTimestamp = this.times[index];
      this.selectedBalance = this.data[index];

      this.showExportSnapshotDialog = true;
    }
  }

  exportSnapshot() {
    if (this.$interop.isPackaged) {
      this.exportSnapshotCSV();
    } else {
      this.downloadSnapshot();
    }
  }

  async exportSnapshotCSV() {
    const { setMessage } = useMainStore();
    let message: Message | null = null;

    try {
      if (this.$interop.isPackaged && this.$api.defaultBackend) {
        const path = await this.$interop.openDirectory(
          i18n.t('dashboard.snapshot.select_directory').toString()
        );

        if (!path) {
          return;
        }

        const success = await this.$api.exportSnapshotCSV({
          path,
          timestamp: this.selectedTimestamp
        });

        message = {
          title: i18n.t('dashboard.snapshot.message.title').toString(),
          description: success
            ? i18n.t('dashboard.snapshot.message.success').toString()
            : i18n.t('dashboard.snapshot.message.failure').toString(),
          success
        };

        this.showExportSnapshotDialog = false;
      } else {
        await this.downloadSnapshot();
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
  }

  async downloadSnapshot() {
    const resp = await this.$api.downloadSnapshot({
      timestamp: this.selectedTimestamp
    });

    const blob = new Blob([resp.data], { type: 'application/zip' });
    const url = window.URL.createObjectURL(blob);

    const date = dayjs(this.selectedTimestamp * 1000).format('YYYYDDMMHHmmss');
    const fileName = `${date}-snapshot.zip`;

    downloadFileByUrl(url, fileName);

    this.showExportSnapshotDialog = false;
  }
}
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
