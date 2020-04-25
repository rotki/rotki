<template>
  <span>
    <span v-if="usdValue" class="amount-display__value">
      {{
        value
          | calculatePrice(exchangeRate(currency.ticker_symbol))
          | formatPrice(floatingPrecision)
      }}
    </span>
    <span v-else class="amount-display__value">
      {{ value | formatPrice(floatingPrecision) }}
    </span>

    <v-tooltip top>
      <template #activator="{ on }">
        <span
          v-if="value.decimalPlaces() > floatingPrecision"
          class="amount-display__asterisk"
          v-on="on"
        >
          *
        </span>
      </template>
      <span v-if="usdValue" class="amount-display__full-value">
        {{ value | calculatePrice(exchangeRate(currency.ticker_symbol)) }}
      </span>
      <span v-else class="amount-display__full-value">
        {{ value }}
      </span>
    </v-tooltip>
  </span>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { Currency } from '@/model/currency';

const { mapGetters } = createNamespacedHelpers('session');
const { mapGetters: mapBalancesGetters } = createNamespacedHelpers('balances');

@Component({
  computed: {
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapBalancesGetters(['exchangeRate'])
  }
})
export default class AmountDisplay extends Vue {
  @Prop({ required: true })
  value!: BigNumber;
  @Prop({ required: false, default: false, type: Boolean })
  usdValue!: boolean;

  currency!: Currency;
  floatingPrecision!: number;
}
</script>

<style scoped lang="scss">
.amount-display {
  &__asterisk {
    font-weight: 500;
    padding: 2px;
    &:hover {
      cursor: pointer;
    }
  }
}
</style>
