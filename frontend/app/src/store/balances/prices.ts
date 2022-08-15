import { BigNumber } from '@rotki/common';
import { computed, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore, storeToRefs } from 'pinia';
import { currencies, CURRENCY_USD } from '@/data/currencies';
import i18n from '@/i18n';
import { Balances } from '@/services/balances/types';
import { api } from '@/services/rotkehlchen-api';
import { useBlockchainBalancesStore } from '@/store/balances/blockchain-balances';
import {
  AssetPriceResponse,
  AssetPrices,
  FetchPricePayload,
  HistoricPricePayload,
  HistoricPrices,
  OracleCachePayload
} from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { ExchangeRates, PriceOracle } from '@/types/user';
import { bigNumberify } from '@/utils/bignumbers';
import { chunkArray } from '@/utils/data';
import { convertFromTimestamp } from '@/utils/date';

export const useBalancePricesStore = defineStore('balances/prices', () => {
  const prices = ref<AssetPrices>({});
  const { awaitTask, isTaskRunning } = useTasks();
  const { notify } = useNotifications();

  const fetchPrices = async (payload: FetchPricePayload) => {
    const { aggregatedAssets } = storeToRefs(useBlockchainBalancesStore());
    const assets = get(aggregatedAssets);

    const taskType = TaskType.UPDATE_PRICES;
    if (get(isTaskRunning(taskType))) {
      return;
    }

    const fetch = async (assets: string[]) => {
      const { taskId } = await api.balances.prices(
        payload.selectedAsset ? [payload.selectedAsset] : assets,
        CURRENCY_USD,
        payload.ignoreCache
      );

      const { result } = await awaitTask<AssetPriceResponse, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.t('actions.session.fetch_prices.task.title').toString(),
          numericKeys: null
        },
        true
      );

      set(prices, {
        ...get(prices),
        ...result.assets
      });
    };

    try {
      await Promise.all(
        chunkArray<string>(assets, 100).map(asset => fetch(asset))
      );
    } catch (e: any) {
      const title = i18n
        .t('actions.session.fetch_prices.error.title')
        .toString();
      const message = i18n
        .t('actions.session.fetch_prices.error.message', {
          error: e.message
        })
        .toString();
      notify({
        title,
        message,
        display: true
      });
    }
  };

  const updateBalancesPrices = (balances: Balances) => {
    for (const asset in balances) {
      const assetPrice = get(prices)[asset];
      if (!assetPrice) {
        continue;
      }
      const assetInfo = balances[asset];
      balances[asset] = {
        amount: assetInfo.amount,
        usdValue: assetInfo.amount.times(assetPrice)
      };
    }
    return balances;
  };

  const exchangeRates = ref<ExchangeRates>({});
  const fetchExchangeRates = async () => {
    try {
      const { taskId } = await api.getFiatExchangeRates(
        currencies.map(value => value.tickerSymbol)
      );

      const meta: TaskMeta = {
        title: i18n.t('actions.balances.exchange_rates.task.title').toString(),
        numericKeys: []
      };

      const { result } = await awaitTask<ExchangeRates, TaskMeta>(
        taskId,
        TaskType.EXCHANGE_RATES,
        meta
      );

      set(exchangeRates, ExchangeRates.parse(result));
    } catch (e: any) {
      notify({
        title: i18n.t('actions.balances.exchange_rates.error.title').toString(),
        message: i18n
          .t('actions.balances.exchange_rates.error.message', {
            message: e.message
          })
          .toString(),
        display: true
      });
    }
  };

  const exchangeRate = (currency: string) => {
    return computed<BigNumber | undefined>(() => {
      return get(exchangeRates)[currency] as BigNumber;
    });
  };

  const getHistoricPrice = async ({
    fromAsset,
    timestamp,
    toAsset
  }: HistoricPricePayload): Promise<BigNumber> => {
    const taskType = TaskType.FETCH_HISTORIC_PRICE;
    if (get(isTaskRunning(taskType))) {
      return bigNumberify(-1);
    }

    try {
      const { taskId } = await api.balances.fetchRate(
        fromAsset,
        toAsset,
        timestamp
      );
      const { result } = await awaitTask<HistoricPrices, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n
            .t('actions.balances.historic_fetch_price.task.title')
            .toString(),
          description: i18n
            .t('actions.balances.historic_fetch_price.task.description', {
              fromAsset,
              toAsset,
              date: convertFromTimestamp(timestamp)
            })
            .toString(),
          numericKeys: null
        },
        true
      );

      return result.assets[fromAsset][timestamp];
    } catch (e) {
      return bigNumberify(-1);
    }
  };

  const createOracleCache = async ({
    fromAsset,
    purgeOld,
    source,
    toAsset
  }: OracleCachePayload): Promise<ActionStatus> => {
    const taskType = TaskType.CREATE_PRICE_CACHE;
    if (get(isTaskRunning(taskType))) {
      return {
        success: false,
        message: i18n
          .t('actions.balances.create_oracle_cache.already_running')
          .toString()
      };
    }
    try {
      const { taskId } = await api.balances.createPriceCache(
        source,
        fromAsset,
        toAsset,
        purgeOld
      );
      const { result } = await awaitTask<true, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n
            .t('actions.balances.create_oracle_cache.task', {
              fromAsset,
              toAsset,
              source
            })
            .toString(),
          numericKeys: null
        },
        true
      );

      return {
        success: result
      };
    } catch (e: any) {
      return {
        success: false,
        message: i18n
          .t('actions.balances.create_oracle_cache.failed', {
            fromAsset,
            toAsset,
            source,
            error: e.message
          })
          .toString()
      };
    }
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
    fetchPrices,
    updateBalancesPrices,
    exchangeRates,
    fetchExchangeRates,
    exchangeRate,
    getHistoricPrice,
    createOracleCache,
    getPriceCache,
    deletePriceCache
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useBalancePricesStore, import.meta.hot)
  );
}
