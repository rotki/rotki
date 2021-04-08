<template>
  <div
    class="amount-display"
    :class="{
      'blur-content': privacyMode,
      'amount-display--profit': pnl && value.gt(0),
      'amount-display--loss': pnl && value.lt(0)
    }"
  >
    <v-skeleton-loader
      :loading="loading"
      min-width="60"
      max-width="70"
      class="d-flex flex-row align-baseline"
      type="text"
    >
      <amount-currency
        v-if="!renderValue.isNaN() && currencyLocation === 'before'"
        class="mr-1 ml-1"
        :show-currency="shownCurrency"
        :currency="currency"
        :asset="symbol"
      />
      <span>
        <v-tooltip
          top
          open-delay="400ms"
          :disabled="
            ((!!fiatCurrency ||
              renderValue.decimalPlaces() <= floatingPrecision) &&
              !tooltip) ||
            isPriceAsset
          "
        >
          <template #activator="{ on, attrs }">
            <span
              data-cy="display-amount"
              class="amount-display__value text-no-wrap"
              v-bind="attrs"
              v-on="on"
            >
              {{ formattedValue }}
            </span>
          </template>
          <span class="amount-display__full-value">
            {{ fullValue }}
          </span>
        </v-tooltip>
      </span>
      <amount-currency
        v-if="!renderValue.isNaN() && currencyLocation === 'after'"
        class="ml-1"
        :asset-padding="assetPadding"
        :show-currency="shownCurrency"
        :currency="currency"
        :asset="symbol"
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
import { AssetInfoGetter, ExchangeRateGetter } from '@/store/balances/types';
import {
  AMOUNT_ROUNDING_MODE,
  VALUE_ROUNDING_MODE
} from '@/store/settings/consts';
import { GeneralSettings } from '@/typing/types';
import { bigNumberify } from '@/utils/bignumbers';
import RoundingMode = BigNumber.RoundingMode;

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
    ...mapState('settings', [AMOUNT_ROUNDING_MODE, VALUE_ROUNDING_MODE]),
    ...mapState('session', ['privacyMode', 'scrambleData']),
    ...mapGetters('balances', ['exchangeRate', 'assetInfo'])
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
  @Prop({ required: false, type: String, default: '' })
  priceAsset!: string;
  @Prop({ required: false, type: Boolean, default: false })
  integer!: boolean;
  @Prop({
    required: false,
    type: Number,
    default: 0,
    validator: chars => chars >= 0 && chars <= 5
  })
  assetPadding!: number;
  @Prop({ required: false, type: Boolean, default: false })
  pnl!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  tooltip!: boolean;

  currency!: Currency;
  privacyMode!: boolean;
  scrambleData!: boolean;
  floatingPrecision!: number;
  thousandSeparator!: string;
  decimalSeparator!: string;
  currencyLocation!: GeneralSettings['currencyLocation'];
  exchangeRate!: ExchangeRateGetter;
  amountRoundingMode!: RoundingMode;
  valueRoundingMode!: RoundingMode;
  assetInfo!: AssetInfoGetter;

  get symbol(): string {
    if (!this.asset) {
      return '';
    }
    return this.assetInfo(this.asset)?.symbol ?? this.asset;
  }

  get shownCurrency(): ShownCurrency {
    return this.showCurrency === 'none' && !!this.fiatCurrency
      ? 'symbol'
      : this.showCurrency;
  }

  get isPriceAsset(): boolean {
    return this.currency.ticker_symbol === this.priceAsset;
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
    if (this.isPriceAsset) {
      return bigNumberify(1).toFormat(this.floatingPrecision);
    }
    return this.formatValue(this.renderValue);
  }

  get fullValue(): string {
    const value = this.convertFiat
      ? this.convertValue(this.renderValue)
      : this.renderValue;
    return value.toFormat(value.decimalPlaces());
  }

  get rounding(): RoundingMode | undefined {
    const { ticker_symbol } = this.currency;
    const isValue = this.fiatCurrency === ticker_symbol;
    let rounding: BigNumber.RoundingMode | undefined = undefined;
    if (isValue) {
      rounding = this.valueRoundingMode;
    } else if (!this.convertFiat) {
      rounding = this.amountRoundingMode;
    }
    return rounding;
  }

  private convertValue(value: BigNumber): BigNumber {
    const { ticker_symbol } = this.currency;
    const rate = this.exchangeRate(ticker_symbol);
    return rate ? value.multipliedBy(rate) : value;
  }

  formatValue(value: BigNumber): string {
    const floatingPrecision = this.integer ? 0 : this.floatingPrecision;
    const price = this.convertFiat ? this.convertValue(value) : value;

    if (price.isNaN()) {
      return '-';
    }

    const formattedValue = displayAmountFormatter.format(
      price,
      floatingPrecision,
      this.thousandSeparator,
      this.decimalSeparator,
      this.rounding
    );

    const hiddenDecimals = price.decimalPlaces() > floatingPrecision;
    if (hiddenDecimals && this.rounding === BigNumber.ROUND_UP) {
      return `< ${formattedValue}`;
    } else if (
      price.lt(1) &&
      hiddenDecimals &&
      this.rounding === BigNumber.ROUND_DOWN
    ) {
      return `> ${formattedValue}`;
    }
    return formattedValue;
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

  &--profit {
    color: var(--v-rotki-gain-base);
  }

  &--loss {
    color: var(--v-rotki-loss-base);
  }
}

.blur-content {
  filter: blur(0.75em);
}
</style>
