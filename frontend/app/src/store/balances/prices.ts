import type { ActionStatus } from '@/types/action';
import type { FetchPricePayload } from '@/types/blockchain/accounts';
import type { Balances } from '@/types/blockchain/balances';
import type { TaskMeta } from '@/types/task';
import type { MaybeRef } from '@vueuse/core';
import { usePriceApi } from '@/composables/api/balances/price';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useStatusUpdater } from '@/composables/status';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { CURRENCY_USD, useCurrencies } from '@/types/currencies';
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
import { isTaskCancelled } from '@/utils';
import { chunkArray } from '@/utils/data';
import { convertFromTimestamp } from '@/utils/date';
import { logger } from '@/utils/logging';
import { assert, type BigNumber, One } from '@rotki/common';

export const useBalancePricesStore = defineStore('balances/prices', () => {
  const prices = ref<AssetPrices>({});
  const exchangeRates = ref<ExchangeRates>({});

  const { awaitTask, isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { assetInfo } = useAssetInfoRetrieval();
  const { t } = useI18n();
  const {
    createPriceCache,
    deletePriceCache,
    getPriceCache,
    queryCachedPrices,
    queryFiatExchangeRates,
    queryHistoricalRate,
    queryPrices,
  } = usePriceApi();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { currencies } = useCurrencies();

  const assetPricesWithCurrentCurrency = ref<AssetPrices>({});

  const assetWithManualPrices = computed(() => Object.entries(prices.value)
    .filter(([, price]) => price.isManualPrice)
    .map(([asset]) => asset));

  watch([assetWithManualPrices, currencySymbol], async ([assets, symbol]) => {
    if (assets.length === 0)
      return;

    const data = await queryCachedPrices(assets, symbol);
    set(assetPricesWithCurrentCurrency, data);
  });

  const fetchPrices = async (payload: FetchPricePayload): Promise<void> => {
    const taskType = TaskType.UPDATE_PRICES;

    const fetch = async (assets: string[]): Promise<void> => {
      const { taskId } = await queryPrices(assets, CURRENCY_USD, payload.ignoreCache);

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
          display: true,
          message,
          title,
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
        usdValue: assetInfo.amount.times(assetPrice.value),
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
          display: true,
          message: t('actions.balances.exchange_rates.error.message', {
            message: error.message,
          }),
          title: t('actions.balances.exchange_rates.error.title'),
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
          description: t(
            'actions.balances.historic_fetch_price.task.description',
            {
              date: convertFromTimestamp(timestamp),
              fromAsset,
              toAsset,
            },
            1,
          ),
          title: t('actions.balances.historic_fetch_price.task.title'),
        },
        true,
      );

      const parsed = HistoricPrices.parse(result);
      return parsed.assets[fromAsset]?.[timestamp] ?? One.negated();
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
    if (isTaskRunning(taskType)) {
      return {
        message: t('actions.balances.create_oracle_cache.already_running'),
        success: false,
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
            source,
            toAsset,
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
          display: true,
          message: t('actions.balances.create_oracle_cache.error.message', {
            message: error.message,
          }),
          title: t('actions.balances.create_oracle_cache.error.title'),
        });
      }
      return {
        message: t('actions.balances.create_oracle_cache.failed', {
          error: error.message,
          fromAsset,
          source,
          toAsset,
        }),
        success: false,
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

  /**
   * @deprecated
   * TODO: Remove this immediately.
   * This is a hacky way to set EUR => EUR price and EURe => EUR price to 1.
   * @param {MaybeRef<string>} asset
   *
   */
  const isAssetPriceEqualToCurrentCurrency = (asset: MaybeRef<string>): ComputedRef<boolean> => computed(() => {
    const currency = get(currencySymbol);
    return get(asset) === currency || (currency === 'EUR' && get(assetInfo(asset))?.collectionId === '240');
  });

  /**
   * @deprecated
   * TODO: Remove this immediately.
   * Hacky way to prevent double conversion (try to replicate `match_main_currency` that has been removed)
   * @param {MaybeRef<string>} asset
   */
  const assetPrice = (asset: MaybeRef<string>): ComputedRef<BigNumber | undefined> =>
    computed(() => {
      if (get(isAssetPriceEqualToCurrentCurrency(asset)))
        return One;

      const assetVal = get(asset);

      return get(assetPricesWithCurrentCurrency)[assetVal]?.value ?? get(prices)[assetVal]?.value;
    });

  const isManualAssetPrice = (asset: MaybeRef<string>): ComputedRef<boolean> =>
    computed(() => get(prices)[get(asset)]?.isManualPrice || false);

  /**
   * @deprecated
   * TODO: Remove this immediately.
   * Hacky way to prevent double conversion (try to replicate `match_main_currency` that has been removed)
   * @param {MaybeRef<string>} asset
   */
  const isAssetPriceInCurrentCurrency = (asset: MaybeRef<string>): ComputedRef<boolean> =>
    computed(() => (get(isAssetPriceEqualToCurrentCurrency(asset)) || !!get(assetPricesWithCurrentCurrency)[get(asset)]?.value));

  watch([exchangeRates, currencySymbol], ([rates, symbol]) => {
    if (Object.keys(rates).length > 0) {
      const rate = get(exchangeRate(symbol));
      if (!rate || rate.eq(0)) {
        notify({
          display: true,
          message: t('missing_exchange_rate.message'),
          title: t('missing_exchange_rate.title'),
        });
      }
    }
  });

  return {
    assetPrice,
    createOracleCache,
    deletePriceCache,
    exchangeRate,
    exchangeRates,
    fetchExchangeRates,
    fetchPrices,
    getHistoricPrice,
    getPriceCache,
    isAssetPriceInCurrentCurrency,
    isManualAssetPrice,
    prices,
    toSelectedCurrency,
    updateBalancesPrices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalancePricesStore, import.meta.hot));
