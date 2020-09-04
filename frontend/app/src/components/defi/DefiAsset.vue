<template>
  <div class="defi-asset d-flex flex-row align-center">
    <crypto-icon size="32px" :symbol="asset.tokenSymbol" />
    <span class="ml-3">{{ asset.tokenSymbol }}</span>
    <v-spacer />
    <div class="d-flex flex-column align-end">
      <amount-display
        :asset-padding="assetPadding"
        :value="asset.balance.amount"
        class="defi-asset__amount font-weight-medium"
      />
      <amount-display
        :asset-padding="assetPadding"
        :value="asset.balance.usdValue"
        fiat-currency="USD"
      />
    </div>
  </div>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import CryptoIcon from '@/components/CryptoIcon.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { DefiAsset as Asset } from '@/store/defi/types';

@Component({
  components: { AmountDisplay, CryptoIcon }
})
export default class DefiAsset extends Vue {
  @Prop({ required: true })
  asset!: Asset;

  readonly assetPadding: number = 1;
}
</script>
