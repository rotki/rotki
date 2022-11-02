<template>
  <div
    class="d-flex flex-row balance-display shrink pt-1 pb-1 align-center"
    :class="{
      'justify-end': !noJustify,
      [$style.gain]: mode === 'gain',
      [$style.loss]: mode === 'loss'
    }"
  >
    <div :class="`d-flex flex-column align-${align}`">
      <amount-display
        :loading="priceLoading"
        :asset="asset"
        :asset-padding="assetPadding"
        :value="value.amount"
        class="d-block font-weight-medium"
      />
      <amount-display
        fiat-currency="USD"
        :asset-padding="assetPadding"
        :value="value.usdValue"
        :show-currency="ticker ? 'ticker' : 'none'"
        :loading="priceLoading"
        class="d-block grey--text"
      />
    </div>
    <asset-link v-if="!noIcon" class="ml-4" icon :asset="asset">
      <asset-icon :identifier="asset" size="24px" />
    </asset-link>
  </div>
</template>

<script setup lang="ts">
import { Balance } from '@rotki/common';
import { PropType } from 'vue';
import AssetLink from '@/components/assets/AssetLink.vue';

const props = defineProps({
  asset: { required: true, type: String },
  value: {
    required: false,
    type: Object as PropType<Balance>,
    default: null
  },
  noIcon: { required: false, type: Boolean, default: false },
  noJustify: { required: false, type: Boolean, default: false },
  align: { required: false, type: String, default: 'end' },
  mode: {
    required: false,
    type: String as PropType<'gain' | 'loss' | ''>,
    default: ''
  },
  assetPadding: { required: false, type: Number, default: 0 },
  ticker: { required: false, type: Boolean, default: true },
  priceLoading: { required: false, type: Boolean, default: false }
});

const { asset } = toRefs(props);
</script>

<style module lang="scss">
.balance-display {
  line-height: 1.5em;
}

.gain {
  color: #4caf50 !important;
}

.loss {
  color: #d32f2f !important;
}
</style>
