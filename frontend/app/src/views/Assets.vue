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
import AssetLocations from '@/components/assets/AssetLocations.vue';
import AssetValueRow from '@/components/assets/AssetValueRow.vue';
import AssetMixin from '@/mixins/asset-mixin';
import PremiumMixin from '@/mixins/premium-mixin';
import { AssetAmountAndValueOverTime } from '@/premium/premium';

@Component({
  components: { AssetLocations, AssetValueRow, AssetAmountAndValueOverTime }
})
export default class Assets extends Mixins(PremiumMixin, AssetMixin) {
  @Prop({ required: true, type: String })
  identifier!: string;

  get assetName(): string {
    return this.getAssetName(this.identifier);
  }

  get icon(): string {
    return this.identifier;
  }

  get symbol(): string {
    return this.getSymbol(this.identifier);
  }
}
</script>
