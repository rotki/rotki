<template>
  <v-card class="overall-balances mb-6">
    <v-row no-gutters class="pa-5">
      <v-col
        cols="12"
        md="6"
        lg="5"
        class="d-flex flex-column align-center justify-center"
      >
        <div
          class="
            overall-balances__net-worth
            text-center
            font-weight-medium
            mb-2
          "
        >
          <loading
            v-if="anyLoading"
            class="overall-balances__net-worth__loading text-start ms-2"
          />
          <div :style="`font-size: ${adjustedTotalNetWorthFontSize}em`">
            <amount-display
              class="ps-4"
              show-currency="symbol"
              :fiat-currency="currencySymbol"
              :value="totalNetWorth"
            />
          </div>
        </div>
        <div class="overall-balances__net-worth-change py-2">
          <span
            :class="balanceClass"
            class="
              pa-1
              px-2
              d-flex
              flex-row
              overall-balances__net-worth-change__pill
            "
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
        <timeframe-selector
          v-model="activeTimeframe"
          :visible-timeframes="visibleTimeframes"
        />
      </v-col>
      <v-col cols="12" md="6" lg="7" class="d-flex">
        <div
          class="
            d-flex
            justify-center
            align-center
            flex-grow-1
            overall-balances__net-worth-chart
          "
        >
          <net-worth-chart
            v-if="!anyLoading"
            :chart-data="timeframeData"
            :timeframe="selection"
            :timeframes="timeframes"
          />
          <div v-else class="overall-balances__net-worth-chart__loader">
            <v-progress-circular
              indeterminate
              class="align-self-center"
              color="primary"
            />
            <div class="pt-5 text-caption">
              {{ $t('overall_balances.loading') }}
            </div>
          </div>
        </div>
      </v-col>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { TimeUnit } from '@rotki/common/lib/settings';
import {
  TimeFramePeriod,
  Timeframes,
  timeframes
} from '@rotki/common/lib/settings/graphs';
import dayjs from 'dayjs';
import { Component, Mixins, Watch } from 'vue-property-decorator';
import { mapActions, mapGetters, mapMutations, mapState } from 'vuex';
import NetWorthChart from '@/components/dashboard/NetworthChart.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import Loading from '@/components/helper/Loading.vue';
import TimeframeSelector from '@/components/helper/TimeframeSelector.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import StatusMixin from '@/mixins/status-mixin';
import { NetValue } from '@/services/types-api';
import { Section } from '@/store/const';
import { isPeriodAllowed } from '@/store/settings/utils';
import { ActionStatus } from '@/store/types';
import {
  FrontendSettingsPayload,
  LAST_KNOWN_TIMEFRAME
} from '@/types/frontend-settings';
import { bigNumberify } from '@/utils/bignumbers';

@Component({
  components: { TimeframeSelector, Loading, AmountDisplay, NetWorthChart },
  computed: {
    ...mapGetters('session', ['currencySymbol', 'floatingPrecision']),
    ...mapGetters('statistics', ['netValue', 'totalNetWorth']),
    ...mapState('session', ['timeframe']),
    ...mapGetters('settings', ['visibleTimeframes'])
  },
  methods: {
    ...mapActions('statistics', ['fetchNetValue']),
    ...mapMutations('session', ['setTimeframe']),
    ...mapActions('settings', ['updateSetting'])
  }
})
export default class OverallBox extends Mixins(PremiumMixin, StatusMixin) {
  currencySymbol!: string;
  netValue!: (startingDate: number) => NetValue;
  totalNetWorth!: BigNumber;
  fetchNetValue!: () => Promise<void>;
  timeframe!: TimeFramePeriod;
  visibleTimeframes!: TimeFramePeriod[];
  setTimeframe!: (timeframe: TimeFramePeriod) => void;
  updateSetting!: (payload: FrontendSettingsPayload) => Promise<ActionStatus>;
  floatingPrecision!: number;

  get activeTimeframe(): TimeFramePeriod {
    return this.timeframe;
  }

  set activeTimeframe(value: TimeFramePeriod) {
    this.setTimeframe(value);
    this.updateSetting({ [LAST_KNOWN_TIMEFRAME]: value });
  }

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

  get timeframes(): Timeframes {
    return timeframes((unit, amount) =>
      dayjs().subtract(amount, unit).startOf(TimeUnit.DAY).unix()
    );
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

  get adjustedTotalNetWorthFontSize(): number {
    const digits = this.totalNetWorth
      .toFormat(this.floatingPrecision)
      .replace(/\./g, '')
      .replace(/,/g, '').length;

    // this number adjusted visually
    // when we use max floating precision (8), it won't overlap
    return Math.min(1, 12 / digits);
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
    const startingDate = this.timeframes[this.selection].startingDate();
    return this.netValue(startingDate);
  }

  @Watch('premium')
  async onPremiumChange() {
    await this.fetchNetValue();
  }

  created() {
    if (!this.premium && !isPeriodAllowed(this.activeTimeframe)) {
      this.activeTimeframe = TimeFramePeriod.TWO_WEEKS;
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
          @media (max-width: 450px) {
            font-size: 2.4em;
            line-height: 2.4rem;
          }
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
