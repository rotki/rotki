<script setup lang="ts">
import { type Balance } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    asset: string;
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
const { assetPrice } = useBalancePricesStore();

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
    return owned.multipliedBy(get(ethPrice));
  }
  return Zero;
});

const css = useCssModule();
</script>

<template>
  <div
    class="d-flex flex-row shrink pt-1 pb-1 align-center"
    :class="{
      'justify-end': !noJustify,
      [css.gain]: mode === 'gain',
      [css.loss]: mode === 'loss'
    }"
  >
    <div :class="`d-flex flex-column align-${align}`">
      <amount-display
        :loading="loading"
        :asset="asset"
        :asset-padding="assetPadding"
        :value="amount"
        class="d-block font-weight-medium"
      />
      <amount-display
        :fiat-currency="valueCurrency"
        :asset-padding="assetPadding"
        :value="valueInCurrency"
        :show-currency="ticker ? 'ticker' : 'none'"
        :loading="loading"
        class="d-block grey--text"
      />
    </div>
    <asset-link v-if="!noIcon" class="ml-4" icon :asset="asset">
      <asset-icon :identifier="asset" :size="iconSize" />
    </asset-link>
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
