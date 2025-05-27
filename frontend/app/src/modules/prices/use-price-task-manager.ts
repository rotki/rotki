import type { ActionStatus } from '@/types/action';
import type { FetchPricePayload } from '@/types/blockchain/accounts';
import type { TaskMeta } from '@/types/task';
import { usePriceApi } from '@/composables/api/balances/price';
import { useStatusUpdater } from '@/composables/status';
import { useCollectionIdentifiers } from '@/modules/assets/use-collection-identifiers';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { CURRENCY_USD, type SupportedCurrency } from '@/types/currencies';
import { AssetPriceResponse, type HistoricPricePayload, HistoricPrices, type OracleCachePayload } from '@/types/prices';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { ExchangeRates } from '@/types/user';
import { isTaskCancelled } from '@/utils';
import { chunkArray } from '@/utils/data';
import { convertFromTimestamp } from '@/utils/date';
import { logger } from '@/utils/logging';
import { assert, type BigNumber, One } from '@rotki/common';

interface UsePriceTaskManagerReturn {
  createOracleCache: (payload: OracleCachePayload) => Promise<ActionStatus>;
  fetchExchangeRates: (symbol?: SupportedCurrency) => Promise<void>;
  fetchPrices: (payload: FetchPricePayload) => Promise<void>;
  getHistoricPrice: (payload: HistoricPricePayload) => Promise<BigNumber>;
  cacheEuroCollectionAssets: () => Promise<void>;
}

export function usePriceTaskManager(): UsePriceTaskManagerReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { euroCollectionAssets, euroCollectionAssetsLoaded, exchangeRates, prices } = storeToRefs(useBalancePricesStore());
  const {
    createPriceCache,
    queryFiatExchangeRates,
    queryHistoricalRate,
    queryPrices,
  } = usePriceApi();
  const { getCollectionAssets } = useCollectionIdentifiers();

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
      const priceBatches = chunkArray<string>([...payload.selectedAssets], 100);
      for (const batch of priceBatches) {
        await fetch(batch);
      }
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

  const fetchExchangeRates = async (symbol?: SupportedCurrency): Promise<void> => {
    try {
      const selectedCurrency = symbol ?? get(currencySymbol);

      const { taskId } = await queryFiatExchangeRates([selectedCurrency]);
      const { result } = await awaitTask<ExchangeRates, TaskMeta>(taskId, TaskType.EXCHANGE_RATES, {
        title: t('actions.balances.exchange_rates.task.title'),
      });

      const rates = ExchangeRates.parse(result);

      set(exchangeRates, {
        ...get(exchangeRates),
        ...rates,
      });

      const rate = rates[selectedCurrency];

      if (rate && rate.eq(0)) {
        notify({
          display: true,
          message: t('missing_exchange_rate.message'),
          title: t('missing_exchange_rate.title'),
        });
      }
    }
    catch (error: any) {
      if (isTaskCancelled(error)) {
        return;
      }
      notify({
        display: true,
        message: t('actions.balances.exchange_rates.error.message', {
          message: error.message,
        }),
        title: t('actions.balances.exchange_rates.error.title'),
      });
    }
  };

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

  async function cacheEuroCollectionAssets(): Promise<void> {
    if (get(euroCollectionAssetsLoaded)) {
      return;
    }
    try {
      const assets = await getCollectionAssets('240');
      set(euroCollectionAssets, assets);
      set(euroCollectionAssetsLoaded, true);
      logger.info(`${assets.length} Euro collection assets cached`);
    }
    catch (error: any) {
      logger.error(error);
    }
  }

  return {
    cacheEuroCollectionAssets,
    createOracleCache,
    fetchExchangeRates,
    fetchPrices,
    getHistoricPrice,
  };
}
