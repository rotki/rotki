<template>
  <div class="balancer-pool-asset d-flex flex-column pa-1">
    <asset-icon
      :identifier="getTokenIdentifier(assets[0])"
      :symbol="getTokenSymbol(assets[0])"
      size="22px"
    />
    <asset-icon
      :identifier="getTokenIdentifier(assets[1])"
      :symbol="getTokenSymbol(assets[1])"
      size="22px"
      class="align-self-end"
    />
  </div>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import AssetMixin from '@/mixins/asset-mixin';
import { BalancerUnderlyingToken } from '@/store/defi/types';

@Component({})
export default class BalancerPoolAsset extends Mixins(AssetMixin) {
  @Prop({ required: true, type: Array, validator: value => value.length >= 2 })
  assets!: BalancerUnderlyingToken[] | string[];

  getTokenIdentifier(token: BalancerUnderlyingToken | string): string {
    if (typeof token === 'string') {
      return token;
    }
    return token.token;
  }

  getTokenSymbol(token: BalancerUnderlyingToken | string): string {
    if (typeof token === 'string') {
      return token;
    }

    return this.getSymbol(token.token);
  }
}
</script>

<style scoped lang="scss">
.balancer-pool-asset {
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
</style>
