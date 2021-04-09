import { Component, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import { TokenDetails } from '@/services/defi/types';
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

  getSymbol(details: TokenDetails): string {
    return this.assetSymbol(details);
  }

  getIdentifier(details: TokenDetails): string {
    if (typeof details === 'string') {
      return details;
    }
    return `_ceth_${details.ethereumAddress}`;
  }

  getTokenAddress(details: TokenDetails): string {
    if (typeof details === 'string') {
      return this.assetInfo(details)?.ethereumAddress ?? '';
    }
    return details.ethereumAddress;
  }

  getAssetName(identifier: string): string {
    const asset = this.assetInfo(identifier);
    return asset ? (asset.name ? asset.name : '') : '';
  }
}
