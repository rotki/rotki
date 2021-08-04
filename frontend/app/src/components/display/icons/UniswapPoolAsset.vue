<template>
  <div
    class="pa-1"
    :class="{
      [$style.asset]: true,
      [$style.uniswap]: !sushi,
      [$style.sushiswap]: sushi
    }"
  >
    <asset-icon :class="$style.icon" :identifier="assets[0]" size="22px" />
    <asset-icon
      :class="[$style.icon, $style.bottom]"
      :identifier="assets[1]"
      size="22px"
      :styled="{
        'padding-left': '20px'
      }"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';

export default defineComponent({
  props: {
    assets: {
      required: true,
      type: Array as PropType<string[]>,
      validator: value => Array.isArray(value) && value.length === 2
    },
    sushi: {
      required: false,
      default: false,
      type: Boolean
    }
  }
});
</script>

<style module lang="scss">
.uniswap {
  background-image: url(~@/assets/images/defi/uniswap.svg);
}

.sushiswap {
  background-image: url(~@/assets/images/modules/sushiswap.svg);
}

.asset {
  height: 48px;
  width: 48px;
  background-repeat: no-repeat;
  background-position: 8px 32px;
  border-radius: 50%;
  background-size: 12px 12px;
}

.icon {
  width: 22px;
  height: 22px;
}

.bottom {
  margin-top: -4px;
  margin-left: -4px;
  padding-right: 20px;
}
</style>
