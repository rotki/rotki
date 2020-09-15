<template>
  <div
    class="d-flex flex-row balance_display shrink"
    :class="{
      'justify-end': !noJustify,
      'balance-display--gain': mode === 'gain',
      'balance-display--loss': mode === 'loss'
    }"
  >
    <crypto-icon v-if="!noIcon" :symbol="asset" size="24px" class="mr-1" />
    <div
      class="ml-1 d-flex flex-column align-end"
      :style="{ 'min-width': `${minWidth}ch` }"
    >
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
  @Prop({ required: false, type: Boolean, default: false })
  noIcon!: boolean;
  @Prop({ required: false, type: Number, default: 16 })
  minWidth!: number;
  @Prop({ required: false, type: Boolean, default: false })
  noJustify!: boolean;
  @Prop({ required: false, type: String, default: '' })
  mode!: 'gain' | 'loss' | '';

  readonly assetPadding: number = 5;
}
</script>

<style scoped lang="scss">
.balance-display {
  &--gain {
    color: #4caf50 !important;
  }

  &--loss {
    color: #d32f2f !important;
  }
}
</style>
