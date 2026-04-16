<script setup lang="ts">
import { type Balance, Zero } from '@rotki/common';
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

const valueInCurrency = computed<BigNumber>(() => {
  if (!calculateValue)
    return get(balanceValue);

  return getAssetPrice(asset, Zero).multipliedBy(get(amount));
});
</script>

<template>
  <div
    class="flex flex-row shrink py-1 gap-4 items-center"
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
      icon-only
      :size="iconSize"
    />
  </div>
</template>
