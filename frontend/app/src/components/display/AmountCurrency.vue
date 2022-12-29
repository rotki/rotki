<script setup lang="ts">
import { type ComputedRef, type PropType } from 'vue';
import { type Currency } from '@/types/currencies';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useAssetCacheStore } from '@/store/assets/asset-cache';

const props = defineProps({
  currency: { required: true, type: Object as PropType<Currency> },
  showCurrency: {
    required: false,
    default: 'none',
    type: String as PropType<'none' | 'ticker' | 'symbol' | 'name'>,
    validator: (showCurrency: string) => {
      return ['none', 'ticker', 'symbol', 'name'].includes(showCurrency);
    }
  },
  asset: { required: false, default: '', type: String },
  assetPadding: {
    required: false,
    type: Number,
    default: 0,
    validator: (chars: number) => chars >= 0 && chars <= 5
  }
});

const { asset, assetPadding, showCurrency, currency } = toRefs(props);
const assetStyle = computed(() => {
  if (!get(assetPadding)) {
    return {};
  }
  return {
    width: `${get(assetPadding) + 1}ch`,
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

const symbol: ComputedRef<string> = computed(() => {
  if (get(asset)) {
    return get(assetSymbol(get(asset)));
  }

  return '';
});

const { isPending } = useAssetCacheStore();
const loading = isPending(asset);
</script>

<template>
  <v-tooltip
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
        v-on="on"
      >
        {{ symbol }}
      </span>
      <v-skeleton-loader v-else width="30" type="text" height="12" />
    </template>
    <span data-cy="display-currency">
      {{ symbol }}
    </span>
  </v-tooltip>

  <span v-else :style="assetStyle" data-cy="display-currency">
    {{ displayAsset }}
  </span>
</template>
