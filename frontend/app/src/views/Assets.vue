<template>
  <v-container>
    <v-row align="center" class="mt-12">
      <v-col cols="auto">
        <asset-icon :identifier="icon" size="48px" :symbol="symbol" />
      </v-col>
      <v-col class="d-flex flex-column">
        <span class="text-h5 font-weight-medium">{{ symbol }}</span>
        <span class="text-subtitle-2 text--secondary">
          {{ assetName }}
        </span>
      </v-col>
    </v-row>
    <asset-value-row class="mt-8" :identifier="identifier" :symbol="symbol" />
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
import { AssetAmountAndValueOverTime } from '@/premium/premium';
import { AssetInfoGetter } from '@/store/balances/types';

@Component({
  components: { AssetLocations, AssetValueRow, AssetAmountAndValueOverTime },
  computed: {
    ...mapGetters('balances', ['assetInfo'])
  }
})
export default class Assets extends Mixins(PremiumMixin) {
  @Prop({ required: true, type: String })
  identifier!: string;

  assetInfo!: AssetInfoGetter;

  get assetName(): string {
    const asset = this.assetInfo(this.identifier);
    return asset ? (asset.name ? asset.name : '') : '';
  }

  get icon(): string {
    return this.identifier;
  }

  get symbol(): string {
    const asset = this.assetInfo(this.identifier);
    return asset
      ? asset.symbol
        ? asset.symbol
        : this.identifier
      : this.identifier;
  }
}
</script>
