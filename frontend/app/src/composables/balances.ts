import { AssetBalance, AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { computed, Ref } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { tradeLocations } from '@/components/history/consts';
import { Routes } from '@/router/routes';
import { ManualBalance } from '@/services/balances/types';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval } from '@/store/assets';
import {
  AddAccountsPayload,
  AllBalancePayload,
  AssetBreakdown,
  AssetPrices,
  BalanceByLocation,
  BasicBlockchainAccountPayload,
  BlockchainAccountPayload,
  BlockchainAccountWithBalance,
  BlockchainBalancePayload,
  BlockchainTotal,
  ExchangeBalancePayload,
  ExchangeRateGetter,
  ExchangeSetupPayload,
  FetchPricePayload,
  HistoricPricePayload,
  LocationBalance,
  NonFungibleBalance,
  OracleCachePayload,
  XpubPayload
} from '@/store/balances/types';
import { ActionStatus } from '@/store/types';
import { useStore } from '@/store/utils';
import { Eth2Validator } from '@/types/balances';
import { Exchange, ExchangeInfo } from '@/types/exchanges';
import { PriceOracle } from '@/types/user';
import { assert } from '@/utils/assertions';

export const setupExchangeRateGetter = () => {
  const store = useStore();
  return store.getters['balances/exchangeRate'] as ExchangeRateGetter;
};

export const setupGeneralBalances = () => {
  const store = useStore();

  const aggregatedBalances = computed<AssetBalanceWithPrice[]>(() => {
    return store.getters['balances/aggregatedBalances'];
  });

  const balancesByLocation = computed<BalanceByLocation>(() => {
    return store.getters['balances/byLocation'];
  });

  const manualBalanceByLocation = computed<LocationBalance[]>(() => {
    return store.getters['balances/manualBalanceByLocation'];
  });

  const liabilities = computed<AssetBalance[]>(() => {
    return store.getters['balances/liabilities'];
  });

  const blockchainTotals = computed<BlockchainTotal[]>(() => {
    return store.getters['balances/blockchainTotals'];
  });

  const hasDetails = (account: string) =>
    computed<boolean>(() => {
      return store.getters['balances/hasDetails'](account);
    });

  const accountAssets = (account: string) =>
    computed<AssetBalance[]>(() => {
      return store.getters['balances/accountAssets'](account);
    });

  const accountLiabilities = (account: string) =>
    computed<AssetBalance[]>(() => {
      return store.getters['balances/accountLiabilities'](account);
    });

  const loopringBalances = (account: string) =>
    computed<AssetBalance[]>(() => {
      return store.getters['balances/loopringBalances'](account);
    });

  const assetBreakdown = (asset: string) =>
    computed<AssetBreakdown[]>(() => {
      return store.getters['balances/assetBreakdown'](asset);
    });

  const fetchBalances: (
    payload: Partial<AllBalancePayload>
  ) => Promise<void> = async payload => {
    return await store.dispatch('balances/fetchBalances', payload);
  };

  const fetchBlockchainBalances: (
    payload: BlockchainBalancePayload
  ) => Promise<void> = async payload => {
    return await store.dispatch('balances/fetchBlockchainBalances', payload);
  };

  const fetchLoopringBalances: (
    refresh: boolean
  ) => Promise<void> = async refresh => {
    return await store.dispatch('balances/fetchLoopringBalances', refresh);
  };

  const fetchManualBalances: () => Promise<void> = async () => {
    return await store.dispatch('balances/fetchManualBalances');
  };

  const fetchHistoricPrice: (
    payload: HistoricPricePayload
  ) => Promise<BigNumber> = async payload => {
    return await store.dispatch('balances/fetchHistoricPrice', payload);
  };

  const refreshPrices: (
    payload: FetchPricePayload
  ) => Promise<void> = async payload => {
    return await store.dispatch('balances/refreshPrices', payload);
  };

  const isEthereumToken = (asset: string) => {
    return computed<boolean>(() =>
      store.getters['balances/isEthereumToken'](asset)
    );
  };

  const fetchTokenDetails = async (address: string) => {
    return await store.dispatch('balances/fetchTokenDetails', address);
  };

  const exchangeRate = (currency: string) =>
    computed<BigNumber>(() => store.getters['balances/exchangeRate'](currency));

  const nfBalances = computed<NonFungibleBalance[]>(() => {
    return store.getters['balances/nfBalances'];
  });

  const nfTotalValue = (includeLPToken: boolean = false) =>
    computed<BigNumber>(() => {
      return store.getters['balances/nfTotalValue'](includeLPToken);
    });

  return {
    aggregatedBalances,
    balancesByLocation,
    manualBalanceByLocation,
    liabilities,
    blockchainTotals,
    nfBalances,
    nfTotalValue,
    hasDetails,
    accountAssets,
    accountLiabilities,
    loopringBalances,
    assetBreakdown,
    fetchBalances,
    isEthereumToken,
    fetchTokenDetails,
    fetchBlockchainBalances,
    fetchLoopringBalances,
    fetchManualBalances,
    fetchHistoricPrice,
    refreshPrices,
    exchangeRate
  };
};

export type BlockchainData = {
  btcAccounts: Ref<BlockchainAccountWithBalance[]>;
  bchAccounts: Ref<BlockchainAccountWithBalance[]>;
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
  const bchAccounts = computed<BlockchainAccountWithBalance[]>(
    () => store.getters['balances/bchAccounts']
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
    bchAccounts,
    blockchainAssets,
    kusamaBalances,
    polkadotBalances,
    avaxAccounts,
    loopringAccounts
  };
};

