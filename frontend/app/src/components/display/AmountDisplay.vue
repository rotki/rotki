<template>
  <span class="amount-display" :class="privacyMode ? 'blur-content' : ''">
    <span
      v-if="fiatCurrency && fiatCurrency !== currency.ticker_symbol"
      class="amount-display__value"
    >
      {{
        renderValue
          | calculatePrice(exchangeRate(currency.ticker_symbol))
          | roundDown(floatingPrecision)
      }}
    </span>
    <span
      v-else-if="fiatCurrency === currency.ticker_symbol"
      class="amount-display__value"
    >
      {{ renderValue | roundDown(floatingPrecision) }}
    </span>
    <span v-else class="amount-display__value">
      {{ renderValue | formatPrice(floatingPrecision) }}
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
        {{ renderValue | calculatePrice(exchangeRate(currency.ticker_symbol)) }}
      </span>
      <span v-else class="amount-display__full-value">
        {{ renderValue }}
      </span>
    </v-tooltip>
    <span v-if="showCurrency === 'ticker'" class="amount-display__currency">
      {{ currency.ticker_symbol }}
    </span>
    <span
      v-else-if="showCurrency === 'symbol'"
      class="amount-display__currency"
    >
      {{ currency.unicode_symbol }}
    </span>
    <span v-else-if="showCurrency === 'name'" class="amount-display__currency">
      {{ currency.name }}
    </span>
    <span v-else-if="!!asset" class="amount-display__asset">
      {{ asset }}
    </span>
  </span>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { Currency } from '@/model/currency';
import { bigNumberify } from '@/utils/bignumbers';

const { mapGetters, mapState } = createNamespacedHelpers('session');

const { mapGetters: mapBalancesGetters } = createNamespacedHelpers('balances');

@Component({
  computed: {
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapState(['privacyMode', 'scrambleData']),
    ...mapBalancesGetters(['exchangeRate'])
  }
})
export default class AmountDisplay extends Vue {
  @Prop({ required: true })
  value!: BigNumber;
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
  currency!: Currency;
  privacyMode!: boolean;
  scrambleData!: boolean;
  floatingPrecision!: number;

  get renderValue() {
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
td.text-end .amount-display {
  &__asterisk {
    float: right;
    margin-right: -0.6em;
    top: -0.2em;
  }
}

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

  &__currency {
    display: contents !important;
  }

  &__asset,
  &__currency {
    font-size: 0.82em;
    color: #616161;
    margin-left: 5px;
  }
}

.blur-content {
  filter: blur(0.3em);
}
</style>
