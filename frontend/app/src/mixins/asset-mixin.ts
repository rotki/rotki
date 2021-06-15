import { Component, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import {
  AssetInfoGetter,
  AssetSymbolGetter,
  IdentifierForSymbolGetter
} from '@/store/balances/types';

@Component({
  computed: {
    ...mapGetters('balances', [
      'assetInfo',
      'getIdentifierForSymbol',
      'assetSymbol'
    ])
  }
})
export default class AssetMixin extends Vue {
  getIdentifierForSymbol!: IdentifierForSymbolGetter;
  assetInfo!: AssetInfoGetter;
  assetSymbol!: AssetSymbolGetter;

  getSymbol(identifier: string): string {
    return this.assetSymbol(identifier);
  }

  getTokenAddress(identifier: string): string {
    return this.assetInfo(identifier)?.ethereumAddress ?? '';
  }

  getAssetName(identifier: string): string {
    const asset = this.assetInfo(identifier);
    return asset ? (asset.name ? asset.name : '') : '';
  }
}
