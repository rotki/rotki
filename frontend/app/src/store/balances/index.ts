import {
  AssetBalance,
  AssetBalanceWithPrice,
  Balance,
  BigNumber
} from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Eth2Validators } from '@rotki/common/lib/staking/eth2';
import { computed, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { forEach } from 'lodash';
import { acceptHMRUpdate, defineStore, storeToRefs } from 'pinia';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import { bigNumberSum } from '@/filters';
import i18n from '@/i18n';
import {
  BlockchainAssetBalances,
  BtcBalances,
  ManualBalanceWithValue
} from '@/services/balances/types';
import { api } from '@/services/rotkehlchen-api';
import { BtcAccountData, GeneralAccountData } from '@/services/types-api';
import { useAssetInfoRetrieval, useIgnoredAssetsStore } from '@/store/assets';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useBalancePricesStore } from '@/store/balances/prices';
import {
  AccountAssetBalances,
  AllBalancePayload,
  AssetBreakdown,
  FetchPricePayload,
  LocationBalance,
  NonFungibleBalance,
  NonFungibleBalances
} from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { setStatus } from '@/store/utils';
import { Writeable } from '@/types';
import { Exchange, ExchangeData, ExchangeInfo } from '@/types/exchanges';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { ReadOnlyTag } from '@/types/user';
import { NoPrice, sortDesc, zeroBalance } from '@/utils/bignumbers';
import { assetSum, balanceSum } from '@/utils/calculation';
import { logger } from '@/utils/logging';

