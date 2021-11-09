<template>
  <div class="pa-1" :class="$style.asset">
    <asset-icon
      :class="$style.icon"
      :identifier="getTokenIdentifier(assets[0])"
      :symbol="getTokenSymbol(assets[0])"
      size="22px"
    />
    <asset-icon
      :class="[$style.icon, $style.bottom]"
      :identifier="getTokenIdentifier(assets[1])"
      :symbol="getTokenSymbol(assets[1])"
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
import AssetMixin from '@/mixins/asset-mixin';

export default defineComponent({
  name: 'BalancerPoolAsset',
  mixins: [AssetMixin],
  props: {
    assets: {
      required: true,
      type: Array as PropType<BalancerUnderlyingToken[] | string[]>,
      validator: value => Array.isArray(value) && value.length >= 2
    }
  },
  methods: {
    getTokenIdentifier(token: BalancerUnderlyingToken | string): string {
      if (typeof token === 'string') {
        return token;
      }
      return token.token;
    },

    getTokenSymbol(token: BalancerUnderlyingToken | string): string {
      const identifier = typeof token === 'string' ? token : token.token;
      return (this as unknown as AssetMixin).getSymbol(identifier);
    }
  }
});
</script>

<style module lang="scss">
.asset {
  height: 48px;
  width: 48px;
  border-radius: 50%;
  background: url(~@/assets/images/defi/balancer.svg) no-repeat 8px 32px;
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
