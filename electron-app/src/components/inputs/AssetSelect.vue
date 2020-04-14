<template>
  <v-autocomplete
    :value="value"
    :disabled="disabled"
    :items="supportedAssets"
    class="asset-select"
    single-line
    label="Asset"
    :rules="rules"
    item-value="key"
    :item-text="assetText"
    :menu-props="{ closeOnClick: true, closeOnContentClick: true }"
    @input="input"
  >
    <template #selection="{ item }">
      <asset-details
        class="asset-select__details"
        :asset="item.key"
      ></asset-details>
    </template>
    <template #item="{ item }">
      <v-list-item-avatar>
        <crypto-icon :symbol="item.symbol"></crypto-icon>
      </v-list-item-avatar>
      <v-list-item-content :id="`asset-${item.key.toLocaleLowerCase()}`">
        <v-list-item-title>{{ item.symbol }}</v-list-item-title>
        <v-list-item-subtitle>{{ item.name }}</v-list-item-subtitle>
      </v-list-item-content>
    </template>
  </v-autocomplete>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import { SupportedAsset } from '@/services/types-model';

const { mapState } = createNamespacedHelpers('balances');

@Component({
  components: { AssetDetails, CryptoIcon },
  computed: {
    ...mapState(['supportedAssets'])
  }
})
export default class AssetSelect extends Vue {
  supportedAssets!: SupportedAsset[];

  @Prop({ required: true, default: '' })
  value!: string;

  @Prop({ default: () => [], required: false })
  rules!: ((v: string) => boolean | string)[];

  @Prop({ default: false, required: false })
  disabled!: boolean;

  @Emit()
  input(_value: string) {}

  assetText(asset: SupportedAsset): string {
    return `${asset.symbol} ${asset.name}`;
  }
}
</script>

<style scoped lang="scss">
.asset-select {
  &__details {
    padding-top: 4px;
    padding-bottom: 4px;
  }
}
</style>
