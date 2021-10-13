import {
  AssetInfoGetter,
  AssetSymbolGetter,
  ExchangeRateGetter
} from '@/store/balances/types';
import { useStore } from '@/store/utils';

export const setupExchangeRateGetter = () => {
  const store = useStore();
  return store.getters['balances/exchangeRate'] as ExchangeRateGetter;
};

export const setupAssetInfoRetrieval = () => {
  const store = useStore();
  const getAssetInfo: AssetInfoGetter = store.getters['balances/assetInfo'];
  const getAssetSymbol: AssetSymbolGetter =
    store.getters['balances/assetSymbol'];
  const getAssetName = (identifier: string) => {
    const asset = getAssetInfo(identifier);
    return asset ? (asset.name ? asset.name : '') : '';
  };
  return {
    getAssetInfo,
    getAssetSymbol,
    getAssetName
  };
};
