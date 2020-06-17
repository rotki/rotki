<template>
  <div class="networth-chart__chart">
    <canvas id="networth-chart__chart" />
    <div id="networth-chart__tooltip">
      <div
        class="networth-chart__tooltip__value font-weight-bold text-center"
      />
      <div class="networth-chart__tooltip__time rotki-grey--text text-center" />
    </div>
  </div>
</template>

<script lang="ts">
import BigNumber from 'bignumber.js';
import { Chart } from 'chart.js';

import moment from 'moment';
import { Component, Vue, Prop, Watch } from 'vue-property-decorator';
import { bigNumberify } from '@/utils/bignumbers';

export interface ChartData {
  readonly times: number[];
  readonly data: number[];
}

export interface ValueOverTime {
  readonly x: Date;
  readonly y: number;
}

export interface TimeframeProps {
  readonly startingDate: number; // Unix timestamp
  xAxisTimeUnit: string;
  xAxisStepSize: number;
  xAxisLabelDisplayFormat: string;
  tooltipTimeFormat: string;
}

@Component({})
export default class NetworthChart extends Vue {
  @Prop({ required: true })
  timeframe!: string;
  @Prop({ required: true })
  timeframes!: { [timeframe: string]: TimeframeProps };
  @Prop({ required: true })
  chartData!: ChartData;

  chart: Chart | null = null;
  times: number[] = [];
  data: number[] = [];
  filteredData: ValueOverTime[] = [];

  get activeTimeframe(): TimeframeProps {
    return this.timeframes[this.timeframe];
  }

  clearData() {
    this.emptyArray(this.data);
    this.emptyArray(this.times);
    this.emptyArray(this.filteredData);
  }

  transformData() {
    // set the x-axis units and stepsize
    this.chart!.options!.scales!.xAxes![0].time!.unit! = this.activeTimeframe
      .xAxisTimeUnit as Chart.TimeUnit;
    this.chart!.options!.scales!.xAxes![0].time!.stepSize = this.activeTimeframe.xAxisStepSize;

    // set the data
    for (let i = 0; i < this.times.length; i++) {
      const epoch = this.times[i];
      this.filteredData.push({
        x: new Date(epoch * 1000),
        y: this.data[i]
      });
    }

    this.chart!!.update();
  }

  canvasContext(elementId: string): CanvasRenderingContext2D {
    const canvas = document.getElementById(elementId);
    if (!canvas || !(canvas instanceof HTMLCanvasElement)) {
      throw new Error('Canvas could not be found');
    }
    const context = canvas.getContext('2d');
    if (!context) {
      throw new Error('Context could not be found');
    }

    return context;
  }

  emptyArray(array: Array<any>) {
    const elements = array.length;
    for (let i = 0; i < elements; i++) {
      array.pop();
    }
  }

  createChart() {
    const chartCanvas = this.canvasContext('networth-chart__chart');
    const areaGradient = chartCanvas.createLinearGradient(0, 0, 0, 160);
    areaGradient.addColorStop(
      0,
      String(this.$vuetify.theme.currentTheme['rotki-light-blue'])
    );
    areaGradient.addColorStop(1, 'white');

    return new Chart(chartCanvas, {
      type: 'line',
      data: {
        datasets: [
          {
            data: this.filteredData,
            lineTension: 0,
            backgroundColor: areaGradient,
            borderColor: String(
              this.$vuetify.theme.currentTheme['rotki-light-blue']
            ),
            borderWidth: 2,
            pointHoverBorderWidth: 2,
            pointHoverBorderColor: 'white',
            pointBackgroundColor: 'white',
            pointHoverBackgroundColor: String(
              this.$vuetify.theme.currentTheme['rotki-light-blue']
            )
          }
        ]
      },

      options: {
        responsive: true,
        maintainAspectRatio: false,
        hover: { intersect: false },
        legend: {
          display: false
        },
        // hide points and only show on hover
        elements: {
          point: {
            radius: 0,
            hoverRadius: 6,
            pointStyle: 'circle'
          }
        },
        tooltips: {
          enabled: false,
          mode: 'index',
          intersect: false,
          custom: tooltipModel => {
            // Tooltip Element
            let tooltipEl = document.getElementById('networth-chart__tooltip');

            // Hide if no tooltip
            if (tooltipModel.opacity === 0) {
              tooltipEl!.style.opacity = '0';
              return;
            }

            // Set caret Position
            tooltipEl!.classList.remove('above', 'below', 'no-transform');
            if (tooltipModel.yAlign) {
              tooltipEl!.classList.add(tooltipModel.yAlign);
            } else {
              tooltipEl!.classList.add('no-transform');
            }

            // Content
            let tooltipValueHtml = '';
            const tooltipValue = tooltipEl!.querySelector(
              '.networth-chart__tooltip__value'
            );
            const networthValue = bigNumberify(
              tooltipModel.dataPoints[0].value!
            ).toFormat(2, BigNumber.ROUND_DOWN);
            tooltipValueHtml = `${networthValue}`;
            tooltipValue!.innerHTML = tooltipValueHtml;

            let tooltipTimeHtml = '';
            const tooltipTime = tooltipEl!.querySelector(
              '.networth-chart__tooltip__time'
            );
            const time = moment(
              tooltipModel.dataPoints[0].label,
              'MMM DD, YYYY, h:mm:ss a'
            ).format(this.activeTimeframe.tooltipTimeFormat);
            tooltipTimeHtml = `${time}`;
            tooltipTime!.innerHTML = tooltipTimeHtml;

            // Element display & positioning. Styling is in css below
            tooltipEl!.style.opacity = '0.9';

            const tooltipXOffset = -130;
            const tooltipYOffset = -20;
            tooltipEl!.style.position = 'absolute';
            tooltipEl!.style.left = tooltipModel.caretX + tooltipXOffset + 'px';
            tooltipEl!.style.top = tooltipModel.caretY + tooltipYOffset + 'px';
          }
        },
        scales: {
          xAxes: [
            {
              type: 'time',
              gridLines: {
                display: false
              },
              time: {
                unit: this.activeTimeframe.xAxisTimeUnit as Chart.TimeUnit,
                stepSize: this.activeTimeframe.xAxisStepSize,
                displayFormats: {
                  month: this.timeframes['All'].xAxisLabelDisplayFormat,
                  week: this.timeframes['1M'].xAxisLabelDisplayFormat,
                  day: this.timeframes['1W'].xAxisLabelDisplayFormat,
                  hour: this.timeframes['1D'].xAxisLabelDisplayFormat
                }
              }
            }
          ],
          yAxes: [
            {
              display: false
            }
          ]
        }
      }
    });
  }

  @Watch('timeframe')
  timeframeChange() {
    this.clearData();
    this.times.push(...this.chartData.times);
    this.data.push(...this.chartData.data);
    this.transformData();
  }

  mounted() {
    Chart.defaults.global.defaultFontFamily = 'Roboto';
    this.clearData();
    this.chart = this.createChart();
    this.times.push(...this.chartData.times);
    this.data.push(...this.chartData.data);
    this.transformData();
  }
}
</script>
<style scoped lang="scss">
#networth-chart__tooltip {
  opacity: 0;
  background-color: white;
  padding: 8px 15px;
  font-family: 'Roboto';
  font-size: 14px;
  border-radius: 15px;
  box-shadow: 0px 0px 8px var(--v-rotki-grey-base);
  pointer-events: none;
}

.networth-chart {
  &__chart {
    position: relative;
    height: 200px;
    width: 99%; // when we set to 100% it's glithcy (sometimes extends past the container div), so keep it < 100%
  }
}
</style>
