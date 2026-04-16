import type { FetchPricePayload } from '@/modules/accounts/blockchain-accounts';
import type { SupportedCurrency } from '@/modules/amount-display/currencies';
import type { ActionStatus } from '@/modules/common/action';
import type { TaskMeta } from '@/modules/tasks/types';
import { type BigNumber, One } from '@rotki/common';
import { usePriceApi } from '@/composables/api/balances/price';
import { useStatusUpdater } from '@/composables/status';
import { chunkArray } from '@/modules/common/data/data';
import { convertFromTimestamp } from '@/modules/common/data/date';
import { logger } from '@/modules/common/logging/logging';
import { Section, Status } from '@/modules/common/status';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { AssetPriceResponse, type HistoricPricePayload, HistoricPrices, type OracleCachePayload } from '@/modules/prices/price-types';
import { ExchangeRates } from '@/modules/settings/types/user-settings';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { useTaskStore } from '@/modules/tasks/use-task-store';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';

interface UsePriceTaskManagerReturn {
  createOracleCache: (payload: OracleCachePayload) => Promise<ActionStatus>;
  fetchExchangeRates: (symbol?: SupportedCurrency) => Promise<void>;
  fetchPrices: (payload: FetchPricePayload) => Promise<void>;
  getHistoricPrice: (payload: HistoricPricePayload) => Promise<BigNumber>;
}

export function usePriceTaskManager(): UsePriceTaskManagerReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { runTask } = useTaskHandler();
  const { isTaskRunning } = useTaskStore();
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
    const fetch = async (assets: string[]): Promise<void> => {
      const outcome = await runTask<AssetPriceResponse, TaskMeta>(
        async () => queryPrices(assets, get(currencySymbol), payload.ignoreCache),
        {
          type: TaskType.UPDATE_PRICES,
          meta: {
            description: t('actions.session.fetch_prices.task.description', { count: assets.length }, assets.length),
            title: t('actions.session.fetch_prices.task.title'),
          },
          unique: false,
        },
      );

      if (outcome.success) {
        set(prices, {
          ...get(prices),
          ...AssetPriceResponse.parse(outcome.result),
        });
      }
      else if (isActionableFailure(outcome)) {
        throw new Error(outcome.message);
      }
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
      const title = t('actions.session.fetch_prices.error.title');
      const message = t('actions.session.fetch_prices.error.message', {
        error: getErrorMessage(error),
      });
      notifyError(title, message);
    }
    finally {
      setStatus(Status.LOADED);
    }
  };

  const fetchExchangeRates = async (symbol?: SupportedCurrency): Promise<void> => {
    const selectedCurrency = symbol ?? get(currencySymbol);

    const outcome = await runTask<ExchangeRates, TaskMeta>(
      async () => queryFiatExchangeRates([selectedCurrency]),
      { type: TaskType.EXCHANGE_RATES, meta: { title: t('actions.balances.exchange_rates.task.title') } },
    );

    if (outcome.success) {
      const rates = ExchangeRates.parse(outcome.result);

      set(exchangeRates, {
        ...get(exchangeRates),
        ...rates,
      });

      const rate = rates[selectedCurrency];

      if (rate && rate.eq(0)) {
        notifyError(t('missing_exchange_rate.title'), t('missing_exchange_rate.message'));
      }
    }
    else if (isActionableFailure(outcome)) {
      notifyError(
        t('actions.balances.exchange_rates.error.title'),
        t('actions.balances.exchange_rates.error.message', {
          message: outcome.message,
        }),
      );
    }
  };

  const getHistoricPrice = async ({ fromAsset, timestamp, toAsset }: HistoricPricePayload): Promise<BigNumber> => {
    if (fromAsset === toAsset) {
      return One;
    }

    const outcome = await runTask<HistoricPrices, TaskMeta>(
      async () => queryHistoricalRate(fromAsset, toAsset, timestamp),
      {
        type: TaskType.FETCH_HISTORIC_PRICE,
        meta: {
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
        unique: false,
      },
    );

    if (outcome.success) {
      const parsed = HistoricPrices.parse(outcome.result);
      return parsed.assets[fromAsset]?.[timestamp] ?? One.negated();
    }

    if (isActionableFailure(outcome))
      logger.error(outcome.error);

    return One.negated();
  };

  const createOracleCache = async ({
    fromAsset,
    purgeOld,
    source,
    toAsset,
  }: OracleCachePayload): Promise<ActionStatus> => {
    if (isTaskRunning(TaskType.CREATE_PRICE_CACHE)) {
      return {
        message: t('actions.balances.create_oracle_cache.already_running'),
        success: false,
      };
    }

    const outcome = await runTask<true, TaskMeta>(
      async () => createPriceCache(source, fromAsset, toAsset, purgeOld),
      {
        type: TaskType.CREATE_PRICE_CACHE,
        meta: {
          title: t('actions.balances.create_oracle_cache.task', {
            fromAsset,
            source,
            toAsset,
          }),
        },
        guard: false,
        unique: false,
      },
    );

    if (outcome.success) {
      return { success: outcome.result };
    }

    if (isActionableFailure(outcome)) {
      notifyError(
        t('actions.balances.create_oracle_cache.error.title'),
        t('actions.balances.create_oracle_cache.error.message', {
          message: outcome.message,
        }),
      );
    }

    return {
      message: t('actions.balances.create_oracle_cache.failed', {
        error: outcome.message,
        fromAsset,
        source,
        toAsset,
      }),
      success: false,
    };
  };

  return {
    createOracleCache,
    fetchExchangeRates,
    fetchPrices,
    getHistoricPrice,
  };
}
