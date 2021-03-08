<template>
  <asset-details-base :asset="currentAsset" :opens-details="opensDetails" />
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import AssetDetailsBase from '@/components/helper/AssetDetailsBase.vue';

import { SupportedAsset } from '@/services/types-model';

@Component({
  components: { AssetDetailsBase, CryptoIcon },
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

  assetInfo!: (key: string) => SupportedAsset;

  get currentAsset() {
    const details = this.assetInfo(this.asset);
    return {
      symbol: details ? details.symbol : this.asset,
      name: details ? details.name : this.asset,
      identifier: details ? details.key : this.asset
    };
  }
}
</script>
