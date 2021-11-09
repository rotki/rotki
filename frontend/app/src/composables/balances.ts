import { AssetBalanceWithPrice } from '@rotki/common';
import { computed } from '@vue/composition-api';
import {
  AssetInfoGetter,
  AssetSymbolGetter,
  BlockchainAccountWithBalance,
  ExchangeRateGetter
} from '@/store/balances/types';
import { useStore } from '@/store/utils';

export const setupExchangeRateGetter = () => {
  const store = useStore();
  return store.getters['balances/exchangeRate'] as ExchangeRateGetter;
};

export const setupBlockchainData = () => {
  const store = useStore();

  const ethAccounts = computed<BlockchainAccountWithBalance[]>(
    () => store.getters['balances/ethAccounts']
  );
  const btcAccounts = computed<BlockchainAccountWithBalance[]>(
    () => store.getters['balances/btcAccounts']
  );
  const blockchainAssets = computed<AssetBalanceWithPrice[]>(
    () => store.getters['balances/blockchainAssets']
  );
  const kusamaBalances = computed<BlockchainAccountWithBalance[]>(
    () => store.getters['balances/kusamaBalances']
  );
  const polkadotBalances = computed<BlockchainAccountWithBalance[]>(
    () => store.getters['balances/polkadotBalances']
  );
  const avaxAccounts = computed<BlockchainAccountWithBalance[]>(
    () => store.getters['balances/avaxAccounts']
  );
  return {
    ethAccounts,
    btcAccounts,
    blockchainAssets,
    kusamaBalances,
    polkadotBalances,
    avaxAccounts
  };
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
