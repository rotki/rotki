import { AssetBalanceWithPrice } from '@rotki/common';
import { computed, Ref } from '@vue/composition-api';
import { ManualBalance } from '@/services/balances/types';
import {
  AssetInfoGetter,
  AssetSymbolGetter,
  BlockchainAccountWithBalance,
  ExchangeRateGetter
} from '@/store/balances/types';
import { ActionStatus } from '@/store/types';
import { useStore } from '@/store/utils';

export const setupExchangeRateGetter = () => {
  const store = useStore();
  return store.getters['balances/exchangeRate'] as ExchangeRateGetter;
};

export type BlockchainData = {
  btcAccounts: Ref<BlockchainAccountWithBalance[]>;
  polkadotBalances: Ref<BlockchainAccountWithBalance[]>;
  blockchainAssets: Ref<AssetBalanceWithPrice[]>;
  ethAccounts: Ref<BlockchainAccountWithBalance[]>;
  avaxAccounts: Ref<BlockchainAccountWithBalance[]>;
  kusamaBalances: Ref<BlockchainAccountWithBalance[]>;
};

export const setupBlockchainData = (): BlockchainData => {
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

export const setupManualBalances = () => {
  const store = useStore();
  const fetchManualBalances = async () => {
    await store.dispatch('balances/fetchManualBalances');
  };

  const deleteManualBalance = async (label: string) => {
    await store.dispatch('balances/deleteManualBalance', label);
  };

  const manualBalances = computed(() => store.state.balances!.manualBalances);
  const manualLiabilities = computed(
    () => store.state.balances!.manualLiabilities
  );

  const editBalance: (balance: ManualBalance) => Promise<ActionStatus> =
    async balance => {
      return await store.dispatch('balances/editManualBalance', balance);
    };

  const addBalance: (balance: ManualBalance) => Promise<ActionStatus> =
    async balance => {
      return await store.dispatch('balances/addManualBalance', balance);
    };

  const manualLabels = computed<string[]>(() => {
    return store.getters['balances/manualLabels'];
  });

  return {
    editBalance,
    addBalance,
    fetchManualBalances,
    deleteManualBalance,
    manualLabels,
    manualBalances,
    manualLiabilities
  };
};
