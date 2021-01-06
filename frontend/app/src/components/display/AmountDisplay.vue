<template>
  <div class="amount-display" :class="privacyMode ? 'blur-content' : ''">
    <v-skeleton-loader
      :loading="loading"
      min-width="60"
      max-width="70"
      class="d-flex flex-row align-baseline"
      type="text"
    >
      <amount-currency
        v-if="!renderValue.isNaN() && currencyLocation === 'before'"
        class="ml-2"
        :show-currency="shownCurrency"
        :currency="currency"
        :asset="asset"
      />
      <v-tooltip
        top
        open-delay="400ms"
        :disabled="
          !!fiatCurrency || renderValue.decimalPlaces() <= floatingPrecision
        "
      >
        <template #activator="{ on, attrs }">
          <span class="amount-display__value" v-bind="attrs" v-on="on">
            {{ formattedValue }}
          </span>
        </template>
        <span class="amount-display__full-value">
          {{ fullValue }}
        </span>
      </v-tooltip>
      <amount-currency
        v-if="!renderValue.isNaN() && currencyLocation === 'after'"
        class="ml-1"
        :asset-padding="assetPadding"
        :show-currency="shownCurrency"
        :currency="currency"
        :asset="asset"
      />
    </v-skeleton-loader>
  </div>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import AmountCurrency from '@/components/display/AmountCurrency.vue';
import { displayAmountFormatter } from '@/data/amount_formatter';
import { Currency } from '@/model/currency';
import { GeneralSettings } from '@/typing/types';
import { bigNumberify } from '@/utils/bignumbers';

type ShownCurrency = 'none' | 'ticker' | 'symbol' | 'name';

@Component({
  components: {
    AmountCurrency
  },
  computed: {
    ...mapGetters('session', ['floatingPrecision', 'currency']),
    ...mapGetters('settings', [
      'thousandSeparator',
      'decimalSeparator',
      'currencyLocation'
    ]),
    ...mapState('session', ['privacyMode', 'scrambleData']),
    ...mapGetters('balances', ['exchangeRate'])
  }
})
export default class AmountDisplay extends Vue {
  @Prop({ required: true })
  value!: BigNumber;
  @Prop({ required: false, type: Boolean, default: false })
  loading!: boolean;
  @Prop({ required: false })
  amount!: BigNumber;
  @Prop({ required: false, default: null, type: String })
  fiatCurrency!: string | null;
  @Prop({
    required: false,
    default: 'none',
    validator: showCurrency => {
      return ['none', 'ticker', 'symbol', 'name'].indexOf(showCurrency) > -1;
    }
  })
  showCurrency!: ShownCurrency;
  @Prop({ required: false, default: '' })
  asset!: string;
  @Prop({ required: false, type: Boolean, default: false })
  integer!: boolean;
  @Prop({
    required: false,
    type: Number,
    default: 0,
    validator: chars => chars >= 0 && chars <= 5
  })
  assetPadding!: number;

  currency!: Currency;
  privacyMode!: boolean;
  scrambleData!: boolean;
  floatingPrecision!: number;
  thousandSeparator!: string;
  decimalSeparator!: string;
  currencyLocation!: GeneralSettings['currencyLocation'];
  exchangeRate!: (currency: string) => number;

  get shownCurrency(): ShownCurrency {
    return this.showCurrency === 'none' && !!this.fiatCurrency
      ? 'symbol'
      : this.showCurrency;
  }

  get renderValue(): BigNumber {
    const multiplier = [10, 100, 1000];
    let valueToRender;

    // return a random number if scrambeData is on
    if (this.scrambleData) {
      return BigNumber.random()
        .multipliedBy(multiplier[Math.floor(Math.random() * multiplier.length)])
        .plus(BigNumber.random(2));
    }

    if (this.amount && this.fiatCurrency === this.currency.ticker_symbol) {
      valueToRender = this.amount;
    } else {
      valueToRender = this.value;
    }

    // in certain cases where what is passed as a value is a string and not BigNumber, convert it
    if (typeof valueToRender === 'string') {
      return bigNumberify(valueToRender);
    }
    return valueToRender;
  }

  get convertFiat(): boolean {
    const { ticker_symbol } = this.currency;
    return !!this.fiatCurrency && this.fiatCurrency !== ticker_symbol;
  }

  get formattedValue(): string {
    return this.formatValue(this.renderValue);
  }

  get fullValue(): string {
    return this.renderValue.toFormat(this.renderValue.decimalPlaces());
  }

  private convertValue(value: BigNumber): BigNumber {
    const { ticker_symbol } = this.currency;
    const rate = bigNumberify(this.exchangeRate(ticker_symbol));
    return value.multipliedBy(rate);
  }

  formatValue(value: BigNumber): string {
    const { ticker_symbol } = this.currency;
    const roundDown = this.fiatCurrency === ticker_symbol;
    const floatingPrecision = this.integer ? 0 : this.floatingPrecision;

    let rounding: BigNumber.RoundingMode | undefined = undefined;
    if (roundDown) {
      rounding = BigNumber.ROUND_DOWN;
    } else if (!this.convertFiat) {
      rounding = BigNumber.ROUND_UP;
    }

    const price = this.convertFiat ? this.convertValue(value) : value;

    return price.isNaN()
      ? '-'
      : displayAmountFormatter.format(
          price,
          floatingPrecision,
          this.thousandSeparator,
          this.decimalSeparator,
          rounding
        );
  }
}
</script>

<style scoped lang="scss">
.amount-display {
  display: inline-block;

  span {
    display: inline-block;
  }

  &:hover {
    cursor: pointer;
  }
}

.blur-content {
  filter: blur(0.75em);
}
</style>
