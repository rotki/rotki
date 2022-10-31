import { BigNumber } from '@rotki/common';
import { MaybeRef } from '@vueuse/core';
import { ComputedRef } from 'vue';
import { useStatusUpdater } from '@/composables/status';
import { usePriceApi } from '@/services/balances/price';
import { FetchPricePayload } from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { Balances } from '@/types/blockchain/balances';
import { useCurrencies, CURRENCY_USD } from '@/types/currencies';
import {
  AssetPriceResponse,
  AssetPrices,
  HistoricPricePayload,
  HistoricPrices,
  OracleCachePayload
} from '@/types/prices';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { ExchangeRates } from '@/types/user';
import { bigNumberify } from '@/utils/bignumbers';
import { chunkArray } from '@/utils/data';
import { convertFromTimestamp } from '@/utils/date';

export const useBalancePricesStore = defineStore('balances/prices', () => {
  const prices = ref<AssetPrices>({});
  const exchangeRates = ref<ExchangeRates>({});

  const { awaitTask, isTaskRunning } = useTasks();
  const { notify } = useNotifications();
  const { t } = useI18n();
  const {
    getPriceCache,
    createPriceCache,
    deletePriceCache,
    queryHistoricalRate,
    queryFiatExchangeRates,
    queryPrices
  } = usePriceApi();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { currencies } = useCurrencies();

  const fetchPrices = async (payload: FetchPricePayload): Promise<void> => {
    const taskType = TaskType.UPDATE_PRICES;

    const fetch = async (assets: string[]): Promise<void> => {
      const { taskId } = await queryPrices(
        assets,
        CURRENCY_USD,
        payload.ignoreCache
      );

      const { result } = await awaitTask<AssetPriceResponse, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.session.fetch_prices.task.title').toString(),
          numericKeys: []
        },
        true
      );

      set(prices, {
        ...get(prices),
        ...AssetPriceResponse.parse(result)
      });
    };

    const { setStatus } = useStatusUpdater(Section.PRICES);

    try {
      setStatus(Status.LOADING);
      await Promise.all(
        chunkArray<string>(payload.selectedAssets, 100).map(fetch)
      );
    } catch (e: any) {
      const title = t('actions.session.fetch_prices.error.title').toString();
      const message = t('actions.session.fetch_prices.error.message', {
        error: e.message
      }).toString();
      notify({
        title,
        message,
        display: true
      });
    } finally {
      setStatus(Status.LOADED);
    }
  };

  const updateBalancesPrices = (balances: Balances): Balances => {
    for (const asset in balances) {
      const assetPrice = get(prices)[asset];
      if (!assetPrice) {
        continue;
      }
      const assetInfo = balances[asset];
      balances[asset] = {
        amount: assetInfo.amount,
        usdValue: assetInfo.amount.times(assetPrice.value)
      };
    }
    return balances;
  };

  const fetchExchangeRates = async (): Promise<void> => {
    try {
      const { taskId } = await queryFiatExchangeRates(
        get(currencies).map(value => value.tickerSymbol)
      );

      const meta: TaskMeta = {
        title: t('actions.balances.exchange_rates.task.title').toString(),
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
        title: t('actions.balances.exchange_rates.error.title').toString(),
        message: t('actions.balances.exchange_rates.error.message', {
          message: e.message
        }).toString(),
        display: true
      });
    }
  };

  const exchangeRate = (
    currency: string
  ): ComputedRef<BigNumber | undefined> => {
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
      const { taskId } = await queryHistoricalRate(
        fromAsset,
        toAsset,
        timestamp
      );
      const { result } = await awaitTask<HistoricPrices, TaskMeta>(
        taskId,
        taskType,
        {
          title: t(
            'actions.balances.historic_fetch_price.task.title'
          ).toString(),
          description: t(
            'actions.balances.historic_fetch_price.task.description',
            {
              fromAsset,
              toAsset,
              date: convertFromTimestamp(timestamp)
            }
          ).toString(),
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
        message: t(
          'actions.balances.create_oracle_cache.already_running'
        ).toString()
      };
    }
    try {
      const { taskId } = await createPriceCache(
        source,
        fromAsset,
        toAsset,
        purgeOld
      );
      const { result } = await awaitTask<true, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.balances.create_oracle_cache.task', {
            fromAsset,
            toAsset,
            source
          }).toString(),
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
        message: t('actions.balances.create_oracle_cache.failed', {
          fromAsset,
          toAsset,
          source,
          error: e.message
        }).toString()
      };
    }
  };

  const toSelectedCurrency = (
    value: MaybeRef<BigNumber>
  ): ComputedRef<BigNumber> =>
    computed(() => {
      const mainCurrency = get(currencySymbol);
      const currentExchangeRate = get(exchangeRate(mainCurrency));
      const val = get(value);
      return currentExchangeRate ? val.multipliedBy(currentExchangeRate) : val;
    });

  const getAssetPrice = (asset: string): BigNumber | undefined => {
    return get(prices)[asset]?.value;
  };

  const reset = (): void => {
    set(prices, {});
    set(exchangeRates, {});
  };

  watch([exchangeRates, currencySymbol], ([a, b]) => {
    if (Object.keys(a).length > 0) {
      const rate = get(exchangeRate(b));
      if (!rate || rate.eq(0)) {
        notify({
          title: t('missing_exchange_rate.title').toString(),
          message: t('missing_exchange_rate.message').toString(),
          display: true
        });
      }
    }
  });

  return {
    prices,
    exchangeRates,
    getAssetPrice,
    fetchPrices,
    updateBalancesPrices,
    fetchExchangeRates,
    exchangeRate,
    getHistoricPrice,
    createOracleCache,
    getPriceCache,
    deletePriceCache,
    toSelectedCurrency,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useBalancePricesStore, import.meta.hot)
  );
}
