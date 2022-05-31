<template>
  <div class="pa-1" :class="$style.asset">
    <asset-icon
      :class="$style.icon"
      :identifier="assets[0].token"
      size="22px"
    />
    <asset-icon
      :class="[$style.icon, $style.bottom]"
      :identifier="assets[1].token"
      size="22px"
      :styled="{
        'padding-left': '20px'
      }"
    />
  </div>
</template>

<script lang="ts">
import { BalancerUnderlyingToken } from '@rotki/common/lib/defi/balancer';
import { defineComponent, PropType } from '@vue/composition-api';

export default defineComponent({
  name: 'BalancerPoolAsset',
  props: {
    assets: {
      required: true,
      type: Array as PropType<BalancerUnderlyingToken[]>,
      validator: value => Array.isArray(value) && value.length >= 2
    }
  }
});
</script>

<style module lang="scss">
.asset {
  height: 48px;
  width: 48px;
  border-radius: 50%;
  background: url(/assets/images/defi/balancer.svg) no-repeat 8px 32px;
  background-size: 12px 12px;

  > * {
    width: 22px;
    height: 22px;

    &:nth-child(2) {
      margin-top: -4px;
      margin-left: -4px;
    }
  }
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
