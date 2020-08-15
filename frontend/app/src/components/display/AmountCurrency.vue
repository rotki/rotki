<template>
  <fragment>
    <span v-if="showCurrency === 'ticker'" class="amount-currency">
      {{ currency.ticker_symbol }}
    </span>
    <span v-else-if="showCurrency === 'symbol'" class="amount-currency">
      {{ currency.unicode_symbol }}
    </span>
    <span v-else-if="showCurrency === 'name'" class="amount-currency">
      {{ currency.name }}
    </span>
    <span v-else-if="!!asset" class="amount-currency">
      {{ asset }}
    </span>
  </fragment>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import Fragment from '@/components/helper/Fragment';
import { Currency } from '@/model/currency';

@Component({
  components: { Fragment }
})
export default class AmountCurrency extends Vue {
  @Prop({ required: true })
  currency!: Currency;
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
}
</script>

<style scoped lang="scss">
.amount-display {
  .amount-currency {
    margin-left: 5px;
    margin-right: 5px;
    font-size: 0.8em;
  }
}
</style>
