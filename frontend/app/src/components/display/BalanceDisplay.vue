<template>
  <div
    class="d-flex flex-row balance_display shrink pt-1 pb-1 align-center"
    :class="{
      'justify-end': !noJustify,
      'balance-display--gain': mode === 'gain',
      'balance-display--loss': mode === 'loss'
    }"
  >
    <asset-icon
      v-if="!noIcon"
      :identifier="asset"
      :symbol="getSymbol(asset)"
      size="24px"
      class="mr-1"
    />
    <div
      class="ml-1 d-flex flex-column align-end"
      :style="{ 'min-width': `${minWidth}ch` }"
    >
      <amount-display
        :loading-="!!!value"
        :asset="getSymbol(asset)"
        :asset-padding="assetPadding"
        :value="value.amount"
        class="d-block font-weight-medium"
      />
      <amount-display
        :loading-="!!!value"
        fiat-currency="USD"
        :asset-padding="assetPadding"
        :value="value.usdValue"
        class="d-block grey--text"
      />
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import AssetMixin from '@/mixins/asset-mixin';
import { Balance } from '@/services/types-api';

@Component({})
export default class BalanceDisplay extends Mixins(AssetMixin) {
  @Prop({ required: true })
  asset!: string;
  @Prop({ required: true })
  value!: Balance | null;
  @Prop({ required: false, type: Boolean, default: false })
  noIcon!: boolean;
  @Prop({ required: false, type: Number, default: 16 })
  minWidth!: number;
  @Prop({ required: false, type: Boolean, default: false })
  noJustify!: boolean;
  @Prop({ required: false, type: String, default: '' })
  mode!: 'gain' | 'loss' | '';
  @Prop({ required: false, type: Number, default: 5 })
  assetPadding!: number;
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
