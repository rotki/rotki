import type { FetchPricePayload } from '@/modules/accounts/blockchain-accounts';
import type { SupportedCurrency } from '@/modules/assets/amount-display/currencies';
import type { ActionStatus } from '@/modules/core/common/action';
import { type BigNumber, One } from '@rotki/common';
import { getOr, isErr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { type HistoricPricePayload, HistoricPrices, type OracleCachePayload } from '@/modules/assets/prices/price-types';
import { useFetchPrices } from '@/modules/assets/prices/use-fetch-prices';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { convertFromTimestamp } from '@/modules/core/common/data/date';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { ExchangeRates } from '@/modules/settings/types/user-settings';
import { useSetting } from '@/modules/settings/use-setting';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UsePriceTaskManagerReturn {
  createOracleCache: (payload: OracleCachePayload) => Promise<ActionStatus>;
  fetchExchangeRates: (symbol?: SupportedCurrency) => Promise<void>;
  fetchPrices: (payload: FetchPricePayload) => Promise<void>;
  getHistoricPrice: (payload: HistoricPricePayload) => Promise<BigNumber>;
}

export function usePriceTaskManager(): UsePriceTaskManagerReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { statusOf, submitTask } = useNativeTask();
  const { notifyError } = useNotifications();
  const currencySymbol = useSetting('currencySymbol');
  const { exchangeRates } = storeToRefs(useBalancePricesStore());
  const {
    createPriceCache,
    queryFiatExchangeRates,
    queryHistoricalRate,
  } = usePriceApi();
  // Latest-price fetching runs as a native orchestrator activity; see use-fetch-prices.
  const { fetchPrices } = useFetchPrices();

  const fetchExchangeRates = async (symbol?: SupportedCurrency): Promise<void> => {
    const selectedCurrency = symbol ?? get(currencySymbol);

    // One native PRICES activity (`prices:exchange-rates`); liveness is read off the orchestrator.
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.PRICES, ActivityPart.EXCHANGE_RATES),
      kind: ActivityKind.PRICES,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
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
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.exchange_rates'), { currency: selectedCurrency }),
      title: t('task_center.group.prices'),
    });

    onActionableError(outcome, error => notifyError(
      t('actions.balances.exchange_rates.error.title'),
      t('actions.balances.exchange_rates.error.message', { message: error.message }),
    ));
  };

  const getHistoricPrice = async ({ fromAsset, timestamp, toAsset }: HistoricPricePayload): Promise<BigNumber> => {
    if (fromAsset === toAsset) {
      return One;
    }

    // One native PRICES activity per (fromAsset, toAsset, timestamp). The id must carry all
    // three: `submitTask` dedups by id, so a shared id would hand two distinct queries the same
    // promise and return one the other's price. Readers aggregate with `useWorkStatusPrefix`.
    //
    // The price is the activity's *return value*, not a variable in this closure. Two identical
    // concurrent lookups legitimately dedup onto one activity, and the second caller's `run`
    // never executes — reading a local left it at `One.negated()`, which
    // `use-snapshot-asset-price.ts` treats as "no historic price" and silently replaces with
    // `usdValue/amount`. A fabricated price is worse than a slow one.
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

  const createOracleCache = async ({
    fromAsset,
    purgeOld,
    source,
    toAsset,
  }: OracleCachePayload): Promise<ActionStatus> => {
    // Single shared id ⇒ only one oracle-cache build at a time, preserving the old type-wide guard.
    if (statusOf(ActivityKind.PRICES, ActivityPart.ORACLE_CACHE).active) {
      return {
        message: t('actions.balances.create_oracle_cache.already_running'),
        success: false,
      };
    }

    const cacheTitle = t('actions.balances.create_oracle_cache.task', {
      fromAsset,
      source,
      toAsset,
    });

    const outcome = await submitTask({
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

    if (isErr(outcome)) {
      if (isActionable(outcome.error)) {
        notifyError(
          t('actions.balances.create_oracle_cache.error.title'),
          t('actions.balances.create_oracle_cache.error.message', {
            message: outcome.error.message,
          }),
        );
      }

      return {
        message: t('actions.balances.create_oracle_cache.failed', {
          error: outcome.error.message,
          fromAsset,
          source,
          toAsset,
        }),
        success: false,
      };
    }

    return { success: true };
  };

  return {
    createOracleCache,
    fetchExchangeRates,
    fetchPrices,
    getHistoricPrice,
  };
}
