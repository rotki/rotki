<script setup lang="ts">
import { type Balance } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    asset?: string;
    value?: Balance | null;
    noIcon?: boolean;
    noJustify?: boolean;
    align?: string;
    mode?: 'gain' | 'loss' | '';
    assetPadding?: number;
    ticker?: boolean;
    loading?: boolean;
    iconSize?: string;
    calculateValue?: boolean;
  }>(),
  {
    asset: '',
    value: null,
    noIcon: false,
    noJustify: false,
    align: 'end',
    mode: '',
    assetPadding: 0,
    ticker: true,
    loading: false,
    iconSize: '24px',
    calculateValue: false
  }
);

const { asset, value, calculateValue } = toRefs(props);

const amount = useValueOrDefault(
  useRefMap(value, value => value?.amount),
  Zero
);
const usdValue = useValueOrDefault(
  useRefMap(value, value => value?.usdValue),
  Zero
);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { assetPrice, toSelectedCurrency } = useBalancePricesStore();

const valueCurrency = computed(() => {
  if (!get(calculateValue)) {
    return 'USD';
  }

  return get(currencySymbol);
});

const valueInCurrency = computed(() => {
  if (!get(calculateValue)) {
    return get(usdValue);
  }

  const owned = get(amount);
  const ethPrice = assetPrice(get(asset));

  if (isDefined(ethPrice)) {
    return owned.multipliedBy(get(toSelectedCurrency(ethPrice)));
  }
  return Zero;
});

const css = useCssModule();
</script>

<template>
  <div
    class="flex flex-row shrink pt-1 pb-1 items-center"
    :class="{
      'justify-end': !noJustify,
      [css.gain]: mode === 'gain',
      [css.loss]: mode === 'loss'
    }"
  >
    <div :class="`d-flex flex-column align-${align}`">
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
        class="block grey--text"
      />
    </div>
    <AssetLink v-if="!noIcon" class="ml-4" icon :asset="asset">
      <AssetIcon :identifier="asset" :size="iconSize" />
    </AssetLink>
  </div>
</template>

<style module lang="scss">
.gain {
  color: #4caf50 !important;
}

.loss {
  color: #d32f2f !important;
}
</style>
