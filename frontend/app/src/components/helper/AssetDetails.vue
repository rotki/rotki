<template>
  <asset-details-base
    :hide-name="hideName"
    :asset="currentAsset"
    :opens-details="opensDetails"
  />
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import AssetMixin from '@/mixins/asset-mixin';

@Component({
  components: { AssetDetailsBase }
})
export default class AssetDetails extends Mixins(AssetMixin) {
  @Prop({
    required: true,
    validator(value: string): boolean {
      return !!value && value.length > 0;
    }
  })
  asset!: string;
  @Prop({ required: false, type: Boolean, default: false })
  opensDetails!: boolean;
  @Prop({ required: false, type: Boolean, default: false })
  hideName!: boolean;

  get currentAsset() {
    const details = this.assetInfo(this.asset);
    return {
      symbol: details ? details.symbol : this.asset,
      name: details ? details.name : this.asset,
      identifier: details ? details.identifier : this.asset
    };
  }
}
</script>