export const setupLocationInfo = () => {
  const isSupportedBlockchain = (identifier: string): boolean => {
    return Object.values(Blockchain).includes(identifier as any);
  };

  const getLocation = (identifier: string) => {
    const { assetName } = useAssetInfoRetrieval();

    if (isSupportedBlockchain(identifier)) {
      return {
        name: get(assetName(identifier)),
        identifier: identifier,
        exchange: false,
        imageIcon: true,
        icon: `${api.serverUrl}/api/1/assets/${identifier}/icon`,
        detailPath: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.route}#blockchain-balances-${identifier}`
      };
    }

    const locationFound = tradeLocations.find(
      location => location.identifier === identifier
    );
    assert(!!locationFound, 'location should not be falsy');
    return locationFound;
  };

  return {
    getLocation
  };
};

export const setupManualBalances = () => {
  const store = useStore();
  const fetchManualBalances = async () => {
    await store.dispatch('balances/fetchManualBalances');
  };

  const deleteManualBalance = async (id: number) => {
    await store.dispatch('balances/deleteManualBalance', id);
  };

  const manualBalances = computed(() => store.state.balances!.manualBalances);
  const manualLiabilities = computed(
    () => store.state.balances!.manualLiabilities
  );

  const editBalance: (
    balance: ManualBalance
  ) => Promise<ActionStatus> = async balance => {
    return await store.dispatch('balances/editManualBalance', balance);
  };

  const addBalance: (
    balance: Omit<ManualBalance, 'id'>
  ) => Promise<ActionStatus> = async balance => {
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
  const store = useStore();

  const account = (address: string) =>
    computed<GeneralAccount | undefined>(() =>
      store.getters['balances/account'](address)
    );

  const eth2Account = (address: string) =>
    computed<GeneralAccount | undefined>(() =>
      store.getters['balances/eth2Account'](address)
    );

  const accounts = computed<GeneralAccount[]>(
    () => store.getters['balances/accounts']
  );

  const addAccount = async (payload: BlockchainAccountPayload) => {
    return await store.dispatch('balances/addAccount', payload);
  };

  const removeAccount = async (payload: BasicBlockchainAccountPayload) => {
    return await store.dispatch('balances/removeAccount', payload);
  };

  const editAccount = async (payload: BlockchainAccountPayload) => {
    return await store.dispatch('balances/editAccount', payload);
  };

  const addAccounts = async (payload: AddAccountsPayload) => {
    return await store.dispatch('balances/addAccounts', payload);
  };

  const eth2Validators = computed(
    () => store.state.balances?.eth2Validators.entries
  );

  const addEth2Validator = async (payload: Eth2Validator) => {
    return await store.dispatch('balances/addEth2Validator', payload);
  };

  const editEth2Validator = async (payload: Eth2Validator) => {
    return await store.dispatch('balances/editEth2Validator', payload);
  };

  const deleteEth2Validators = async (payload: string[]) => {
    return await store.dispatch('balances/deleteEth2Validators', payload);
  };

  const deleteXpub = async (payload: XpubPayload) => {
    return await store.dispatch('balances/deleteXpub', payload);
  };

  return {
    account,
    eth2Account,
    accounts,
    addAccount,
    editAccount,
    addAccounts,
    eth2Validators,
    removeAccount,
    addEth2Validator,
    editEth2Validator,
    deleteEth2Validators,
    deleteXpub
  };
};

export const usePrices = () => {
  const store = useStore();

  const prices = computed<AssetPrices>(() => {
    const balances = store.state.balances;
    return balances!!.prices;
  });

  const createOracleCache = async (payload: OracleCachePayload) => {
    return await store.dispatch('balances/createOracleCache', payload);
  };

  const getPriceCache = async (source: PriceOracle) => {
    return await api.balances.getPriceCache(source);
  };

  const deletePriceCache = async (
    source: PriceOracle,
    fromAsset: string,
    toAsset: string
  ) => {
    return await api.balances.deletePriceCache(source, fromAsset, toAsset);
  };

  return {
    prices,
    createOracleCache,
    getPriceCache,
    deletePriceCache
  };
};

export const setupExchanges = () => {
  const store = useStore();

  const exchanges = computed<ExchangeInfo[]>(() => {
    return store.getters['balances/exchanges'];
  });

  const connectedExchanges = computed<Exchange[]>(() => {
    return store.state.balances!!.connectedExchanges;
  });

  const exchangeBalances = (exchange: string) =>
    computed<AssetBalanceWithPrice[]>(() =>
      store.getters['balances/exchangeBalances'](exchange)
    );

  const fetchExchangeBalances: (
    payload: ExchangeBalancePayload
  ) => Promise<void> = async payload => {
    return await store.dispatch('balances/fetchExchangeBalances', payload);
  };

  const fetchConnectedExchangeBalances = async (refresh: boolean = false) => {
    return await store.dispatch(
      'balances/fetchConnectedExchangeBalances',
      refresh
    );
  };

  const setupExchange = async (payload: ExchangeSetupPayload) => {
    return await store.dispatch('balances/setupExchange', payload);
  };

  const removeExchange = async (exchange: Exchange) => {
    return await store.dispatch('balances/removeExchange', exchange);
  };

  return {
    exchanges,
    exchangeBalances,
    connectedExchanges,
    fetchExchangeBalances,
    fetchConnectedExchangeBalances,
    setupExchange,
    removeExchange
  };
};
