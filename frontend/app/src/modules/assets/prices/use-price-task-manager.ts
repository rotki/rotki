import type { FetchPricePayload } from '@/modules/accounts/blockchain-accounts';
import type { SupportedCurrency } from '@/modules/assets/amount-display/currencies';
import { type BigNumber, One } from '@rotki/common';
import { err, getOr, isErr, isOk, map as mapResult, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { type HistoricPricePayload, HistoricPrices, type OracleCachePayload } from '@/modules/assets/prices/price-types';
import { assetSetDigest, useFetchPrices } from '@/modules/assets/prices/use-fetch-prices';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { convertFromTimestamp } from '@/modules/core/common/data/date';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { Cancelled, onActionableError, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { ExchangeRates } from '@/modules/settings/types/user-settings';
import { useSetting } from '@/modules/settings/use-setting';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { PRICE_REFRESH_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { type RunBackendTask, useNativeTask } from '@/modules/task-center/use-native-task';

interface UsePriceTaskManagerReturn {
  /** Reports the outcome as its only message; a cancelled run reports nothing. */
  createOracleCache: (payload: OracleCachePayload) => Promise<Result<void, TaskError>>;
  fetchExchangeRates: (symbol?: SupportedCurrency) => Promise<void>;
  fetchPrices: (payload: FetchPricePayload) => Promise<void>;
  getHistoricPrice: (payload: HistoricPricePayload) => Promise<BigNumber>;
  refreshLatestPrices: (payload: FetchPricePayload, onFetched: () => void) => Promise<void>;
}

export function usePriceTaskManager(): UsePriceTaskManagerReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { statusOf, submitTask } = useNativeTask();
  const { notifyError, notifyInfo } = useNotifications();
  const { getAssetField } = useAssetInfoRetrieval();
  const currencySymbol = useSetting('currencySymbol');
  const { exchangeRates } = storeToRefs(useBalancePricesStore());
  const {
    createPriceCache,
    queryFiatExchangeRates,
    queryHistoricalRate,
  } = usePriceApi();
  const { fetchPrices, queryLatestPrices } = useFetchPrices();

  /**
   * The body of an exchange-rate fetch, run through `runTask` inside whichever activity calls it.
   *
   * @param runTask - the runner of the activity this is a stage of
   * @param selectedCurrency - the currency to fetch the rate of
   */
  const queryExchangeRates = async (runTask: RunBackendTask, selectedCurrency: SupportedCurrency): Promise<Result<void, TaskError>> => mapResult(
    await runTask<ExchangeRates>(
      async () => queryFiatExchangeRates([selectedCurrency]),
    ),
    (result) => {
      const rates = ExchangeRates.parse(result);
      set(exchangeRates, {
        ...get(exchangeRates),
        ...rates,
      });

      const rate = rates[selectedCurrency];
      if (rate?.eq(0))
        notifyError(t('missing_exchange_rate.title'), t('missing_exchange_rate.message'));
    },
  );

  const fetchExchangeRates = async (symbol?: SupportedCurrency): Promise<void> => {
    const selectedCurrency = symbol ?? get(currencySymbol);

    await submitTask({
      id: makeActivityId(ActivityKind.PRICES, ActivityPart.EXCHANGE_RATES),
      kind: ActivityKind.PRICES,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => queryExchangeRates(runTask, selectedCurrency),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.exchange_rates'), { currency: selectedCurrency }),
      title: t('task_center.group.prices'),
    });
  };

  /**
   * Refreshes the latest prices of `payload.selectedAssets` as one PRICES activity on
   * {@link PRICE_REFRESH_LANE}, then calls `onFetched` to apply them.
   *
   * @remarks
   * The lane runs one refresh at a time, so two overlapping refreshes cannot race their writes; one
   * asked for while another runs queues behind it, and one asked for again with the same assets
   * and mode joins the first. A queued refresh is the orchestrator's, so a logout drops it.
   *
   * With `ignoreCache` the exchange rates are a first stage of the same activity. A failed rate
   * fetch does not stop the prices, but the activity still reports it. Nothing is applied once
   * the activity is cancelled.
   *
   * The id ends in `balances` so it never joins a plain {@link fetchPrices} of the same set,
   * which neither fetches the rates nor applies anything.
   */
  const refreshLatestPrices = async (payload: FetchPricePayload, onFetched: () => void): Promise<void> => {
    const { ignoreCache, selectedAssets } = payload;
    const assetCount = selectedAssets.length;
    await submitTask({
      id: makeActivityId(ActivityKind.PRICES, ActivityPart.LATEST, assetSetDigest(selectedAssets), ignoreCache ? ActivityPart.PULL : ActivityPart.CACHED, ActivityPart.BALANCES),
      kind: ActivityKind.PRICES,
      lane: PRICE_REFRESH_LANE,
      rerunnable: true,
      run: async (context): Promise<Result<void, TaskError>> => {
        const rates = ignoreCache ? await queryExchangeRates(context.runTask, get(currencySymbol)) : ok(undefined);
        const latest = await queryLatestPrices(context, payload);
        if (context.cancelled())
          return err(Cancelled({ message: 'Price refresh cancelled' }));

        onFetched();
        return isErr(latest) ? latest : rates;
      },
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.latest'), { count: assetCount }, assetCount),
      title: t('task_center.group.prices'),
    });
  };

  const getHistoricPrice = async ({ fromAsset, timestamp, toAsset }: HistoricPricePayload): Promise<BigNumber> => {
    if (fromAsset === toAsset) {
      return One;
    }

    const outcome = await submitTask<BigNumber>({
      id: makeActivityId(ActivityKind.PRICES, ActivityPart.HISTORIC, fromAsset, toAsset, timestamp),
      kind: ActivityKind.PRICES,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<BigNumber, TaskError>> => mapResult(
        await runTask<HistoricPrices>(
          async () => queryHistoricalRate(fromAsset, toAsset, timestamp),
        ),
        result => HistoricPrices.parse(result).assets[fromAsset]?.[timestamp] ?? One.negated(),
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.historic'), { date: convertFromTimestamp(timestamp), fromAsset, toAsset }),
      title: t('task_center.group.prices'),
    });

    onActionableError(outcome, error => logger.error(error.message));

    return getOr(outcome, One.negated());
  };

  const buildOracleCache = async ({
    fromAsset,
    purgeOld,
    source,
    toAsset,
  }: OracleCachePayload): Promise<Result<void, TaskError>> => {
    if (statusOf(ActivityKind.PRICES, ActivityPart.ORACLE_CACHE).active)
      return err(TaskFailed({ message: t('actions.balances.create_oracle_cache.already_running') }));

    const cacheTitle = t('actions.balances.create_oracle_cache.task', {
      fromAsset,
      source,
      toAsset,
    });

    return submitTask({
      id: makeActivityId(ActivityKind.PRICES, ActivityPart.ORACLE_CACHE),
      kind: ActivityKind.PRICES,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<true>(
          async () => createPriceCache(source, fromAsset, toAsset, purgeOld),
        ),
        () => {},
      ),
      subtitle: cacheTitle,
      title: t('task_center.group.prices'),
    });
  };

  const createOracleCache = async (payload: OracleCachePayload): Promise<Result<void, TaskError>> => {
    const outcome = await buildOracleCache(payload);
    const title = t('oracle_prices.cache.notification.title');
    const pair = {
      fromAsset: getAssetField(payload.fromAsset, 'symbol'),
      source: payload.source,
      toAsset: getAssetField(payload.toAsset, 'symbol'),
    };

    if (isOk(outcome))
      notifyInfo(title, t('oracle_prices.cache.notification.success', pair));

    return outcome;
  };

  return {
    createOracleCache,
    fetchExchangeRates,
    fetchPrices,
    getHistoricPrice,
    refreshLatestPrices,
  };
}
