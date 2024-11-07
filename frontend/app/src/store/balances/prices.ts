import { useCurrencies } from '@/types/currencies';
import {
  AssetPriceResponse,
  type AssetPrices,
  type HistoricPricePayload,
  HistoricPrices,
  type OracleCachePayload,
} from '@/types/prices';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { ExchangeRates } from '@/types/user';
import type { TaskMeta } from '@/types/task';
import type { Balances } from '@/types/blockchain/balances';
import type { MaybeRef } from '@vueuse/core';
import type { BigNumber } from '@rotki/common';
import type { ActionStatus } from '@/types/action';
import type { FetchPricePayload } from '@/types/blockchain/accounts';

export const useBalancePricesStore = defineStore('balances/prices', () => {
  const prices = ref<AssetPrices>({});
  const exchangeRates = ref<ExchangeRates>({});

  const { awaitTask, isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { t } = useI18n();
  const {
    getPriceCache,
    createPriceCache,
    deletePriceCache,
    queryHistoricalRate,
    queryFiatExchangeRates,
    queryPrices,
  } = usePriceApi();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { currencies } = useCurrencies();

  const fetchPrices = async (payload: FetchPricePayload): Promise<void> => {
    const taskType = TaskType.UPDATE_PRICES;

    const fetch = async (assets: string[]): Promise<void> => {
      const { taskId } = await queryPrices(assets, get(currencySymbol), payload.ignoreCache);

      const { result } = await awaitTask<AssetPriceResponse, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.session.fetch_prices.task.title'),
        },
        true,
      );

      set(prices, {
        ...get(prices),
        ...AssetPriceResponse.parse(result),
      });
    };

    const { setStatus } = useStatusUpdater(Section.PRICES);

    try {
      setStatus(Status.LOADING);
      await Promise.all(chunkArray<string>(payload.selectedAssets, 100).map(fetch));
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const title = t('actions.session.fetch_prices.error.title');
        const message = t('actions.session.fetch_prices.error.message', {
          error: error.message,
        });
        notify({
          title,
          message,
          display: true,
        });
      }
    }
    finally {
      setStatus(Status.LOADED);
    }
  };

  const updateBalancesPrices = (balances: Balances): Balances => {
    for (const asset in balances) {
      const assetPrice = get(prices)[asset];
      if (!assetPrice)
        continue;

      const assetInfo = balances[asset];
      balances[asset] = {
        amount: assetInfo.amount,
        value: assetInfo.amount.times(assetPrice.value),
      };
    }
    return balances;
  };

  const fetchExchangeRates = async (): Promise<void> => {
    try {
      const { taskId } = await queryFiatExchangeRates(get(currencies).map(value => value.tickerSymbol));

      const meta: TaskMeta = {
        title: t('actions.balances.exchange_rates.task.title'),
      };

      const { result } = await awaitTask<ExchangeRates, TaskMeta>(taskId, TaskType.EXCHANGE_RATES, meta);

      set(exchangeRates, ExchangeRates.parse(result));
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          title: t('actions.balances.exchange_rates.error.title'),
          message: t('actions.balances.exchange_rates.error.message', {
            message: error.message,
          }),
          display: true,
        });
      }
    }
  };

  const exchangeRate = (currency: string): ComputedRef<BigNumber | undefined> =>
    computed(() => get(exchangeRates)[currency]);

  const getHistoricPrice = async ({ fromAsset, timestamp, toAsset }: HistoricPricePayload): Promise<BigNumber> => {
    assert(fromAsset !== toAsset);
    const taskType = TaskType.FETCH_HISTORIC_PRICE;

    try {
      const { taskId } = await queryHistoricalRate(fromAsset, toAsset, timestamp);
      const { result } = await awaitTask<HistoricPrices, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.balances.historic_fetch_price.task.title'),
          description: t(
            'actions.balances.historic_fetch_price.task.description',
            {
              fromAsset,
              toAsset,
              date: convertFromTimestamp(timestamp),
            },
            1,
          ),
        },
        true,
      );

      const parsed = HistoricPrices.parse(result);
      return parsed.assets[fromAsset][timestamp];
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        logger.error(error);

      return One.negated();
    }
  };

  const createOracleCache = async ({
    fromAsset,
    purgeOld,
    source,
    toAsset,
  }: OracleCachePayload): Promise<ActionStatus> => {
    const taskType = TaskType.CREATE_PRICE_CACHE;
    if (get(isTaskRunning(taskType))) {
      return {
        success: false,
        message: t('actions.balances.create_oracle_cache.already_running'),
      };
    }
    try {
      const { taskId } = await createPriceCache(source, fromAsset, toAsset, purgeOld);
      const { result } = await awaitTask<true, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.balances.create_oracle_cache.task', {
            fromAsset,
            toAsset,
            source,
          }),
        },
        true,
      );

      return {
        success: result,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          title: t('actions.balances.create_oracle_cache.error.title'),
          message: t('actions.balances.create_oracle_cache.error.message', {
            message: error.message,
          }),
          display: true,
        });
      }
      return {
        success: false,
        message: t('actions.balances.create_oracle_cache.failed', {
          fromAsset,
          toAsset,
          source,
          error: error.message,
        }),
      };
    }
  };

  const toSelectedCurrency = (value: MaybeRef<BigNumber>): ComputedRef<BigNumber> =>
    computed(() => {
      const mainCurrency = get(currencySymbol);
      const currentExchangeRate = get(exchangeRate(mainCurrency));
      const val = get(value);
      return currentExchangeRate ? val.multipliedBy(currentExchangeRate) : val;
    });

  const assetPrice = (asset: MaybeRef<string>): ComputedRef<BigNumber | undefined> =>
    computed(() => get(prices)[get(asset)]?.value);

  const isManualAssetPrice = (asset: MaybeRef<string>): ComputedRef<boolean> =>
    computed(() => get(prices)[get(asset)]?.isManualPrice || false);

  watch([exchangeRates, currencySymbol], ([rates, symbol]) => {
    if (Object.keys(rates).length > 0) {
      const rate = get(exchangeRate(symbol));
      if (!rate || rate.eq(0)) {
        notify({
          title: t('missing_exchange_rate.title'),
          message: t('missing_exchange_rate.message'),
          display: true,
        });
      }
    }
  });

  return {
    prices,
    exchangeRates,
    assetPrice,
    fetchPrices,
    updateBalancesPrices,
    fetchExchangeRates,
    exchangeRate,
    getHistoricPrice,
    createOracleCache,
    getPriceCache,
    deletePriceCache,
    toSelectedCurrency,
    isManualAssetPrice,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalancePricesStore, import.meta.hot));
