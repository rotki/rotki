<script setup lang="ts">
import AssetLink from '@/components/assets/AssetLink.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useValueOrDefault } from '@/composables/utils/useValueOrDefault';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { type Balance, Zero } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    asset?: string;
    value?: Balance | null;
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
const usdValue = useValueOrDefault(
  useRefMap(value, value => value?.usdValue),
  Zero,
);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { assetPrice, toSelectedCurrency } = usePriceUtils();

const valueCurrency = computed(() => {
  if (!get(calculateValue))
    return 'USD';

  return get(currencySymbol);
});

const valueInCurrency = computed(() => {
  if (!get(calculateValue))
    return get(usdValue);

  const owned = get(amount);
  const ethPrice = assetPrice(get(asset));

  if (isDefined(ethPrice))
    return owned.multipliedBy(get(toSelectedCurrency(ethPrice)));

  return Zero;
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
      <AmountDisplay
        :loading="loading"
        :asset="asset"
        :asset-padding="assetPadding"
        :value="amount"
        class="block font-medium"
      />
      <AmountDisplay
        :fiat-currency="valueCurrency"
        :asset-padding="assetPadding"
        :value="valueInCurrency"
        :show-currency="ticker ? 'ticker' : 'none'"
        :loading="loading"
        class="block text-rui-text-secondary"
      />
    </div>
    <AssetLink
      v-if="!noIcon"
      :asset="asset"
    >
      <AssetIcon
        :identifier="asset"
        :size="iconSize"
        class="flex"
      />
    </AssetLink>
  </div>
</template>
