<template>
  <div class="defi-asset d-flex flex-row align-center">
    <asset-icon
      size="32px"
      :identifier="`_ceth_${asset.tokenAddress}`"
      :symbol="asset.tokenSymbol"
    />
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
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { DefiAsset as Asset } from '@/store/defi/types';

@Component({
  components: { AmountDisplay, AssetIcon }
})
export default class DefiAsset extends Vue {
  @Prop({ required: true })
  asset!: Asset;

  readonly assetPadding: number = 1;
}
</script>
