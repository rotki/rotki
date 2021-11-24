<template>
  <v-tooltip
    v-if="!!asset"
    top
    :disabled="asset.length <= assetPadding"
    open-delay="400"
  >
    <template #activator="{ on, attrs }">
      <span v-bind="attrs" :style="assetStyle" v-on="on">
        {{ asset }}
      </span>
    </template>
    <span>
      {{ asset }}
    </span>
  </v-tooltip>

  <span v-else :style="assetStyle">
    {{ displayAsset }}
  </span>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { Currency } from '@/types/currency';

export default defineComponent({
  name: 'AmountCurrency',
  props: {
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
  },

  setup(props) {
    const { assetPadding, showCurrency, currency } = toRefs(props);
    const assetStyle = computed(() => {
      if (!assetPadding.value) {
        return {};
      }
      return {
        width: `${assetPadding.value + 1}ch`,
        'text-align': 'start'
      };
    });

    const displayAsset = computed(() => {
      const show = showCurrency.value;
      const value = currency.value;
      if (show === 'ticker') {
        return value.tickerSymbol;
      } else if (show === 'symbol') {
        return value.unicodeSymbol;
      } else if (show === 'name') {
        return value.name;
      }

      return '';
    });

    return {
      assetStyle,
      displayAsset
    };
  }
});
</script>
