<template>
  <asset-details-base
    :hide-name="hideName"
    :asset="currentAsset"
    :opens-details="opensDetails"
  />
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';
import { AssetInfoGetter } from '@/store/balances/types';

@Component({
  components: { AssetDetailsBase },
  computed: {
    ...mapGetters('balances', ['assetInfo'])
  }
})
export default class AssetDetails extends Vue {
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

  assetInfo!: AssetInfoGetter;

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
