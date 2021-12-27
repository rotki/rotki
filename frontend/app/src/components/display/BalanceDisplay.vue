<template>
  <div
    class="d-flex flex-row balance_display shrink pt-1 pb-1 align-center"
    :class="{
      'justify-end': !noJustify,
      [$style.gain]: mode === 'gain',
      [$style.loss]: mode === 'loss'
    }"
  >
    <asset-link v-if="!noIcon" icon :asset="asset">
      <asset-icon
        :identifier="asset"
        :symbol="getSymbol(asset)"
        size="24px"
        class="mr-1"
      />
    </asset-link>
    <div
      class="ml-1 d-flex flex-column align-end"
      :style="{ 'min-width': `${minWidth}ch` }"
    >
      <amount-display
        :loading-="!!!value"
        :asset="getSymbol(asset)"
        :asset-padding="assetPadding"
        :value="value.amount"
        class="d-block font-weight-medium"
      />
      <amount-display
        :loading-="!!!value"
        fiat-currency="USD"
        :asset-padding="assetPadding"
        :value="value.usdValue"
        class="d-block grey--text"
      />
    </div>
  </div>
</template>

<script lang="ts">
import { Balance } from '@rotki/common';
import { defineComponent, PropType } from '@vue/composition-api';
import AssetLink from '@/components/assets/AssetLink.vue';
import AssetMixin from '@/mixins/asset-mixin';

export default defineComponent({
  name: 'BalanceDisplay',
  components: { AssetLink },
  mixins: [AssetMixin],
  props: {
    asset: { required: true, type: String },
    value: {
      required: false,
      type: Object as PropType<Balance>,
      default: null
    },
    noIcon: { required: false, type: Boolean, default: false },
    minWidth: { required: false, type: Number, default: 16 },
    noJustify: { required: false, type: Boolean, default: false },
    mode: {
      required: false,
      type: String as PropType<'gain' | 'loss' | ''>,
      default: ''
    },
    assetPadding: { required: false, type: Number, default: 5 }
  }
});
</script>

<style module lang="scss">
.gain {
  color: #4caf50 !important;
}

.loss {
  color: #d32f2f !important;
}
</style>
