<template>
  <div
    class="d-flex flex-row balance-display shrink pt-1 pb-1 align-center"
    :class="{
      'justify-end': !noJustify,
      [$style.gain]: mode === 'gain',
      [$style.loss]: mode === 'loss'
    }"
  >
    <div class="d-flex flex-column align-end">
      <amount-display
        :loading-="!!!value"
        :asset="symbol"
        :asset-padding="assetPadding"
        :value="value.amount"
        class="d-block font-weight-medium"
      />
      <amount-display
        :loading-="!!!value"
        fiat-currency="USD"
        :asset-padding="assetPadding"
        :value="value.usdValue"
        :show-currency="ticker ? 'ticker' : 'none'"
        :loading="priceLoading"
        class="d-block grey--text"
      />
    </div>
    <asset-link v-if="!noIcon" class="ml-1" icon :asset="asset">
      <asset-icon :identifier="asset" size="24px" />
    </asset-link>
  </div>
</template>

<script lang="ts">
import { Balance } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import AssetLink from '@/components/assets/AssetLink.vue';
import { useAssetInfoRetrieval } from '@/store/assets';

export default defineComponent({
  name: 'BalanceDisplay',
  components: { AssetLink },
  props: {
    asset: { required: true, type: String },
    value: {
      required: false,
      type: Object as PropType<Balance>,
      default: null
    },
    noIcon: { required: false, type: Boolean, default: false },
    noJustify: { required: false, type: Boolean, default: false },
    mode: {
      required: false,
      type: String as PropType<'gain' | 'loss' | ''>,
      default: ''
    },
    assetPadding: { required: false, type: Number, default: 0 },
    ticker: { required: false, type: Boolean, default: true },
    priceLoading: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { asset } = toRefs(props);
    const { getAssetSymbol } = useAssetInfoRetrieval();
    const symbol = computed(() => {
      const identifier = get(asset);
      return identifier ? getAssetSymbol(identifier) : '';
    });
    return {
      symbol
    };
  }
});
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
