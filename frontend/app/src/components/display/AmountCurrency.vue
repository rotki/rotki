<template>
  <fragment>
    <span
      v-if="showCurrency === 'ticker'"
      class="amount-currency"
      :style="assetStyle"
    >
      {{ currency.ticker_symbol }}
    </span>
    <span
      v-else-if="showCurrency === 'symbol'"
      class="amount-currency"
      :style="assetStyle"
    >
      {{ currency.unicode_symbol }}
    </span>
    <span
      v-else-if="showCurrency === 'name'"
      class="amount-currency"
      :style="assetStyle"
    >
      {{ currency.name }}
    </span>
    <v-tooltip
      v-else-if="!!asset"
      top
      :disabled="asset.length <= assetPadding"
      open-delay="400"
    >
      <template #activator="{ on, attrs }">
        <span
          v-bind="attrs"
          class="amount-currency"
          :style="assetStyle"
          v-on="on"
        >
          {{ asset }}
        </span>
      </template>
      <span v-text="asset" />
    </v-tooltip>

    <span v-else class="amount-currency" :style="assetStyle" />
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
  @Prop({
    required: false,
    type: Number,
    default: 0,
    validator: chars => chars >= 0 && chars <= 5
  })
  assetPadding!: number;

  get assetStyle(): { [key: string]: string } {
    if (!this.assetPadding) {
      return {};
    }
    return {
      width: `${this.assetPadding + 1}ch`,
      'text-align': 'start'
    };
  }
}
</script>

<style scoped lang="scss">
.amount-display {
  .amount-currency {
    margin-left: 5px;
    margin-right: 5px;
    font-size: 0.8em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}
</style>