export const useBalancesStore = defineStore('balances', () => {
  const nonFungibleBalancesState = ref<NonFungibleBalances>({});

  const pricesStore = useBalancePricesStore();
  const { prices } = storeToRefs(pricesStore);
  const {
    updateBalancesPrices,
    fetchPrices,
    fetchExchangeRates,
    exchangeRate
  } = pricesStore;

  const manualBalancesStore = useManualBalancesStore();
  const { manualBalancesData, manualBalances, manualBalanceByLocation } =
    storeToRefs(manualBalancesStore);
  const { fetchManualBalances } = manualBalancesStore;

  const exchangeStore = useExchangeBalancesStore();
  const { exchanges, exchangeBalances, connectedExchanges } =
    storeToRefs(exchangeStore);
  const { getBalances: getExchangeBalances, setExchanges } = exchangeStore;

  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { isAssetIgnored } = useIgnoredAssetsStore();

  const { treatEth2AsEth, currencySymbol } = storeToRefs(
    useGeneralSettingsStore()
  );

  const blockchainAccountsStore = useBlockchainAccountsStore();
  const {
    ethAccountsState,
    ksmAccountsState,
    dotAccountsState,
    avaxAccountsState,
    btcAccountsState,
    bchAccountsState,
    eth2ValidatorsState
  } = storeToRefs(blockchainAccountsStore);
  const { fetchAccounts, reset: resetBlockchainAccountsStore } =
    blockchainAccountsStore;

  const blockchainBalancesStore = useBlockchainBalancesStore();

  const {
    adjustBlockchainPrices,
    fetchBlockchainBalances,
    fetchLoopringBalances,
    reset: resetBlockchainBalancesStore
  } = blockchainBalancesStore;

  const {
    ethBalancesState,
    ksmBalancesState,
    dotBalancesState,
    avaxBalancesState,
    btcBalancesState,
    bchBalancesState,
    eth2BalancesState,
    loopringBalancesState,
    totals,
    blockchainTotal
  } = storeToRefs(blockchainBalancesStore);

  const { awaitTask, addTask, isTaskRunning } = useTasks();
  const { notify } = useNotifications();

  const adjustPrices = async () => {
    adjustBlockchainPrices();

    const newManualBalancesData = get(manualBalancesData).map(item => {
      const assetPrice = get(prices)[item.asset];
      if (!assetPrice) {
        return item;
      }
      return {
        ...item,
        usdValue: item.amount.times(assetPrice)
      };
    });

    set(manualBalancesData, newManualBalancesData);

    const exchanges = { ...(get(exchangeBalances) as ExchangeData) };
    for (const exchange in exchanges) {
      exchanges[exchange] = updateBalancesPrices(exchanges[exchange]);
    }

    set(exchangeBalances, exchanges);
  };

  const refreshPrices = async (payload: FetchPricePayload) => {
    setStatus(Status.LOADING, Section.PRICES);
    await fetchExchangeRates();
    await fetchPrices(payload);
    await adjustPrices();
    setStatus(Status.LOADED, Section.PRICES);
  };

  const assetBreakdown = (asset: string) =>
    computed<AssetBreakdown[]>(() => {
      const breakdown: AssetBreakdown[] = [];

      const cexBalances = get(exchangeBalances) as ExchangeData;
      for (const exchange in cexBalances) {
        const exchangeData = cexBalances[exchange];
        if (!exchangeData[asset]) {
          continue;
        }

        breakdown.push({
          address: '',
          location: exchange,
          balance: exchangeData[asset],
          tags: []
        });
      }

      (get(manualBalances) as ManualBalanceWithValue[]).forEach(
        manualBalance => {
          if (manualBalance.asset !== asset) {
            return;
          }

          breakdown.push({
            address: '',
            location: manualBalance.location,
            balance: {
              amount: manualBalance.amount,
              usdValue: manualBalance.usdValue
            },
            tags: manualBalance.tags
          });
        }
      );

      const addBlockchainToBreakdown = (
        blockchain: Blockchain,
        balances: BlockchainAssetBalances,
        accounts: GeneralAccountData[]
      ) => {
        for (const address in balances) {
          const balance = balances[address];
          const assetBalance = balance.assets[asset];
          if (!assetBalance) {
            continue;
          }

          const tags =
            accounts.find(account => account.address === address)?.tags || [];

          breakdown.push({
            address,
            location: blockchain,
            balance: assetBalance,
            tags
          });
        }
      };

      const list = [
        {
          blockchain: Blockchain.ETH,
          balances: get(ethBalancesState) as BlockchainAssetBalances,
          accounts: get(ethAccountsState)
        },
        {
          blockchain: Blockchain.KSM,
          balances: get(ksmBalancesState) as BlockchainAssetBalances,
          accounts: get(ksmAccountsState)
        },
        {
          blockchain: Blockchain.DOT,
          balances: get(dotBalancesState) as BlockchainAssetBalances,
          accounts: get(dotAccountsState)
        },
        {
          blockchain: Blockchain.AVAX,
          balances: get(avaxBalancesState) as BlockchainAssetBalances,
          accounts: get(avaxAccountsState)
        }
      ];

      list.map(item =>
        addBlockchainToBreakdown(item.blockchain, item.balances, item.accounts)
      );

      const addBlockchainBtcToBreakdown = (
        blockchain: Blockchain,
        balances: BtcBalances,
        accounts: BtcAccountData
      ) => {
        const { standalone, xpubs } = balances;
        if (standalone) {
          for (const address in standalone) {
            const balance = standalone[address];
            const tags =
              accounts.standalone.find(account => account.address === address)
                ?.tags || [];

            breakdown.push({
              address,
              location: blockchain,
              balance,
              tags
            });
          }
        }

        if (xpubs) {
          for (let i = 0; i < xpubs.length; i++) {
            const xpub = xpubs[i];
            const addresses = xpub.addresses;
            const tags = accounts?.xpubs[i].tags;
            for (const address in addresses) {
              const balance = addresses[address];

              breakdown.push({
                address,
                location: blockchain,
                balance,
                tags
              });
            }
          }
        }
      };

      if (asset === Blockchain.BTC) {
        addBlockchainBtcToBreakdown(
          Blockchain.BTC,
          get(btcBalancesState) as BtcBalances,
          get(btcAccountsState)
        );
      }

      if (asset === Blockchain.BCH) {
        addBlockchainBtcToBreakdown(
          Blockchain.BCH,
          get(bchBalancesState) as BtcBalances,
          get(bchAccountsState)
        );
      }

      const loopringBalances = get(
        loopringBalancesState
      ) as AccountAssetBalances;
      for (const address in loopringBalances) {
        const existing: Writeable<AssetBreakdown> | undefined = breakdown.find(
          value => value.address === address
        );
        const balanceElement = loopringBalances[address][asset];
        if (!balanceElement) {
          continue;
        }
        if (existing) {
          existing.balance = balanceSum(existing.balance, balanceElement);
        } else {
          breakdown.push({
            address,
            location: Blockchain.ETH,
            balance: loopringBalances[address][asset],
            tags: [ReadOnlyTag.LOOPRING]
          });
        }
      }

      if (
        asset === Blockchain.ETH2 ||
        (get(treatEth2AsEth) && asset === Blockchain.ETH)
      ) {
        const validators = get(eth2ValidatorsState) as Eth2Validators;
        for (const { publicKey } of validators.entries) {
          const balances = get(eth2BalancesState) as BlockchainAssetBalances;
          const validatorBalances = balances[publicKey];
          let balance: Balance = zeroBalance();
          if (validatorBalances && validatorBalances.assets) {
            const assets = validatorBalances.assets;
            balance = {
              amount: assets[Blockchain.ETH2].amount,
              usdValue: assetSum(assets)
            };
          }

          breakdown.push({
            address: publicKey,
            location: Blockchain.ETH2,
            balance,
            tags: []
          });
        }
      }

      return breakdown.sort((a, b) =>
        sortDesc(a.balance.usdValue, b.balance.usdValue)
      );
    });

  const locationBreakdown = (identifier: string) =>
    computed<AssetBalanceWithPrice[]>(() => {
      const ownedAssets: Record<string, Balance> = {};

      const addToOwned = (value: AssetBalance) => {
        const associatedAsset: string = get(
          getAssociatedAssetIdentifier(value.asset)
        );

        const ownedAsset = ownedAssets[associatedAsset];

        ownedAssets[associatedAsset] = !ownedAsset
          ? {
              ...value
            }
          : {
              ...balanceSum(ownedAsset, value)
            };
      };

      const exchange = get(connectedExchanges).find(
        ({ location }) => identifier === location
      );

      if (exchange) {
        const balances = get(getExchangeBalances(exchange.location));
        balances.forEach((value: AssetBalance) => addToOwned(value));
      }

      if (identifier === TRADE_LOCATION_BLOCKCHAIN) {
        (get(totals) as AssetBalance[]).forEach((value: AssetBalance) =>
          addToOwned(value)
        );

        const loopringBalances = get(
          loopringBalancesState
        ) as AccountAssetBalances;
        for (const address in loopringBalances) {
          const accountBalances = loopringBalances[address];

          forEach(accountBalances, (balance: Balance, asset: string) => {
            addToOwned({ asset, ...balance });
          });
        }
      }

      (get(manualBalances) as ManualBalanceWithValue[]).forEach(value => {
        if (value.location === identifier) {
          addToOwned(value);
        }
      });

      return Object.keys(ownedAssets)
        .filter(asset => !get(isAssetIgnored(asset)))
        .map(asset => ({
          asset,
          amount: ownedAssets[asset].amount,
          usdValue: ownedAssets[asset].usdValue,
          usdPrice: (get(prices)[asset] as BigNumber) ?? NoPrice
        }))
        .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
    });

  const balancesByLocation = computed<Record<string, BigNumber>>(() => {
    const byLocations: Record<string, BigNumber> = {};

    const addToOwned = (location: string, value: BigNumber) => {
      const byLocation = byLocations[location];

      byLocations[location] = !byLocation ? value : value.plus(byLocation);
    };

    for (const { location, usdValue } of get(
      manualBalanceByLocation
    ) as LocationBalance[]) {
      addToOwned(location, usdValue);
    }

    const mainCurrency = get(currencySymbol);
    const total = get(blockchainTotal) as BigNumber;

    const currentExchangeRate = get(exchangeRate(mainCurrency)) as
      | BigNumber
      | undefined;
    const blockchainTotalConverted = currentExchangeRate
      ? total.multipliedBy(currentExchangeRate)
      : total;

    addToOwned(TRADE_LOCATION_BLOCKCHAIN, blockchainTotalConverted);

    for (const { location, total } of get(exchanges) as ExchangeInfo[]) {
      const exchangeBalanceConverted = currentExchangeRate
        ? total.multipliedBy(currentExchangeRate)
        : total;
      addToOwned(location, exchangeBalanceConverted);
    }

    return byLocations;
  });

  const fetchNfBalances = async (payload?: {
    ignoreCache: boolean;
  }): Promise<void> => {
    const { activeModules } = useGeneralSettingsStore();
    if (!activeModules.includes(Module.NFTS)) {
      return;
    }
    const section = Section.NON_FUNGIBLE_BALANCES;
    try {
      setStatus(Status.LOADING, section);
      const taskType = TaskType.NF_BALANCES;
      const { taskId } = await api.balances.fetchNfBalances(payload);
      const { result } = await awaitTask<NonFungibleBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.t('actions.nft_balances.task.title').toString(),
          numericKeys: []
        }
      );

      set(nonFungibleBalancesState, NonFungibleBalances.parse(result));
      setStatus(Status.LOADED, section);
    } catch (e: any) {
      logger.error(e);
      notify({
        title: i18n.t('actions.nft_balances.error.title').toString(),
        message: i18n
          .t('actions.nft_balances.error.message', {
            message: e.message
          })
          .toString(),
        display: true
      });
      setStatus(Status.NONE, section);
    }
  };

  const fetchBalances = async (payload: Partial<AllBalancePayload> = {}) => {
    if (get(isTaskRunning(TaskType.QUERY_BALANCES))) {
      return;
    }
    try {
      const { taskId } = await api.queryBalancesAsync(payload);
      await addTask(taskId, TaskType.QUERY_BALANCES, {
        title: i18n.t('actions.balances.all_balances.task.title').toString(),
        ignoreResult: true
      });
    } catch (e: any) {
      notify({
        title: i18n.t('actions.balances.all_balances.error.title').toString(),
        message: i18n
          .t('actions.balances.all_balances.error.message', {
            message: e.message
          })
          .toString(),
        display: true
      });
    }
    await fetchAccounts();
  };

  const fetch = async (exchanges: Exchange[]): Promise<void> => {
    await fetchManualBalances();
    await fetchExchangeRates();
    await fetchBalances();

    if (exchanges && exchanges.length > 0) {
      await setExchanges(exchanges);
    }

    await fetchBlockchainBalances();
    await fetchNfBalances();
    await fetchLoopringBalances(false);
  };

  const nfBalances = computed<NonFungibleBalance[]>(() => {
    const balances: NonFungibleBalance[] = [];
    const nonFungibleBalances = get(
      nonFungibleBalancesState
    ) as NonFungibleBalances;
    for (const address in nonFungibleBalances) {
      const addressNfBalance = nonFungibleBalances[address];
      balances.push(...addressNfBalance);
    }
    return balances;
  });

  const nfTotalValue = (includeLPToken: boolean = false) =>
    computed<BigNumber>(() => {
      return bigNumberSum(
        get(nfBalances)
          .filter(item => includeLPToken || !item.isLp)
          .map(item => item.usdPrice)
      );
    });

  const reset = () => {
    resetBlockchainBalancesStore();
    resetBlockchainAccountsStore();
    set(nonFungibleBalancesState, {});
  };

  return {
    nonFungibleBalancesState,
    nfBalances,
    nfTotalValue,
    adjustPrices,
    refreshPrices,
    assetBreakdown,
    locationBreakdown,
    balancesByLocation,
    fetchBalances,
    fetchNfBalances,
    fetch,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useBalancesStore, import.meta.hot));
}
