import { AssetBalanceWithPrice } from '@rotki/common';
import { GeneralAccount } from '@rotki/common/lib/account';
import { SupportedAsset } from '@rotki/common/lib/data';
import { computed, Ref } from '@vue/composition-api';
import { ManualBalance } from '@/services/balances/types';
import {
  AddAccountsPayload,
  AssetInfoGetter,
  AssetSymbolGetter,
  BlockchainAccountPayload,
  BlockchainAccountWithBalance,
  ExchangeRateGetter,
  IdentifierForSymbolGetter
} from '@/store/balances/types';
import { ActionStatus } from '@/store/types';
import { useStore } from '@/store/utils';
import { Eth2Validator } from '@/types/balances';

export const setupExchangeRateGetter = () => {
  const store = useStore();
  return store.getters['balances/exchangeRate'] as ExchangeRateGetter;
};

export const setupSupportedAssets = () => {
  const store = useStore();
  const supportedAssets = computed<SupportedAsset[]>(() => {
    return store.state.balances!.supportedAssets;
  });

  return { supportedAssets };
};

export type BlockchainData = {
  btcAccounts: Ref<BlockchainAccountWithBalance[]>;
  polkadotBalances: Ref<BlockchainAccountWithBalance[]>;
  blockchainAssets: Ref<AssetBalanceWithPrice[]>;
  ethAccounts: Ref<BlockchainAccountWithBalance[]>;
  eth2Balances: Ref<BlockchainAccountWithBalance[]>;
  avaxAccounts: Ref<BlockchainAccountWithBalance[]>;
  kusamaBalances: Ref<BlockchainAccountWithBalance[]>;
  loopringAccounts: Ref<BlockchainAccountWithBalance[]>;
};

export const setupBlockchainData = (): BlockchainData => {
  const store = useStore();

  const ethAccounts = computed<BlockchainAccountWithBalance[]>(
    () => store.getters['balances/ethAccounts']
  );
  const eth2Balances = computed<BlockchainAccountWithBalance[]>(
    () => store.getters['balances/eth2Balances']
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
  const loopringAccounts = computed<BlockchainAccountWithBalance[]>(
    () => store.getters['balances/loopringAccounts']
  );

  return {
    ethAccounts,
    eth2Balances,
    btcAccounts,
    blockchainAssets,
    kusamaBalances,
    polkadotBalances,
    avaxAccounts,
    loopringAccounts
  };
};

export const setupAssetInfoRetrieval = () => {
  const store = useStore();
  const getAssetInfo: AssetInfoGetter = store.getters['balances/assetInfo'];
  const getAssetSymbol: AssetSymbolGetter =
    store.getters['balances/assetSymbol'];
  const getAssetIdentifierForSymbol: IdentifierForSymbolGetter =
    store.getters['balances/getIdentifierForSymbol'];
  const getAssetName = (identifier: string) => {
    const asset = getAssetInfo(identifier);
    return asset ? (asset.name ? asset.name : '') : '';
  };
  const getTokenAddress = (identifier: string) => {
    return getAssetInfo(identifier)?.ethereumAddress ?? '';
  };
  return {
    getAssetInfo,
    getAssetIdentifierForSymbol,
    getAssetSymbol,
    getAssetName,
    getTokenAddress
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

export const setupBlockchainAccounts = () => {
  const { dispatch, getters, state } = useStore();
  const account = (address: string) =>
    computed<GeneralAccount | undefined>(() =>
      getters['balances/account'](address)
    );
  const accounts = computed<GeneralAccount[]>(
    () => getters['balances/accounts']
  );
  const addAccount = async (payload: BlockchainAccountPayload) => {
    return await dispatch('balances/addAccount', payload);
  };
  const editAccount = async (payload: BlockchainAccountPayload) => {
    return await dispatch('balances/editAccount', payload);
  };
  const addAccounts = async (payload: AddAccountsPayload) => {
    return await dispatch('balances/addAccounts', payload);
  };

  const addEth2Validator = async (payload: Eth2Validator) => {
    return await dispatch('balances/addEth2Validator', payload);
  };

  const editEth2Validator = async (payload: Eth2Validator) => {
    return await dispatch('balances/editEth2Validator', payload);
  };

  const eth2Validators = computed(() => state.balances?.eth2Validators.entries);

  return {
    account,
    accounts,
    addAccount,
    editAccount,
    addAccounts,
    addEth2Validator,
    editEth2Validator,
    eth2Validators
  };
};
