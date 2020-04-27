<template>
  <span :class="privacyMode ? 'blur-content' : ''">
    <span v-if="fiat" class="amount-display__value">
      {{
        renderValue
          | calculatePrice(exchangeRate(currency.ticker_symbol))
          | formatPrice(2)
      }}
    </span>
    <span v-else class="amount-display__value">
      {{ renderValue | formatPrice(floatingPrecision) }}
    </span>

    <v-tooltip v-if="!fiat" top>
      <template #activator="{ on }">
        <span
          v-if="renderValue.decimalPlaces() > floatingPrecision"
          class="amount-display__asterisk"
          v-on="on"
        >
          *
        </span>
      </template>
      <span v-if="fiat" class="amount-display__full-value">
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
  </span>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { Currency } from '@/model/currency';
import { bigNumberify } from '@/utils/bignumbers';

const { mapGetters } = createNamespacedHelpers('session');
const { mapState } = createNamespacedHelpers('session');

const { mapGetters: mapBalancesGetters } = createNamespacedHelpers('balances');

@Component({
  computed: {
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapState(['privacyMode', 'scrambleData']),
    ...mapBalancesGetters(['exchangeRate']),
    renderValue: function () {
      const multiplier = [10, 100, 1000];

      if (this.$store.state.session.scrambleData) {
        return BigNumber.random()
          .multipliedBy(
            multiplier[Math.floor(Math.random() * multiplier.length)]
          )
          .plus(BigNumber.random(2));
      }
      if (typeof this.$props.value === 'string') {
        return bigNumberify(this.$props.value);
      }
      return this.$props.value;
    }
  }
})
export default class AmountDisplay extends Vue {
  @Prop({ required: true })
  value!: BigNumber;
  @Prop({ required: false, default: false, type: Boolean })
  fiat!: boolean;
  @Prop({
    required: false,
    default: 'none',
    validator: showCurrency => {
      return ['none', 'ticker', 'symbol', 'name'].indexOf(showCurrency) > -1;
    }
  })
  showCurrency!: string;

  currency!: Currency;
  privacyMode!: boolean;
  scrambleData!: boolean;
  floatingPrecision!: number;
}
</script>

<style scoped lang="scss">
td.text-end .amount-display {
  &__asterisk {
    float: right;
    margin-right: -0.6em;
    top: -0.1em;
  }
}

.amount-display {
  &__asterisk {
    font-weight: 500;
    font-size: 0.8em;
    &:hover {
      cursor: pointer;
    }
  }
}
.blur-content {
  color: transparent;
  text-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
}
</style>
