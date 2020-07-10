<template>
  <v-card class="overall-balances mt-3 mb-6" :loading="isLoading">
    <v-row no-gutters class="pa-5">
      <v-col cols="12" md="4" lg="4" class="d-flex flex-column al">
        <div class="overall-balances__networth text-center font-weight-medium">
          <amount-display
            show-currency="symbol"
            :fiat-currency="currency.ticker_symbol"
            :value="totalNetworth"
          />
        </div>
        <div class="overall-balances__networth-change py-2">
          <span
            :class="
              balanceDelta.isNegative() ? 'rotki-red lighten-1' : 'rotki-green'
            "
            class="pa-1 px-2"
          >
            {{ balanceDelta.isNegative() ? '▼' : '▲' }}
            <amount-display
              show-currency="symbol"
              :fiat-currency="currency.ticker_symbol"
              :value="balanceDelta"
            />
          </span>
        </div>
        <div class="overall-balances__timeframe-chips text-center">
          <v-chip
            v-for="(timeframe, i) in timeframes"
            :key="i"
            :class="
              timeframe.text === activeTimeframe
                ? 'overall-balances__timeframe-chips--active'
                : ''
            "
            class="ma-2"
            small
            @click="setActiveTimeframe(timeframe.text)"
          >
            {{ timeframe.text }}
          </v-chip>
        </div>
      </v-col>
      <v-col cols="12" md="8" lg="8" class="d-flex">
        <div class="d-flex justify-center align-center flex-grow-1">
          <networth-chart
            v-if="!isLoading"
            :chart-data="chartData"
            :timeframe="activeTimeframe"
            :timeframes="timeframes"
          />
          <div v-else class="overall-balances__networth-chart__loader">
            <v-progress-circular indeterminate class="align-self-center" />
            <div class="pt-5 caption">
              LOADING
            </div>
          </div>
        </div>
      </v-col>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import moment from 'moment';
import { Component, Vue, Prop } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';

import NetworthChart from '@/components/dashboard/NetworthChart.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';

import { aggregateTotal } from '@/filters';
import { Currency } from '@/model/currency';
import { AssetBalance } from '@/store/balances/types';
import { bigNumberify } from '@/utils/bignumbers';

const { mapState } = createNamespacedHelpers('session');
const { mapGetters } = createNamespacedHelpers('session');
const {
  mapGetters: mapBalanceGetters,
  mapState: mapBalanceState
} = createNamespacedHelpers('balances');

export interface NetvalueData {
  readonly times: number[];
  readonly data: string[];
}

export interface ChartData {
  readonly times: number[];
  readonly data: number[];
}

export interface TimeframeProps {
  readonly text: string;
  startingDate: number; // Unix timestamp
  xAxisTimeUnit: string;
  xAxisStepSize: number;
  xAxisLabelDisplayFormat: string;
  tooltipTimeFormat: string;
}

@Component({
  components: { AmountDisplay, NetworthChart },
  computed: {
    ...mapState(['premium']),
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapBalanceGetters(['aggregatedBalances', 'exchangeRate']),
    ...mapBalanceState(['netvalueData'])
  }
})
export default class OverallBox extends Vue {
  @Prop({ required: false, default: false })
  isLoading!: boolean;

  premium!: boolean;
  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;

  aggregatedBalances!: AssetBalance[];
  netvalueData!: NetvalueData;

  activeTimeframe: string = 'All'; // TODO: set the default based on user setting?

  timeframes: { [timeframe: string]: TimeframeProps } = {
    'All': { // eslint-disable-line
      text: 'All',
      startingDate: 0, // unix time
      xAxisTimeUnit: 'month',
      xAxisStepSize: 1,
      xAxisLabelDisplayFormat: 'MMMM YYYY',
      tooltipTimeFormat: 'MMMM D, YYYY'
    },
    '1M': {
      text: '1M',
      startingDate: moment().subtract(1, 'month').startOf('day').unix(),
      xAxisTimeUnit: 'week',
      xAxisStepSize: 1,
      xAxisLabelDisplayFormat: 'MMM D',
      tooltipTimeFormat: 'MMM D'
    },
    '1W': {
      text: '1W',
      startingDate: moment().subtract(1, 'week').startOf('day').unix(),
      xAxisTimeUnit: 'day',
      xAxisStepSize: 1,
      xAxisLabelDisplayFormat: 'ddd',
      tooltipTimeFormat: 'ddd'
    },
    '1D': {
      text: '1D',
      startingDate: moment().subtract(1, 'day').startOf('day').unix(),
      xAxisTimeUnit: 'hour',
      xAxisStepSize: 4,
      xAxisLabelDisplayFormat: 'HH:mm',
      tooltipTimeFormat: 'HH:mm'
    }
  };

  get currentNetWorth(): { time: number; value: number } {
    return { time: moment().unix(), value: this.totalNetworth.toNumber() };
  }

  get chartData(): ChartData {
    if (this.isLoading) {
      return { times: [], data: [] };
    }

    let filteredData: ChartData = { times: [], data: [] };

    this.netvalueData.times.forEach((entry, index) => {
      if (entry > this.timeframes[this.activeTimeframe].startingDate) {
        filteredData.times.push(entry);
        filteredData.data.push(
          bigNumberify(this.netvalueData.data[index])
            .multipliedBy(this.exchangeRate(this.currency.ticker_symbol))
            .toNumber()
        );
      }
    });

    return {
      times: [...filteredData.times, this.currentNetWorth.time],
      data: [...filteredData.data, this.currentNetWorth.value]
    };
  }

  get totalNetworth(): BigNumber {
    return aggregateTotal(
      this.aggregatedBalances,
      this.currency.ticker_symbol,
      this.exchangeRate(this.currency.ticker_symbol),
      this.floatingPrecision
    );
  }

  get balanceDelta(): BigNumber {
    return this.totalNetworth.minus(this.startingBalance);
  }

  get startingBalance(): BigNumber {
    return bigNumberify(this.chartData.data[0]);
  }

  setActiveTimeframe(timeframe: string) {
    this.activeTimeframe = timeframe;
  }

  mounted() {
    if (this.premium) {
      this.$store.dispatch('balances/fetchNetvalueData');
    }
  }
}
</script>
<style scoped lang="scss">
.overall-balances {
  &__balance {
    display: flex;
    justify-content: center;
    align-items: baseline;
  }

  &__networth {
    ::v-deep {
      .amount-display {
        &__value {
          font-size: 3.5em;
        }

        &__currency {
          font-size: 3em;
        }
      }
    }
  }

  &__networth-change {
    display: flex;
    justify-content: center;
    align-items: baseline;
    margin-bottom: 1em;

    span {
      border-radius: 0.75em;
    }
  }

  &__timeframe-chips {
    .v-chip {
      cursor: pointer;
    }

    &--active {
      color: white !important;
      background-color: var(--v-primary-base) !important;
    }
  }

  &__networth-chart {
    &__loader {
      display: flex;
      height: 100%;
      flex-direction: column;
      align-content: center;
      justify-content: center;
      text-align: center;
    }
  }
}
</style>
