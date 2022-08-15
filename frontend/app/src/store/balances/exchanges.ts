import { AssetBalanceWithPrice, Balance, BigNumber } from '@rotki/common';
import { computed, ComputedRef, Ref, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { forEach } from 'lodash';
import { acceptHMRUpdate, defineStore, storeToRefs } from 'pinia';
import i18n from '@/i18n';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { useAssetInfoRetrieval, useIgnoredAssetsStore } from '@/store/assets';
import { useBalancesStore } from '@/store/balances/index';
import { useBalancePricesStore } from '@/store/balances/prices';
import {
  AssetBalances,
  EditExchange,
  ExchangeBalancePayload,
  ExchangeSetupPayload
} from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { useHistory } from '@/store/history';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { getStatus, setStatus, showError } from '@/store/utils';
import {
  Exchange,
  ExchangeData,
  ExchangeInfo,
  SupportedExchange
} from '@/types/exchanges';
import { ExchangeMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';
import { NoPrice, sortDesc } from '@/utils/bignumbers';
import { assetSum, balanceSum } from '@/utils/calculation';

export const useExchangeBalancesStore = defineStore(
  'balances/exchanges',
  () => {
    const connectedExchanges: Ref<Exchange[]> = ref([]);
    const exchangeBalances: Ref<ExchangeData> = ref({});

    const { awaitTask, isTaskRunning, metadata } = useTasks();
    const { notify } = useNotifications();
    const { purgeHistoryLocation } = useHistory();
    const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
    const { isAssetIgnored } = useIgnoredAssetsStore();

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

    const getExchangeNonce = (exchange: SupportedExchange) =>
      computed(() => {
        return (
          get(connectedExchanges).filter(
            ({ location }) => location === exchange
          ).length + 1
        );
      });

    const getBalances = (
      exchange: SupportedExchange
    ): ComputedRef<AssetBalanceWithPrice[]> =>
      computed(() => {
        const { prices } = storeToRefs(useBalancePricesStore());
        const ownedAssets: Record<string, Balance> = {};
        const balances = get(exchangeBalances);

        forEach(balances[exchange], (value: Balance, asset: string) => {
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
        });

        return Object.keys(ownedAssets)
          .filter(asset => !get(isAssetIgnored(asset)))
          .map(asset => ({
            asset,
            amount: ownedAssets[asset].amount,
            usdValue: ownedAssets[asset].usdValue,
            usdPrice: (get(prices)[asset] as BigNumber) ?? NoPrice
          }));
      });

    const addExchange = (exchange: Exchange) => {
      set(connectedExchanges, [...get(connectedExchanges), exchange]);
    };

    const editExchange = ({
      exchange: { location, name: oldName, krakenAccountType, ftxSubaccount },
      newName
    }: EditExchange) => {
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
        const success = await api.removeExchange(exchange);
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
        showError(
          i18n.tc('actions.balances.exchange_removal.description', 0, {
            exchange,
            error: e.message
          }),
          i18n.tc('actions.balances.exchange_removal.title')
        );
        return false;
      }
    };

    const setExchanges = async (exchanges: Exchange[]): Promise<void> => {
      set(connectedExchanges, exchanges);
      await fetchConnectedExchangeBalances(false);
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

      const currentStatus: Status = getStatus(Section.EXCHANGES);
      const section = Section.EXCHANGES;
      const newStatus =
        currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
      setStatus(newStatus, section);

      try {
        const { taskId } = await api.queryExchangeBalances(
          location,
          ignoreCache
        );
        const meta: ExchangeMeta = {
          location,
          title: i18n
            .t('actions.balances.exchange_balances.task.title', {
              location
            })
            .toString(),
          numericKeys: balanceKeys
        };

        const { result } = await awaitTask<AssetBalances, ExchangeMeta>(
          taskId,
          taskType,
          meta,
          true
        );

        set(exchangeBalances, {
          ...get(exchangeBalances),
          [location]: result
        });
      } catch (e: any) {
        const message = i18n
          .t('actions.balances.exchange_balances.error.message', {
            location,
            error: e.message
          })
          .toString();
        const title = i18n
          .t('actions.balances.exchange_balances.error.title', {
            location
          })
          .toString();

        notify({
          title,
          message,
          display: true
        });
      } finally {
        setStatus(Status.LOADED, section);
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
        const success = await api.setupExchange(exchange, edit);
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

        const { refreshPrices } = useBalancesStore();

        fetchExchangeBalances({
          location: exchange.location,
          ignoreCache: false
        }).then(() => refreshPrices({ ignoreCache: false }));

        purgeHistoryLocation(exchange.location);

        return success;
      } catch (e: any) {
        showError(
          i18n
            .t('actions.balances.exchange_setup.description', {
              exchange: exchange.location,
              error: e.message
            })
            .toString(),
          i18n.t('actions.balances.exchange_setup.title').toString()
        );
        return false;
      }
    };

    const reset = () => {
      set(connectedExchanges, []);
      set(exchangeBalances, {});
    };

    return {
      exchanges,
      connectedExchanges,
      exchangeBalances,
      setExchanges,
      setupExchange,
      addExchange,
      editExchange,
      removeExchange,
      getBalances,
      getExchangeNonce,
      fetchExchangeBalances,
      fetchConnectedExchangeBalances,
      reset
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useExchangeBalancesStore, import.meta.hot)
  );
}
