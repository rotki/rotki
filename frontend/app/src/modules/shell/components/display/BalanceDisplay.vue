<script setup lang="ts">
import type { AssetDisplay } from '@/modules/assets/types';
import { type Balance, type BigNumber, Zero } from '@rotki/common';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useValueOrDefault } from '@/modules/core/common/use-value-or-default';

const {
  align = 'end',
  asset = '',
  calculateValue = false,
  iconSize = '24px',
  loading = false,
  mode = '',
  noIcon = false,
  noJustify = false,
  ticker = true,
  value = null,
} = defineProps<{
  asset?: string;
  value?: Partial<Balance> | null;
  noIcon?: boolean;
  noJustify?: boolean;
  align?: 'start' | 'end';
  mode?: 'gain' | 'loss' | '';
  ticker?: boolean;
  loading?: boolean;
  iconSize?: string;
  calculateValue?: boolean;
}>();

const amount = useValueOrDefault(
  () => value?.amount,
  Zero,
);
const balanceValue = useValueOrDefault(
  () => value?.value,
  Zero,
);

const { getAssetPrice } = usePriceUtils();

// Computed rather than a template literal: this renders in every balance table cell.
const assetDisplay = computed<AssetDisplay>(() => ({ iconOnly: true, size: iconSize }));

const valueInCurrency = computed<BigNumber>(() => {
  if (!calculateValue)
    return get(balanceValue);

  const price = getAssetPrice(asset, Zero);
  return price.gt(0) ? price.multipliedBy(get(amount)) : Zero;
});
</script>

<template>
  <div
    class="flex shrink py-1 gap-4 items-center"
    :class="{
      'justify-end': !noJustify,
      'text-rui-success': mode === 'gain',
      'text-rui-error': mode === 'loss',
    }"
  >
    <div
      class="flex flex-col"
      :class="{
        'items-start': align === 'start',
        'items-end': align === 'end',
      }"
    >
      <AssetAmountDisplay
        :asset="asset"
        :amount="amount"
        :loading="loading"
        class="block font-medium"
      />
      <FiatDisplay
        :value="valueInCurrency"
        :loading="loading"
        :symbol="ticker ? 'ticker' : 'none'"
        class="block text-rui-text-secondary"
      />
    </div>
    <AssetDetails
      v-if="!noIcon"
      :asset="asset"
      :display="assetDisplay"
    />
  </div>
</template>
