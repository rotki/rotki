import type { AllBalancePayload } from '@/modules/accounts/blockchain-accounts';
import { startPromise } from '@shared/utils';
import { map as mapResult, type Result } from 'plainfp/result';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { useBalancesApi } from '@/modules/balances/api/use-balances-api';
import { useAutoTokenDetection } from '@/modules/balances/blockchain/use-auto-token-detection';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

export const useBalanceFetching = createSharedComposable(() => {
  const { fetchManualBalances } = useManualBalances();
  const { fetchConnectedExchangeBalances } = useExchanges();
  const { fetchAccounts } = useBlockchainAccountManagement();
  const { queryBalancesAsync } = useBalancesApi();
  const { fetchExchangeRates } = usePriceTaskManager();
  const { refreshPrices } = usePriceRefresh();
  const { notifyError } = useNotifications();
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });
  const { fetchNetValue } = useStatisticsDataFetching();
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const { skipReason: autoDetectSkipReason, withDetection } = useAutoTokenDetection();

  const fetchBalances = async (payload: Partial<AllBalancePayload> = {}): Promise<void> => {
    const description = payload.ignoreErrors
      ? `${t('actions.balances.all_balances.task.description')} ${t('actions.balances.all_balances.task.ignore_errors_note')}`
      : t('actions.balances.all_balances.task.description');

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.ALL_BALANCES),
      kind: ActivityKind.ALL_BALANCES,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask(async () => queryBalancesAsync(payload)),
        () => {},
      ),
      subtitle: description,
      title: t('task_center.group.all_balances'),
    });

    onActionableError(outcome, error => notifyError(
      t('actions.balances.all_balances.error.title'),
      t('actions.balances.all_balances.error.message', {
        message: error.message,
      }),
    ));
  };

  /**
   * Reads what is already stored: exchange rates, then manual balances, the account walk and the
   * connected exchanges together. `fetchAccounts` hydrates each chain from cache as its accounts
   * land, so nothing here goes to a node.
   */
  const fetchCached = async (): Promise<void> => {
    await fetchExchangeRates();
    await Promise.allSettled([fetchManualBalances(), fetchAccounts({ refreshEns: true }), fetchConnectedExchangeBalances()]);
  };

  /**
   * Re-queries every chain from its nodes, detecting tokens first when detection is due.
   *
   * @remarks
   * Nothing here may ask for a snapshot: `GET /balances` can persist one, and the per-chain queries
   * are still clearing and repopulating chains, so it would record a 0-value row in the user's
   * net-worth history. A scheduled snapshot has to wait until every chain is terminal. Explicit
   * user snapshots go through {@link fetchBalances}.
   */
  const refreshFromChain = async (): Promise<void> => withDetection(async (detect) => {
    logger.debug(detect
      ? 'refreshFromChain: detect-then-query, every chain'
      : `refreshFromChain: query only (${autoDetectSkipReason() ?? 'unknown'}), every chain`);

    await refreshBlockchainBalances({}, RefreshMode.BACKGROUND, { detect });
  });

  const fetch = async (): Promise<void> => {
    await fetchCached();
    startPromise(refreshFromChain());
  };

  /**
   * The periodic tick: every chain, entering at the chain job, without detection.
   *
   * @remarks
   * This costs network calls on a timer, which is why it sits behind a setting the user turns on.
   * `refreshPeriod` defaults to `-1` and the scheduler only starts while it is positive. A chain
   * still mid-refresh is skipped rather than queued, so ticks cannot pile up.
   */
  const autoRefresh = async (): Promise<void> => {
    await Promise.allSettled([
      fetchManualBalances(),
      fetchAccounts({ refreshEns: true }),
      fetchConnectedExchangeBalances(),
      fetchNetValue(),
    ]);

    await Promise.allSettled([
      refreshBlockchainBalances({}, RefreshMode.PERIODIC),
      refreshPrices(true),
    ]);
  };

  return {
    autoRefresh,
    fetch,
    fetchBalances,
    fetchCached,
    refreshFromChain,
  };
});
