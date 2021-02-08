<template>
  <v-container>
    <v-row align="center" class="mt-12">
      <v-col cols="auto">
        <crypto-icon :symbol="identifier" size="48px" />
      </v-col>
      <v-col class="d-flex flex-column">
        <span class="text-h5 font-weight-medium">{{ identifier }}</span>
        <span class="subtitle-2 text--secondary">
          {{ assetName }}
        </span>
      </v-col>
    </v-row>
    <asset-value-row class="mt-8" :identifier="identifier" />
    <asset-amount-and-value-over-time
      v-if="premium"
      class="mt-8"
      :service="$api"
      :asset="identifier"
    />
    <asset-locations class="mt-8" :identifier="identifier" />
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins, Prop } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import AssetLocations from '@/components/assets/AssetLocations.vue';
import AssetValueRow from '@/components/assets/AssetValueRow.vue';
import PremiumMixin from '@/mixins/premium-mixin';
import { SupportedAsset } from '@/services/types-model';
import { AssetAmountAndValueOverTime } from '@/utils/premium';

@Component({
  components: { AssetLocations, AssetValueRow, AssetAmountAndValueOverTime },
  computed: {
    ...mapGetters('balances', ['assetInfo'])
  }
})
export default class Assets extends Mixins(PremiumMixin) {
  @Prop({ required: true, type: String })
  identifier!: string;

  assetInfo!: (asset: string) => SupportedAsset | undefined;

  get assetName(): string {
    const asset = this.assetInfo(this.identifier);
    return asset ? asset.name : '';
  }
}
</script>
