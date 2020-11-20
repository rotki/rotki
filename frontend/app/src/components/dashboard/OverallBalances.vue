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
          <loading
            v-if="anyLoading"
            class="overall-balances__net-worth__loading text-start ms-2"
          />
          <amount-display
            show-currency="symbol"
            :fiat-currency="currencySymbol"
            :value="totalNetWorth"
          />
        </div>
        <div class="overall-balances__net-worth-change py-2">
          <span
            :class="balanceClass"
            class="pa-1 px-2 d-flex flex-row overall-balances__net-worth-change__pill"
          >
            <span class="me-2">{{ indicator }}</span>
            <amount-display
              v-if="!anyLoading"
              show-currency="symbol"
              :fiat-currency="currencySymbol"
              :value="balanceDelta"
            />
            <percentage-display
              v-if="!anyLoading"
              class="ms-2 px-1 text--secondary pe-2"
              :value="percentage"
            />
          </span>
        </div>

        <div class="overall-balances__timeframe-chips text-center">
          <v-tooltip v-if="!premium" top>
            <template #activator="{ on, attrs }">
              <v-icon
                class="overall-balances__premium"
                small
                v-bind="attrs"
                v-on="on"
              >
                mdi-lock
              </v-icon>
            </template>
            <span v-text="$t('overall_balances.premium_hint')" />
          </v-tooltip>
          <v-chip
            v-for="(timeframe, i) in timeframes"
            :key="i"
            :class="activeClass(timeframe.text)"
            class="ma-2"
            :disabled="!premium && !worksWithoutPremium(timeframe.text)"
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
import { Component, Mixins, Watch } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';

import {
  TIMEFRAME_ALL,
  TIMEFRAME_TWO_WEEKS,
  TIMEFRAME_WEEK,
  timeframes
} from '@/components/dashboard/const';
import NetWorthChart from '@/components/dashboard/NetworthChart.vue';
import { TimeFramePeriod, Timeframes } from '@/components/dashboard/types';
import AmountDisplay from '@/components/display/AmountDisplay.vue';

import Loading from '@/components/helper/Loading.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { NetValue } from '@/services/types-api';
import { Section } from '@/store/const';
import { bigNumberify } from '@/utils/bignumbers';

@Component({
  components: { Loading, AmountDisplay, NetWorthChart },
  computed: {
    ...mapGetters('session', ['currencySymbol']),
    ...mapGetters('statistics', ['netValue', 'totalNetWorth'])
  },
  methods: {
    ...mapActions('statistics', ['fetchNetValue'])
  }
})
export default class OverallBox extends Mixins(PremiumMixin, StatusMixin) {
  currencySymbol!: string;
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

  activeClass(timeframePeriod: TimeFramePeriod): string {
    return timeframePeriod === this.selection
      ? 'overall-balances__timeframe-chips--active'
      : '';
  }

  worksWithoutPremium(period: TimeFramePeriod): boolean {
    return [TIMEFRAME_WEEK, TIMEFRAME_TWO_WEEKS].includes(period);
  }

  get timeframes(): Timeframes {
    return timeframes;
  }

  get startingValue(): BigNumber {
    const data = this.timeframeData.data;
    let start = data[0];
    if (start === 0) {
      for (let i = 1; i < data.length; i++) {
        if (data[i] > 0) {
          start = data[i];
          break;
        }
      }
    }
    return bigNumberify(start);
  }

  get balanceDelta(): BigNumber {
    return this.totalNetWorth.minus(this.startingValue);
  }

  get percentage(): string {
    const bigNumber = this.balanceDelta
      .div(this.startingValue)
      .multipliedBy(100);

    return bigNumber.isFinite() ? bigNumber.toFormat(2) : '-';
  }

  get timeframeData(): NetValue {
    const startingDate = timeframes[this.selection].startingDate();
    return this.netValue(startingDate);
  }

  @Watch('premium')
  async onPremiumChange() {
    await this.fetchNetValue();
  }

  created() {
    if (!this.premium) {
      this.activeTimeframe = TIMEFRAME_TWO_WEEKS;
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

  &__net-worth {
    ::v-deep {
      .amount-display {
        &__value {
          font-size: 3.5em;
          line-height: 4rem;
        }

        .amount-currency {
          font-size: 2rem;
        }
      }
    }

    &__loading {
      font-size: 1.5em;
      line-height: 1em;
      margin-bottom: -10px;
    }
  }

  &__net-worth-change {
    display: flex;
    justify-content: center;
    align-items: baseline;
    margin-bottom: 1em;
    min-height: 32px;

    span {
      border-radius: 0.75em;
    }

    &__pill {
      min-height: 32px;
      min-width: 170px;
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

  &__premium {
    margin-left: -16px;
  }
}
</style>
