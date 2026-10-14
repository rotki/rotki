<script setup lang="ts">
import type { AssetDisplay } from '@/modules/assets/types';
import { type BigNumber, Zero } from '@rotki/common';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';

/** A staking card's main figure, read first: the asset's icon, the amount large, its value below. */
const { asset, calculateValue = false, value } = defineProps<{
  asset: string;
  value: { amount: BigNumber; value?: BigNumber };
  loading?: boolean;
  /** Prices the amount at the asset's current price, for figures that come without a value. */
  calculateValue?: boolean;
}>();

const { getAssetPrice } = usePriceUtils();

const assetDisplay: AssetDisplay = { iconOnly: true, size: '32px' };

const fiatValue = computed<BigNumber>(() => {
  if (!calculateValue)
    return value.value ?? Zero;
  const price = getAssetPrice(asset, Zero);
  return price.gt(0) ? price.multipliedBy(value.amount) : Zero;
});
</script>

<template>
  <div class="flex items-center gap-3">
    <AssetDetails
      :asset="asset"
      :display="assetDisplay"
    />
    <div class="flex flex-col">
      <AssetAmountDisplay
        :asset="asset"
        :amount="value.amount"
        :loading="loading"
        class="text-h6 font-medium"
      />
      <FiatDisplay
        :value="fiatValue"
        :loading="loading"
        symbol="ticker"
        class="text-rui-text-secondary"
      />
    </div>
  </div>
</template>
