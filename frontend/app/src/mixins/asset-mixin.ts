import { Ref } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { mapActions } from 'pinia';
import { Component, Vue } from 'vue-property-decorator';
import { useAssetInfoRetrieval } from '@/store/assets';

@Component({
  methods: {
    ...mapActions(useAssetInfoRetrieval, [
      'assetName',
      'assetSymbol',
      'tokenAddress'
    ])
  }
})
export default class AssetMixin extends Vue {
  assetName!: (identifier: string) => Ref<string>;
  assetSymbol!: (identifier: string) => Ref<string>;
  tokenAddress!: (identifier: string) => Ref<string>;

  getSymbol(identifier: string): string {
    return get(this.assetSymbol(identifier));
  }

  getTokenAddress(identifier: string): string {
    return get(this.tokenAddress(identifier));
  }

  getAssetName(identifier: string): string {
    return get(this.assetName(identifier));
  }
}
