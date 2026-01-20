<script setup lang="ts">
import { type Balance, Zero } from '@rotki/common';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useValueOrDefault } from '@/composables/utils/useValueOrDefault';
import { AssetAmountDisplay, FiatDisplay } from '@/modules/amount-display/components';
import { usePriceUtils } from '@/modules/prices/use-price-utils';

const props = withDefaults(
  defineProps<{
    asset?: string;
    value?: Partial<Balance> | null;
    noIcon?: boolean;
    noJustify?: boolean;
    align?: 'start' | 'end';
    mode?: 'gain' | 'loss' | '';
    assetPadding?: number;
    ticker?: boolean;
    loading?: boolean;
    iconSize?: string;
    calculateValue?: boolean;
  }>(),
  {
    align: 'end',
    asset: '',
    assetPadding: 0,
    calculateValue: false,
    iconSize: '24px',
    loading: false,
    mode: '',
    noIcon: false,
    noJustify: false,
    ticker: true,
    value: null,
  },
);

const { asset, calculateValue, value } = toRefs(props);

const amount = useValueOrDefault(
  useRefMap(value, value => value?.amount),
  Zero,
);
const balanceValue = useValueOrDefault(
  useRefMap(value, value => value?.value),
  Zero,
);

const { assetPriceInCurrentCurrency } = usePriceUtils();

const valueInCurrency = computed(() => {
  if (!get(calculateValue))
    return get(balanceValue);

  return get(assetPriceInCurrentCurrency(get(asset))).multipliedBy(get(amount));
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
