import type { ExchangeBalancePayload } from '@/modules/accounts/blockchain-accounts';
import { toSentenceCase } from '@rotki/common';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { err, flatMap as flatMapResult, ok, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { msg } from '@/message-key';
import { useValueThreshold } from '@/modules/assets/amount-display/use-usd-value-threshold';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { exchangeBalancesActivity } from '@/modules/balances/balances.activity';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { ExchangeBalancesResponse } from '@/modules/balances/types/balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { FailureCause, isRetryableCause, parseFailureCause } from '@/modules/core/api/failure-cause';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseExchangeBalancesQueryReturn {
  fetchExchangeBalances: (payload: ExchangeBalancePayload) => Promise<void>;
}

/**
 * The cause a location's failed connections report together.
 *
 * @remarks
 * A rerun queries every connection of the location, so a retry is worth offering as soon as one of
 * them could heal, even beside one that needs a new key.
 */
function locationFailureCause(causes: string[]): FailureCause {
  const parsed = causes.map(parseFailureCause);
  return parsed.find(isRetryableCause) ?? parsed[0] ?? FailureCause.UNKNOWN;
}

/**
 * Queries an exchange location's balances as a task center activity and writes them to the store.
 */
export function useExchangeBalancesQuery(): UseExchangeBalancesQueryReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { submitTask } = useNativeTask();
  const { exchangeAccountBalances, exchangeBalances, exchangeFailedAccounts } = storeToRefs(useBalancesStore());
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());
  const { queryExchangeBalances } = useExchangeApi();
  const valueThreshold = useValueThreshold(BalanceSource.EXCHANGES);

  /**
   * Refreshes one exchange's balances.
   *
   * @remarks
   * One native activity per location, {@link exchangeBalancesActivity}, so liveness and freshness
   * are read off the orchestrator: by its kind for all of them, or by its parts for one.
   *
   * A connection that failed is missing from the location's totals, which would then understate
   * the holdings. Successful accounts update, but failed accounts and location totals stay in place.
   */
  const fetchExchangeBalances = async (payload: ExchangeBalancePayload): Promise<void> => {
    const { ignoreCache, location } = payload;
    const threshold = get(valueThreshold);

    await submitTask({
      id: exchangeBalancesActivity.id({ location }),
      kind: exchangeBalancesActivity.kind,
      lane: exchangeBalancesActivity.laneOf?.({ location }),
      rerunnable: true,
      run: async ({ rerun, runTask }): Promise<Result<void, TaskError>> => flatMapResult(
        await runTask<ExchangeBalancesResponse>(
          async () => queryExchangeBalances(location, rerun || ignoreCache === true, threshold),
        ),
        (result): Result<void, TaskError> => {
          const { failedAccounts, perAccount, totals } = ExchangeBalancesResponse.parse(result);
          const failedConnections = Object.entries(failedAccounts?.[location] ?? {});
          const failures = failedConnections.map(([identifier, { message }]) => {
            const connection = get(connectedExchanges).find(exchange => exchange.identifier === identifier);
            return `${connection?.name ?? identifier}: ${message}`;
          });
          set(exchangeAccountBalances, {
            ...get(exchangeAccountBalances),
            [location]: failures.length > 0
              ? { ...get(exchangeAccountBalances)[location], ...perAccount[location] }
              : perAccount[location] ?? {},
          });
          set(exchangeFailedAccounts, {
            ...get(exchangeFailedAccounts),
            [location]: Object.fromEntries(failedConnections.map(([identifier, { message }]) => [identifier, message])),
          });
          if (failures.length > 0) {
            return err(TaskFailed({
              failureCause: locationFailureCause(failedConnections.map(([, { cause }]) => cause)),
              message: failures.join(' '),
            }));
          }

          set(exchangeBalances, {
            ...get(exchangeBalances),
            [location]: totals[location] ?? {},
          });
          return ok(undefined);
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.exchange_balances.query'), { location: toSentenceCase(location) }),
      title: t('task_center.group.exchange_balances'),
    });
  };

  return { fetchExchangeBalances };
}
