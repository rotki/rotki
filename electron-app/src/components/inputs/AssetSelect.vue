<template>
  <v-autocomplete
    :value="value"
    :disabled="disabled"
    :items="supportedAssets"
    class="asset-select"
    single-line
    label="Asset"
    :rules="rules"
    item-text="symbol"
    :menu-props="{ closeOnClick: true, closeOnContentClick: true }"
    item-value="symbol"
    @input="input"
  >
    <template #selection="{ item }">
      <span>{{ item.symbol }}</span>
    </template>
    <template #item="{ item }">
      <v-list-item-avatar>
        <crypto-icon :symbol="item.symbol"></crypto-icon>
      </v-list-item-avatar>
      <v-list-item-content>
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
import { SupportedAsset } from '@/services/types-common';

const { mapState } = createNamespacedHelpers('balances');

@Component({
  components: { CryptoIcon },
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
  input(_value: string[]) {}
}
</script>

<style scoped lang="scss">
.asset-select {
  &__selection {
    display: flex;
    flex-direction: row;
    margin-right: 8px;

    &__details {
      display: flex;
      flex-direction: column;
    }
  }
}
</style>
