import type { ActionStatus } from '@/types/action';
import type { FetchPricePayload } from '@/types/blockchain/accounts';
import type { SupportedCurrency } from '@/types/currencies';
import type { TaskMeta } from '@/types/task';
import { type BigNumber, One } from '@rotki/common';
import { usePriceApi } from '@/composables/api/balances/price';
import { useStatusUpdater } from '@/composables/status';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { AssetPriceResponse, type HistoricPricePayload, HistoricPrices, type OracleCachePayload } from '@/types/prices';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { ExchangeRates } from '@/types/user';
import { isTaskCancelled } from '@/utils';
import { chunkArray } from '@/utils/data';
import { convertFromTimestamp } from '@/utils/date';
import { logger } from '@/utils/logging';

interface UsePriceTaskManagerReturn {
  createOracleCache: (payload: OracleCachePayload) => Promise<ActionStatus>;
  fetchExchangeRates: (symbol?: SupportedCurrency) => Promise<void>;
  fetchPrices: (payload: FetchPricePayload) => Promise<void>;
  getHistoricPrice: (payload: HistoricPricePayload) => Promise<BigNumber>;
}

export function usePriceTaskManager(): UsePriceTaskManagerReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { notifyError } = useNotifications();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { exchangeRates, prices } = storeToRefs(useBalancePricesStore());
  const {
    createPriceCache,
    queryFiatExchangeRates,
    queryHistoricalRate,
    queryPrices,
  } = usePriceApi();

  const fetchPrices = async (payload: FetchPricePayload): Promise<void> => {
    const taskType = TaskType.UPDATE_PRICES;

    const fetch = async (assets: string[]): Promise<void> => {
      const { taskId } = await queryPrices(assets, get(currencySymbol), payload.ignoreCache);
      const { result } = await awaitTask<AssetPriceResponse, TaskMeta>(
        taskId,
        taskType,
        {
          description: t('actions.session.fetch_prices.task.description', { count: assets.length }, assets.length),
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
    catch (error: unknown) {
      if (!isTaskCancelled(error)) {
        const title = t('actions.session.fetch_prices.error.title');
        const message = t('actions.session.fetch_prices.error.message', {
          error: getErrorMessage(error),
        });
        notifyError(title, message);
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
        notifyError(t('missing_exchange_rate.title'), t('missing_exchange_rate.message'));
      }
    }
    catch (error: unknown) {
      if (isTaskCancelled(error)) {
        return;
      }
      notifyError(
        t('actions.balances.exchange_rates.error.title'),
        t('actions.balances.exchange_rates.error.message', {
          message: getErrorMessage(error),
        }),
      );
    }
  };

  const getHistoricPrice = async ({ fromAsset, timestamp, toAsset }: HistoricPricePayload): Promise<BigNumber> => {
    if (fromAsset === toAsset) {
      return One;
    }
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
    catch (error: unknown) {
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
    catch (error: unknown) {
      const message = getErrorMessage(error);
      if (!isTaskCancelled(error)) {
        notifyError(
          t('actions.balances.create_oracle_cache.error.title'),
          t('actions.balances.create_oracle_cache.error.message', {
            message,
          }),
        );
      }
      return {
        message: t('actions.balances.create_oracle_cache.failed', {
          error: message,
          fromAsset,
          source,
          toAsset,
        }),
        success: false,
      };
    }
  };

  return {
    createOracleCache,
    fetchExchangeRates,
    fetchPrices,
    getHistoricPrice,
  };
}
