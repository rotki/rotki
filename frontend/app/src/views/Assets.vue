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
    <asset-value-row :identifier="identifier" />
  </v-container>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import AssetLocations from '@/components/assets/AssetLocations.vue';
import AssetValueRow from '@/components/assets/AssetValueRow.vue';
import { SupportedAsset } from '@/services/types-model';

@Component({
  components: { AssetLocations, AssetValueRow },
  computed: {
    ...mapGetters('balances', ['assetInfo'])
  }
})
export default class Assets extends Vue {
  @Prop({ required: true, type: String })
  identifier!: string;

  assetInfo!: (asset: string) => SupportedAsset | undefined;

  get assetName(): string {
    const asset = this.assetInfo(this.identifier);
    return asset ? asset.name : '';
  }
}
</script>
