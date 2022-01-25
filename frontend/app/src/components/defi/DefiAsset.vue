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
import { defineComponent, PropType } from '@vue/composition-api';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { DefiAsset } from '@/store/defi/types';

export default defineComponent({
  name: 'DefiAsset',
  components: { AmountDisplay, AssetIcon },
  props: {
    asset: { required: true, type: Object as PropType<DefiAsset> }
  },
  setup() {
    const assetPadding: number = 1;

    return {
      assetPadding
    };
  }
});
</script>
