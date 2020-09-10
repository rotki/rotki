<template>
  <div
    class="d-flex flex-row balance_display shrink"
    :class="$vuetify.breakpoint.lgAndUp ? 'justify-end' : null"
  >
    <crypto-icon :symbol="asset" size="24px" class="mr-2" />
    <div class="ml-2 d-flex flex-column align-end balance_display__amount">
      <amount-display
        :asset="asset"
        :asset-padding="assetPadding"
        :value="value.amount"
        class="d-block font-weight-medium"
      />
      <amount-display
        fiat-currency="USD"
        :asset-padding="assetPadding"
        :value="value.usdValue"
        class="d-block grey--text"
      />
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { Balance } from '@/services/types-api';

@Component({})
export default class BalanceDisplay extends Vue {
  @Prop({ required: true })
  asset!: string;
  @Prop({ required: true })
  value!: Balance;

  readonly assetPadding: number = 5;
}
</script>

<style scoped lang="scss">
.balance_display {
  &__amount {
    min-width: 16ch;
  }
}
</style>
