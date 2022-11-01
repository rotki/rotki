import { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import { MaybeRef } from '@vueuse/core';
import { ComputedRef, Ref } from 'vue';
import { useStatusUpdater } from '@/composables/status';
import { useExchangeApi } from '@/services/balances/exchanges';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useBalancePricesStore } from '@/store/balances/prices';
import { AssetBreakdown, ExchangeBalancePayload } from '@/store/balances/types';
import { usePurgeStore } from '@/store/history/purge';
import { useMessageStore } from '@/store/message';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { AssetBalances } from '@/types/balances';
import {
  EditExchange,
  Exchange,
  ExchangeData,
  ExchangeInfo,
  ExchangeSetupPayload,
  SupportedExchange
} from '@/types/exchanges';
import { AssetPrices } from '@/types/prices';
import { Section, Status } from '@/types/status';
import { ExchangeMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';
import {
  appendAssetBalance,
  mergeAssociatedAssets,
  sumAssetBalances,
  toStoredAssetBalanceWithPrice
} from '@/utils/balances';
import { sortDesc } from '@/utils/bignumbers';
import { assetSum } from '@/utils/calculation';
import { updateBalancesPrices } from '@/utils/prices';

export const useExchangeBalancesStore = defineStore(
  'balances/exchanges',
  () => {
    const connectedExchanges: Ref<Exchange[]> = ref([]);
    const exchangeBalances: Ref<ExchangeData> = ref({});

    const { t, tc } = useI18n();

    const { awaitTask, isTaskRunning, metadata } = useTasks();
    const { notify } = useNotifications();
    const { setMessage } = useMessageStore();
    const { purgeHistoryLocation } = usePurgeStore();
    const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
    const { isAssetIgnored } = useIgnoredAssetsStore();
    const { getAssetPrice } = useBalancePricesStore();
    const { queryRemoveExchange, queryExchangeBalances, querySetupExchange } =
      useExchangeApi();

    const exchanges: ComputedRef<ExchangeInfo[]> = computed(() => {
      const balances = get(exchangeBalances);
      return Object.keys(balances)
        .map(value => ({
          location: value,
          balances: balances[value],
          total: assetSum(balances[value])
        }))
        .sort((a, b) => sortDesc(a.total, b.total));
    });

    const balances: ComputedRef<AssetBalances> = computed(() => {
      return sumAssetBalances(
        Object.values(get(exchangeBalances)),
        getAssociatedAssetIdentifier
      );
    });

    const getBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> =>
      computed(() => {
        const breakdown: AssetBreakdown[] = [];
        const cexBalances = get(exchangeBalances);
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
        return breakdown;
      });

    const getLocationBreakdown = (id: string): ComputedRef<AssetBalances> =>
      computed(() => {
        const assets: AssetBalances = {};
        const exchange = get(connectedExchanges).find(
          ({ location }) => id === location
        );

        if (exchange) {
          const balances = get(getBalances(exchange.location));
          for (const balance of balances) {
            appendAssetBalance(balance, assets, getAssociatedAssetIdentifier);
          }
        }
        return assets;
      });

    const getByLocationBalances = (
      convert: (bn: MaybeRef<BigNumber>) => MaybeRef<BigNumber>
    ): ComputedRef<Record<string, BigNumber>> =>
      computed(() => {
        const balances: Record<string, BigNumber> = {};
        for (const { location, total } of get(exchanges)) {
          const balance = balances[location];
          const value = get(convert(total));
          balances[location] = !balance ? value : value.plus(balance);
        }
        return balances;
      });

    const getExchangeNonce = (
      exchange: SupportedExchange
    ): ComputedRef<number> =>
      computed(() => {
        return (
          get(connectedExchanges).filter(
            ({ location }) => location === exchange
          ).length + 1
        );
      });

    const getBalances = (
      exchange: SupportedExchange,
      hideIgnored: boolean = true
    ): ComputedRef<AssetBalanceWithPrice[]> =>
      computed(() => {
        const balances = get(exchangeBalances);

        if (balances && balances[exchange]) {
          return toStoredAssetBalanceWithPrice(
            get(
              mergeAssociatedAssets(
                balances[exchange],
                getAssociatedAssetIdentifier
              )
            ),
            asset => hideIgnored && get(isAssetIgnored(asset)),
            getAssetPrice
          );
        }

        return [];
      });

    const addExchange = (exchange: Exchange): void => {
      set(connectedExchanges, [...get(connectedExchanges), exchange]);
    };

    const editExchange = ({
      exchange: { location, name: oldName, krakenAccountType, ftxSubaccount },
      newName
    }: EditExchange): void => {
      const exchanges = [...get(connectedExchanges)];
      const name = newName ?? oldName;
      const index = exchanges.findIndex(
        value => value.name === oldName && value.location === location
      );
      exchanges[index] = {
        ...exchanges[index],
        name,
        location,
        krakenAccountType,
        ftxSubaccount
      };
      set(connectedExchanges, exchanges);
    };

    const removeExchange = async (exchange: Exchange): Promise<boolean> => {
      try {
        const success = await queryRemoveExchange(exchange);
        const connected = get(connectedExchanges);
        if (success) {
          const exchangeIndex = connected.findIndex(
            ({ location, name }) =>
              name === exchange.name && location === exchange.location
          );
          assert(
            exchangeIndex >= 0,
            `${exchange} not found in ${connected
              .map(exchange => `${exchange.name} on ${exchange.location}`)
              .join(', ')}`
          );

          const exchanges = [...connected];
          const balances = { ...get(exchangeBalances) };
          const index = exchanges.findIndex(
            ({ location, name }) =>
              name === exchange.name && location === exchange.location
          );
          // can't modify in place or else the vue reactivity does not work
          exchanges.splice(index, 1);
          delete balances[exchange.location];
          set(connectedExchanges, exchanges);
          set(exchangeBalances, balances);

          if (exchanges.length > 0) {
            await fetchExchangeBalances({
              location: exchange.location,
              ignoreCache: false
            });
          }
        }

        await purgeHistoryLocation(exchange.location);

        return success;
      } catch (e: any) {
        setMessage({
          title: tc('actions.balances.exchange_removal.title'),
          description: tc('actions.balances.exchange_removal.description', 0, {
            exchange,
            error: e.message
          })
        });
        return false;
      }
    };

    const setExchanges = (exchanges: Exchange[]): void => {
      set(connectedExchanges, exchanges);
    };

    const fetchExchangeBalances = async (
      payload: ExchangeBalancePayload
    ): Promise<void> => {
      const { location, ignoreCache } = payload;
      const taskType = TaskType.QUERY_EXCHANGE_BALANCES;
      const meta = metadata<ExchangeMeta>(taskType);

      if (get(isTaskRunning(taskType)) && meta?.location === location) {
        return;
      }

      const { setStatus, resetStatus, isFirstLoad } = useStatusUpdater(
        Section.EXCHANGES
      );

      const newStatus = isFirstLoad() ? Status.LOADING : Status.REFRESHING;
      setStatus(newStatus);

      try {
        const { taskId } = await queryExchangeBalances(location, ignoreCache);
        const meta: ExchangeMeta = {
          location,
          title: t('actions.balances.exchange_balances.task.title', {
            location
          }).toString(),
          numericKeys: []
        };

        const { result } = await awaitTask<AssetBalances, ExchangeMeta>(
          taskId,
          taskType,
          meta,
          true
        );

        set(exchangeBalances, {
          ...get(exchangeBalances),
          [location]: AssetBalances.parse(result)
        });
        setStatus(Status.LOADED);
      } catch (e: any) {
        const message = t('actions.balances.exchange_balances.error.message', {
          location,
          error: e.message
        }).toString();
        const title = t('actions.balances.exchange_balances.error.title', {
          location
        }).toString();

        notify({
          title,
          message,
          display: true
        });
        resetStatus();
      }
    };

    const fetchConnectedExchangeBalances = async (
      refresh: boolean = false
    ): Promise<void> => {
      const exchanges = get(connectedExchanges);
      for (const exchange of exchanges) {
        await fetchExchangeBalances({
          location: exchange.location,
          ignoreCache: refresh
        } as ExchangeBalancePayload);
      }
    };

    const setupExchange = async ({
      exchange,
      edit
    }: ExchangeSetupPayload): Promise<boolean> => {
      try {
        const success = await querySetupExchange(exchange, edit);
        const exchangeEntry: Exchange = {
          name: exchange.name,
          location: exchange.location,
          krakenAccountType: exchange.krakenAccountType ?? undefined,
          ftxSubaccount: exchange.ftxSubaccount ?? undefined
        };

        if (!edit) {
          addExchange(exchangeEntry);
        } else {
          editExchange({
            exchange: exchangeEntry,
            newName: exchange.newName
          });
        }

        await fetchExchangeBalances({
          location: exchange.location,
          ignoreCache: false
        });
        //await refreshPrices({ ignoreCache: false });

        await purgeHistoryLocation(exchange.location);

        return success;
      } catch (e: any) {
        setMessage({
          title: t('actions.balances.exchange_setup.title').toString(),
          description: t('actions.balances.exchange_setup.description', {
            exchange: exchange.location,
            error: e.message
          }).toString()
        });
        return false;
      }
    };

    const updatePrices = (prices: MaybeRef<AssetPrices>) => {
      const exchanges = { ...(get(exchangeBalances) as ExchangeData) };
      for (const exchange in exchanges) {
        exchanges[exchange] = updateBalancesPrices(exchanges[exchange], prices);
      }

      set(exchangeBalances, exchanges);
    };

    return {
      exchanges,
      connectedExchanges,
      exchangeBalances,
      balances,
      setExchanges,
      setupExchange,
      addExchange,
      editExchange,
      removeExchange,
      getBalances,
      getExchangeNonce,
      fetchExchangeBalances,
      fetchConnectedExchangeBalances,
      getBreakdown,
      getLocationBreakdown,
      getByLocationBalances,
      updatePrices
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useExchangeBalancesStore, import.meta.hot)
  );
}
