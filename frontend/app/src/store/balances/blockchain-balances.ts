import {
  AssetBalance,
  AssetBalanceWithPrice,
  Balance,
  BigNumber
} from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { get, set } from '@vueuse/core';
import { forEach } from 'lodash';
import cloneDeep from 'lodash/cloneDeep';
import isEmpty from 'lodash/isEmpty';
import { acceptHMRUpdate, defineStore, storeToRefs } from 'pinia';
import { computed, Ref, ref } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { setupLiquidityPosition } from '@/composables/defi';
import { bigNumberSum } from '@/filters';
import {
  BlockchainAssetBalances,
  BlockchainBalances,
  BtcBalances,
  ManualBalanceWithValue
} from '@/services/balances/types';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval, useIgnoredAssetsStore } from '@/store/assets';
import { useBlockchainAccountsStore } from '@/store/balances/blockchain-accounts';
import { chainSection, samePriceAssets } from '@/store/balances/const';
import { useEthNamesStore } from '@/store/balances/ethereum-names';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useBalancePricesStore } from '@/store/balances/prices';
import {
  AccountAssetBalances,
  AssetBalances,
  BlockchainBalancePayload
} from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { getStatus, isLoading, setStatus } from '@/store/utils';
import { Module } from '@/types/modules';
import { BlockchainMetadata, TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { NoPrice, sortDesc } from '@/utils/bignumbers';
import { balanceSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';

const defaultTotals = () => ({
  ETH: {},
  ETH2: {},
  BTC: {},
  BCH: {},
  KSM: {},
  DOT: {},
  AVAX: {}
});

const defaultBtcBalances = (): BtcBalances => ({
  standalone: {},
  xpubs: []
});

export const useBlockchainBalancesStore = defineStore(
  'balances/blockchain',
  () => {
    const ethBalancesState: Ref<BlockchainAssetBalances> = ref({});
    const eth2BalancesState: Ref<BlockchainAssetBalances> = ref({});
    const btcBalancesState: Ref<BtcBalances> = ref(defaultBtcBalances());
    const bchBalancesState: Ref<BtcBalances> = ref(defaultBtcBalances());
    const ksmBalancesState: Ref<BlockchainAssetBalances> = ref({});
    const dotBalancesState: Ref<BlockchainAssetBalances> = ref({});
    const avaxBalancesState: Ref<BlockchainAssetBalances> = ref({});
    const loopringBalancesState: Ref<AccountAssetBalances> = ref({});

    const blockchainTotalsState: Ref<Record<Blockchain, AssetBalances>> = ref(
      defaultTotals()
    );

    const blockchainLiabilitiesState: Ref<Record<Blockchain, AssetBalances>> =
      ref(defaultTotals());

    const aggregatedBlockchainTotals = computed<AssetBalances>(() => {
      const totals = get(blockchainTotalsState);

      let result = {};

      Object.values(totals).forEach(item => {
        result = { ...result, ...item };
      });

      return result;
    });

    const aggregatedBlockchainLiabilities = computed<AssetBalances>(() => {
      const totals = get(blockchainLiabilitiesState);

      let result = {};

      Object.values(totals).forEach(item => {
        result = { ...result, ...item };
      });

      return result;
    });

    const { awaitTask } = useTasks();
    const { notify } = useNotifications();

    const exchangeStore = useExchangeBalancesStore();
    const { connectedExchanges } = storeToRefs(exchangeStore);
    const { getBalances: getExchangeBalances } = exchangeStore;

    const manualBalancesStore = useManualBalancesStore();
    const { manualBalances, manualLiabilities } =
      storeToRefs(manualBalancesStore);

    const { t, tc } = useI18n();

    const fetchBlockchainBalances = async (
      payload: BlockchainBalancePayload = {
        ignoreCache: false
      }
    ): Promise<void> => {
      const { blockchain, ignoreCache } = payload;

      const chains: Blockchain[] = [];
      if (!blockchain) {
        chains.push(...Object.values(Blockchain));
      } else {
        chains.push(blockchain);
      }

      const fetch: (chain: Blockchain) => Promise<void> = async (
        chain: Blockchain
      ) => {
        const section = chainSection[chain];
        const currentStatus = getStatus(section);

        if (isLoading(currentStatus)) {
          return;
        }

        const newStatus =
          currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
        setStatus(newStatus, section);

        const { taskId } = await api.balances.queryBlockchainBalances(
          ignoreCache,
          chain
        );
        const taskType = TaskType.QUERY_BLOCKCHAIN_BALANCES;
        const { result } = await awaitTask<
          BlockchainBalances,
          BlockchainMetadata
        >(
          taskId,
          taskType,
          {
            chain,
            title: tc('actions.balances.blockchain.task.title', 0, {
              chain
            }),
            numericKeys: []
          } as BlockchainMetadata,
          true
        );
        const balances = BlockchainBalances.parse(result);
        await updateBlockchainBalances({
          chain,
          balances,
          ignoreCache
        });
        setStatus(Status.LOADED, section);
      };
      try {
        await Promise.all(chains.map(fetch));
      } catch (e: any) {
        logger.error(e);
        const message = tc('actions.balances.blockchain.error.description', 0, {
          error: e.message
        });
        notify({
          title: tc('actions.balances.blockchain.error.title'),
          message,
          display: true
        });
      }
    };

    const pricesStore = useBalancePricesStore();
    const { updateBalancesPrices } = pricesStore;
    const { prices } = storeToRefs(pricesStore);

    const fetchLoopringBalances = async (refresh: boolean) => {
      const { activeModules } = useGeneralSettingsStore();
      if (!activeModules.includes(Module.LOOPRING)) {
        return;
      }

      const section = Section.L2_LOOPRING_BALANCES;
      const currentStatus = getStatus(section);

      if (
        isLoading(currentStatus) ||
        (currentStatus === Status.LOADED && !refresh)
      ) {
        return;
      }

      const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
      setStatus(newStatus, section);
      try {
        const taskType = TaskType.L2_LOOPRING;
        const { taskId } = await api.balances.loopring();
        const { result } = await awaitTask<AccountAssetBalances, TaskMeta>(
          taskId,
          taskType,
          {
            title: t('actions.balances.loopring.task.title').toString(),
            numericKeys: balanceKeys
          }
        );

        set(loopringBalancesState, result);
      } catch (e: any) {
        notify({
          title: t('actions.balances.loopring.error.title').toString(),
          message: t('actions.balances.loopring.error.description', {
            error: e.message
          }).toString(),
          display: true
        });
      }
      setStatus(Status.LOADED, section);
    };

    const updateBlockchainTotalsState = (
      chain: Blockchain,
      payload: AssetBalances
    ) => {
      const totals = { ...payload };

      for (const asset in totals) {
        if (totals[asset].amount.isZero()) delete totals[asset];
      }

      const totalsState = {
        ...get(blockchainTotalsState),
        [chain]: totals
      };

      set(blockchainTotalsState, totalsState);
    };

    const updateBlockchainLiabilitiesState = (
      chain: Blockchain,
      payload: AssetBalances
    ) => {
      const totals = { ...payload };

      for (const asset in totals) {
        if (totals[asset].amount.isZero()) delete totals[asset];
      }

      const liabilitiesState = {
        ...get(blockchainLiabilitiesState),
        [chain]: liabilities
      };

      set(blockchainLiabilitiesState, liabilitiesState);
    };

    const updateBlockchainBalances = async (payload: {
      chain: Blockchain;
      balances: BlockchainBalances;
      ignoreCache?: boolean;
    }) => {
      const { perAccount, totals } = payload.balances;
      const chain = payload.chain;
      const forceUpdate = payload.ignoreCache;

      const ethBalances = perAccount[Blockchain.ETH];

      if (forceUpdate && ethBalances) {
        const addresses = [...Object.keys(ethBalances)];

        const { fetchEnsNames } = useEthNamesStore();
        await fetchEnsNames(addresses, forceUpdate);
      }

      const updateList = [
        { blockchain: Blockchain.ETH, state: ethBalancesState },
        { blockchain: Blockchain.ETH2, state: eth2BalancesState },
        { blockchain: Blockchain.KSM, state: ksmBalancesState },
        { blockchain: Blockchain.DOT, state: dotBalancesState },
        { blockchain: Blockchain.AVAX, state: avaxBalancesState },
        {
          blockchain: Blockchain.BTC,
          state: btcBalancesState,
          default: () => ({ standalone: [], xpubs: [] })
        },
        {
          blockchain: Blockchain.BCH,
          state: bchBalancesState,
          default: () => ({ standalone: [], xpubs: [] })
        }
      ];

      updateList.forEach(list => {
        if (chain === list.blockchain) {
          set(
            list.state,
            perAccount[list.blockchain] ?? (list.default ? list.default() : {})
          );
        }
      });

      updateBlockchainTotalsState(chain, totals.assets);
      updateBlockchainLiabilitiesState(chain, totals.liabilities);

      const blockchainToRefresh = chain ? [chain] : null;
      const { fetchAccounts } = useBlockchainAccountsStore();
      await fetchAccounts(blockchainToRefresh);
    };

    const adjustBlockchainPrices = async () => {
      const updateTotalsPrices = (
        state: Ref<Record<Blockchain, AssetBalances>>
      ) => {
        for (const chain in get(state)) {
          const balances = get(state)[chain as Blockchain];
          for (const asset in balances) {
            const assetPrice = get(prices)[asset];
            if (!assetPrice) {
              continue;
            }

            const oldState = get(state);
            const newChain = {
              ...oldState[chain as Blockchain],
              [asset]: {
                amount: balances[asset].amount,
                usdValue: balances[asset].amount.times(assetPrice)
              }
            };

            const newState = {
              ...oldState,
              [chain]: newChain
            };

            set(state, newState);
          }
        }
      };

      updateTotalsPrices(blockchainTotalsState);
      updateTotalsPrices(blockchainLiabilitiesState);

      const updateDefaultBlockchainPrices = (
        state: Ref<BlockchainAssetBalances>
      ) => {
        const clonedState = cloneDeep(get(state));
        for (const address in clonedState) {
          const balances = clonedState[address];
          clonedState[address] = {
            assets: updateBalancesPrices(balances.assets),
            liabilities: updateBalancesPrices(balances.liabilities)
          };
        }

        set(state, clonedState);
      };

      [
        ethBalancesState,
        dotBalancesState,
        ksmBalancesState,
        avaxBalancesState
      ].map(state => updateDefaultBlockchainPrices(state));

      const updateBtcNetworkPrices = (
        state: Ref<BtcBalances>,
        blockchain: Blockchain.BTC | Blockchain.BCH
      ) => {
        const assetPrice = get(prices)[blockchain];
        if (assetPrice) {
          const clonedState = cloneDeep(get(state));
          for (const address in clonedState.standalone) {
            const balance = clonedState.standalone[address];
            clonedState.standalone[address] = {
              amount: balance.amount,
              usdValue: balance.amount.times(assetPrice)
            };
          }
          const xpubs = clonedState.xpubs;
          if (xpubs) {
            for (let i = 0; i < xpubs.length; i++) {
              const xpub = xpubs[i];
              for (const address in xpub.addresses) {
                const balance = xpub.addresses[address];
                xpub.addresses[address] = {
                  amount: balance.amount,
                  usdValue: balance.amount.times(assetPrice)
                };
              }
            }
          }

          set(state, clonedState);
        }
      };

      updateBtcNetworkPrices(btcBalancesState, Blockchain.BTC);
      updateBtcNetworkPrices(bchBalancesState, Blockchain.BCH);
    };

    const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
    const { isAssetIgnored } = useIgnoredAssetsStore();
    const totals = (hideIgnored: boolean = true) =>
      computed<AssetBalance[]>(() => {
        const ownedAssets: Record<string, Balance> = {};

        forEach(
          get(aggregatedBlockchainTotals),
          (value: Balance, asset: string) => {
            const associatedAsset: string = get(
              getAssociatedAssetIdentifier(asset)
            );

            const ownedAsset = ownedAssets[associatedAsset];

            ownedAssets[associatedAsset] = !ownedAsset
              ? {
                  ...value
                }
              : {
                  ...balanceSum(ownedAsset, value)
                };
          }
        );

        return Object.keys(ownedAssets)
          .filter(asset => !hideIgnored || !get(isAssetIgnored(asset)))
          .map(asset => ({
            asset,
            amount: ownedAssets[asset].amount,
            usdValue: ownedAssets[asset].usdValue
          }))
          .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
      });

    const aggregatedBalances = (hideIgnored: boolean = true) =>
      computed(() => {
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

        const exchanges = get(connectedExchanges)
          .map(({ location }) => location)
          .filter(uniqueStrings);

        for (const exchange of exchanges) {
          const balances = get(getExchangeBalances(exchange, hideIgnored));
          balances.forEach((value: AssetBalance) => addToOwned(value));
        }

        get(totals(hideIgnored)).forEach((value: AssetBalance) =>
          addToOwned(value)
        );

        (get(manualBalances) as ManualBalanceWithValue[]).forEach(value =>
          addToOwned(value)
        );

        const loopringBalances = get(loopringBalancesState);
        for (const address in loopringBalances) {
          const balances = loopringBalances[address];
          for (const asset in balances) {
            addToOwned({
              ...balances[asset],
              asset
            });
          }
        }

        return Object.keys(ownedAssets)
          .filter(asset => !hideIgnored || !get(isAssetIgnored(asset)))
          .map(asset => ({
            asset,
            amount: ownedAssets[asset].amount,
            usdValue: ownedAssets[asset].usdValue,
            usdPrice: (get(prices)[asset] as BigNumber) ?? NoPrice
          }))
          .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
      });

    const liabilities = (hideIgnored: boolean = true) =>
      computed<AssetBalanceWithPrice[]>(() => {
        const liabilitiesMerged: Record<string, Balance> = {};

        const addToLiabilities = (value: AssetBalance) => {
          const associatedAsset: string = get(
            getAssociatedAssetIdentifier(value.asset)
          );

          const liability = liabilitiesMerged[associatedAsset];

          liabilitiesMerged[associatedAsset] = !liability
            ? {
                ...value
              }
            : {
                ...balanceSum(liability, value)
              };
        };

        forEach(
          get(aggregatedBlockchainLiabilities),
          (balance: Balance, asset: string) => {
            addToLiabilities({ asset, ...balance });
          }
        );

        (get(manualLiabilities) as ManualBalanceWithValue[]).forEach(balance =>
          addToLiabilities(balance)
        );

        return Object.keys(liabilitiesMerged)
          .filter(asset => !hideIgnored || !get(isAssetIgnored(asset)))
          .map(asset => ({
            asset,
            amount: liabilitiesMerged[asset].amount,
            usdValue: liabilitiesMerged[asset].usdValue,
            usdPrice: (get(prices)[asset] as BigNumber) ?? NoPrice
          }))
          .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
      });

    const blockchainTotal = computed<BigNumber>(() => {
      return bigNumberSum(get(totals()).map(asset => asset.usdValue));
    });

    const accountAssets = (account: string) =>
      computed<AssetBalance[]>(() => {
        const ethAccount = get(ethBalancesState)[account];
        if (!ethAccount || isEmpty(ethAccount)) {
          return [];
        }

        return Object.entries(ethAccount.assets)
          .filter(([asset]) => !get(isAssetIgnored(asset)))
          .map(
            ([asset, { amount, usdValue }]) =>
              ({
                asset,
                amount,
                usdValue
              } as AssetBalance)
          );
      });

    const accountLiabilities = (account: string) =>
      computed<AssetBalance[]>(() => {
        const ethAccount = get(ethBalancesState)[account];
        if (!ethAccount || isEmpty(ethAccount)) {
          return [];
        }

        return Object.entries(ethAccount.liabilities)
          .filter(([asset]) => !get(isAssetIgnored(asset)))
          .map(
            ([asset, { amount, usdValue }]) =>
              ({
                asset,
                amount,
                usdValue
              } as AssetBalance)
          );
      });

    const hasDetails = (account: string) => {
      const ethAccount = get(ethBalancesState)[account];
      const loopringBalance = get(loopringBalancesState)[account] || {};
      if (!ethAccount || isEmpty(ethAccount)) {
        return false;
      }

      const assetsCount = Object.entries(ethAccount.assets).length;
      const liabilitiesCount = Object.entries(ethAccount.liabilities).length;
      const loopringsCount = Object.entries(loopringBalance).length;

      return assetsCount + liabilitiesCount + loopringsCount > 1;
    };

    const aggregatedAssets = (hideIgnored: boolean = true) =>
      computed<string[]>(() => {
        const additional: string[] = [];
        const liabilitiesAsset = get(liabilities(hideIgnored)).map(
          ({ asset }) => {
            const samePrices = samePriceAssets[asset];
            if (samePrices) additional.push(...samePrices);
            return asset;
          }
        );
        const assets = get(aggregatedBalances(hideIgnored)).map(({ asset }) => {
          const samePrices = samePriceAssets[asset];
          if (samePrices) additional.push(...samePrices);
          return asset;
        });

        const { lpAggregatedBalances } = setupLiquidityPosition();
        const lpBalances = get(lpAggregatedBalances(false));
        const lpAssets = lpBalances
          .map(item => item.asset)
          .filter(item => !!item) as string[];

        assets.push(...liabilitiesAsset, ...lpAssets, ...additional);
        return assets.filter(uniqueStrings);
      });

    const loopringBalances = (address: string) =>
      computed<AssetBalance[]>(() => {
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

        const loopringBalance = get(loopringBalancesState)[address];
        if (loopringBalance) {
          for (const asset in loopringBalance) {
            addToOwned({
              asset,
              ...loopringBalance[asset]
            });
          }
        }
        return Object.keys(ownedAssets)
          .filter(asset => !get(isAssetIgnored(asset)))
          .map(asset => ({
            asset,
            amount: ownedAssets[asset].amount,
            usdValue: ownedAssets[asset].usdValue
          }))
          .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
      });

    const blockchainAssets = computed<AssetBalanceWithPrice[]>(() => {
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

      get(totals()).forEach(total => addToOwned(total));

      const loopringBalances = get(loopringBalancesState);
      for (const address in loopringBalances) {
        const accountBalances = loopringBalances[address];

        forEach(accountBalances, (balance: Balance, asset: string) => {
          addToOwned({ asset, ...balance });
        });
      }

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

    const reset = () => {
      set(ethBalancesState, {});
      set(eth2BalancesState, {});
      set(btcBalancesState, defaultBtcBalances());
      set(bchBalancesState, defaultBtcBalances());
      set(ksmBalancesState, {});
      set(dotBalancesState, {});
      set(avaxBalancesState, {});
      set(loopringBalancesState, {});
      set(blockchainTotalsState, defaultTotals());
      set(blockchainLiabilitiesState, defaultTotals());
    };

    return {
      ethBalancesState,
      eth2BalancesState,
      btcBalancesState,
      bchBalancesState,
      ksmBalancesState,
      dotBalancesState,
      avaxBalancesState,
      loopringBalancesState,
      blockchainTotalsState,
      blockchainLiabilitiesState,
      totals,
      blockchainTotal,
      aggregatedBalances,
      liabilities,
      aggregatedAssets,
      accountAssets,
      accountLiabilities,
      hasDetails,
      loopringBalances,
      blockchainAssets,
      adjustBlockchainPrices,
      updateBlockchainBalances,
      fetchBlockchainBalances,
      fetchLoopringBalances,
      reset
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useBlockchainBalancesStore, import.meta.hot)
  );
}
