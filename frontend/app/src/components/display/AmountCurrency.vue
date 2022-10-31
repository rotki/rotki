<template>
  <v-tooltip
    v-if="!!asset"
    top
    :disabled="asset.length <= assetPadding"
    open-delay="400"
    tag="div"
  >
    <template #activator="{ on, attrs }">
      <span
        data-cy="display-currency"
        v-bind="attrs"
        :style="assetStyle"
        v-on="on"
      >
        {{ asset }}
      </span>
    </template>
    <span data-cy="display-currency">
      {{ asset }}
    </span>
  </v-tooltip>

  <span v-else :style="assetStyle" data-cy="display-currency">
    {{ displayAsset }}
  </span>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import { Currency } from '@/types/currencies';

const props = defineProps({
  currency: { required: true, type: Object as PropType<Currency> },
  showCurrency: {
    required: false,
    default: 'none',
    type: String as PropType<'none' | 'ticker' | 'symbol' | 'name'>,
    validator: (showCurrency: string) => {
      return ['none', 'ticker', 'symbol', 'name'].indexOf(showCurrency) > -1;
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

const { assetPadding, showCurrency, currency } = toRefs(props);
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
</script>
