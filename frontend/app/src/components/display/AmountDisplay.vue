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
        :show-currency="showCurrency"
        :currency="currency"
        :asset="asset"
      />
      <span
        v-if="fiatCurrency && fiatCurrency !== currency.ticker_symbol"
        class="amount-display__value"
      >
        {{
          renderValue
            | calculatePrice(exchangeRate(currency.ticker_symbol))
            | formatPrice(
              thousandSeparator,
              decimalSeparator,
              floatingPrecision
            )
        }}
      </span>
      <span
        v-else-if="fiatCurrency === currency.ticker_symbol"
        class="amount-display__value"
      >
        {{
          renderValue
            | formatPrice(
              thousandSeparator,
              decimalSeparator,
              floatingPrecision,
              BIGNUMBER_ROUND_DOWN
            )
        }}
      </span>
      <span v-else class="amount-display__value">
        {{
          renderValue
            | formatPrice(
              thousandSeparator,
              decimalSeparator,
              integer ? 0 : floatingPrecision,
              BIGNUMBER_ROUND_UP
            )
        }}
      </span>
      <v-tooltip v-if="!fiatCurrency" top>
        <template #activator="{ on }">
          <span
            v-if="renderValue.decimalPlaces() > floatingPrecision"
            class="amount-display__asterisk"
            v-on="on"
          >
            *
          </span>
        </template>
        <span v-if="fiatCurrency" class="amount-display__full-value">
          {{
            renderValue | calculatePrice(exchangeRate(currency.ticker_symbol))
          }}
        </span>
        <span v-else class="amount-display__full-value">
          {{ renderValue.toFormat(renderValue.decimalPlaces()) }}
        </span>
      </v-tooltip>
      <amount-currency
        v-if="!renderValue.isNaN() && currencyLocation === 'after'"
        class="ml-2"
        :show-currency="showCurrency"
        :currency="currency"
        :asset="asset"
      />
    </v-skeleton-loader>
  </div>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AmountCurrency from '@/components/display/AmountCurrency.vue';
import { Currency } from '@/model/currency';
import { GeneralSettings } from '@/typing/types';
import { bigNumberify } from '@/utils/bignumbers';

const { mapGetters, mapState } = createNamespacedHelpers('session');

const { mapGetters: mapBalancesGetters } = createNamespacedHelpers('balances');

@Component({
  components: {
    AmountCurrency
  },
  computed: {
    ...mapGetters([
      'floatingPrecision',
      'currency',
      'thousandSeparator',
      'decimalSeparator',
      'currencyLocation'
    ]),
    ...mapState(['privacyMode', 'scrambleData']),
    ...mapBalancesGetters(['exchangeRate'])
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
  showCurrency!: string;
  @Prop({ required: false, default: '' })
  asset!: string;
  @Prop({ required: false, type: Boolean, default: false })
  integer!: boolean;

  currency!: Currency;
  privacyMode!: boolean;
  scrambleData!: boolean;
  floatingPrecision!: number;
  thousandSeparator!: string;
  decimalSeparator!: string;
  currencyLocation!: GeneralSettings['currencyLocation'];
  BIGNUMBER_ROUND_DOWN = BigNumber.ROUND_DOWN;
  BIGNUMBER_ROUND_UP = BigNumber.ROUND_UP;

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
}
</script>

<style scoped lang="scss">
.amount-display {
  display: inline-block;

  span {
    display: inline-block;
  }

  &__asterisk {
    position: relative;
    top: -0.2em;
    font-weight: 500;
    font-size: 0.8em;

    &:hover {
      cursor: pointer;
    }
  }
}

td {
  &.text-end {
    .amount-display {
      &__asterisk {
        float: right;
        margin-right: -0.6em;
        top: -0.2em;
      }
    }
  }
}

.blur-content {
  filter: blur(0.75em);
}
</style>
