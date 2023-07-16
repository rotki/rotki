<script setup lang="ts">
import { type ComputedRef } from 'vue';
import { type Currency } from '@/types/currencies';

const props = withDefaults(
  defineProps<{
    currency: Currency;
    showCurrency?: 'none' | 'ticker' | 'symbol' | 'name';
    asset?: string;
    assetPadding?: number;
    xl?: boolean;
  }>(),
  {
    showCurrency: 'none',
    asset: '',
    assetPadding: 0,
    xl: false
  }
);

const { asset, assetPadding, showCurrency, currency } = toRefs(props);
const assetStyle = computed(() => {
  const padding = get(assetPadding);
  if (!padding) {
    return {};
  }
  return {
    width: `${padding + 1}ch`,
    'text-align': 'start'
  } as any;
});

const displayAsset = computed(() => {
  const show = get(showCurrency);
  const value = get(currency);
  if (show === 'ticker') {
    return value.tickerSymbol;
  } else if (show === 'symbol') {
    return value.unicodeSymbol;
  } else if (show === 'name') {
    return value.name;
  }

  return '';
});

const { assetSymbol } = useAssetInfoRetrieval();

const symbol: ComputedRef<string> = assetSymbol(asset);

const { isPending } = useAssetCacheStore();
const loading = isPending(asset);
const css = useCssModule();
</script>

<template>
  <VTooltip
    v-if="asset && symbol"
    top
    :disabled="loading || symbol.length <= assetPadding"
    open-delay="400"
    tag="div"
  >
    <template #activator="{ on, attrs }">
      <span
        v-if="!loading"
        data-cy="display-currency"
        v-bind="attrs"
        :style="assetStyle"
        :class="{ [css.xl]: xl }"
        v-on="on"
      >
        {{ symbol }}
      </span>
      <VSkeletonLoader v-else width="30" type="text" height="12" />
    </template>
    <span data-cy="display-currency" :class="{ [css.xl]: xl }">
      {{ symbol }}
    </span>
  </VTooltip>

  <span
    v-else
    :style="assetStyle"
    data-cy="display-currency"
    :class="{ [css.xl]: xl }"
  >
    {{ displayAsset }}
  </span>
</template>

<style module lang="scss">
.xl {
  font-size: 1.5rem;
}
</style>
