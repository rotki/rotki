<template>
  <v-card class="overall-balances mt-3 mb-6" :loading="anyLoading">
    <v-row no-gutters class="pa-5">
      <v-col
        cols="12"
        md="4"
        lg="4"
        class="d-flex flex-column align-center justify-center"
      >
        <div
          class="overall-balances__net-worth text-center font-weight-medium mb-2"
        >
          <amount-display
            show-currency="symbol"
            :fiat-currency="currency.ticker_symbol"
            :value="totalNetWorth"
          />
        </div>
        <div class="overall-balances__net-worth-change py-2">
          <span :class="balanceClass" class="pa-1 px-2">
            {{ indicator }}
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
            @click="activeTimeframe = timeframe.text"
          >
            {{ timeframe.text }}
          </v-chip>
        </div>
      </v-col>
      <v-col cols="12" md="8" lg="8" class="d-flex">
        <div
          class="d-flex justify-center align-center flex-grow-1 overall-balances__net-worth-chart"
        >
          <net-worth-chart
            v-if="!anyLoading"
            :chart-data="timeframeData"
            :timeframe="selection"
            :timeframes="timeframes"
          />
          <div v-else class="overall-balances__net-worth-chart__loader">
            <v-progress-circular indeterminate class="align-self-center" />
            <div class="pt-5 caption">
              {{ $t('overall_balances.loading') }}
            </div>
          </div>
        </div>
      </v-col>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';

import {
  TIMEFRAME_ALL,
  TIMEFRAME_WEEK,
  timeframes
} from '@/components/dashboard/const';
import NetWorthChart from '@/components/dashboard/NetworthChart.vue';
import { TimeFramePeriod, Timeframes } from '@/components/dashboard/types';
import AmountDisplay from '@/components/display/AmountDisplay.vue';

import PremiumMixin from '@/mixins/premium-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { Currency } from '@/model/currency';
import { NetValue } from '@/services/types-api';
import { Section } from '@/store/const';
import { bigNumberify } from '@/utils/bignumbers';

@Component({
  components: { AmountDisplay, NetWorthChart },
  computed: {
    ...mapGetters('session', ['currency']),
    ...mapGetters('statistics', ['netValue', 'totalNetWorth'])
  },
  methods: {
    ...mapActions('statistics', ['fetchNetValue'])
  }
})
export default class OverallBox extends Mixins(PremiumMixin, StatusMixin) {
  currency!: Currency;
  netValue!: (startingDate: number) => NetValue;
  totalNetWorth!: BigNumber;
  fetchNetValue!: () => Promise<void>;

  activeTimeframe: TimeFramePeriod = TIMEFRAME_ALL;

  section = Section.BLOCKCHAIN_ETH;
  secondSection = Section.BLOCKCHAIN_BTC;

  get indicator(): string {
    if (this.anyLoading) {
      return '';
    }
    return this.balanceDelta.isNegative() ? '▼' : '▲';
  }

  get selection(): TimeFramePeriod {
    if (!this.premium) {
      return TIMEFRAME_WEEK;
    }
    return this.activeTimeframe;
  }

  get balanceClass(): string {
    if (this.anyLoading) {
      return 'rotki-grey lighten-3';
    }
    return this.balanceDelta.isNegative()
      ? 'rotki-red lighten-1'
      : 'rotki-green';
  }

  get timeframes(): Timeframes {
    return timeframes;
  }

  get balanceDelta(): BigNumber {
    const start = this.timeframeData.data[0];
    return this.totalNetWorth.minus(bigNumberify(start));
  }

  get timeframeData(): NetValue {
    const startingDate = timeframes[this.activeTimeframe].startingDate();
    return this.netValue(startingDate);
  }

  mounted() {
    this.fetchNetValue();
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

  &__net-worth {
    ::v-deep {
      .amount-display {
        &__value {
          font-size: 3.5em;
          line-height: 4rem;
        }

        &__currency {
          font-size: 3em;
        }
      }
    }
  }

  &__net-worth-change {
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

  &__net-worth-chart {
    width: 100%;

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
