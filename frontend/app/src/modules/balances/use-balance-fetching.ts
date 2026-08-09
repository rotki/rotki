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

    // Singleton all-balances snapshot query; liveness is read off the orchestrator.
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
   * ⭐ `fetchAccounts`, not `refreshAccounts`. Passing no chain made the latter an accounts read and
   * nothing else — both halves of its balance decision need one — so the name promised work it
   * never did here. Each chain's hydration still happens inside the walk, as its accounts land.
   */
  const fetchCached = async (): Promise<void> => {
    await fetchExchangeRates();
    await Promise.allSettled([fetchManualBalances(), fetchAccounts({ refreshEns: true }), fetchConnectedExchangeBalances()]);
  };

  /**
   * ⭐ A refresh never snapshots. It used to end in `fetchBalances()` with an empty payload —
   * `GET /balances` reads the shared in-memory balances and persists on the backend's own
   * schedule, so a refresh was implicitly asking for a snapshot while its own per-chain queries
   * were still clearing and repopulating chains. That is how a 0-value row could reach the user's
   * net-worth history, and it forced the whole refresh to be ordered around it.
   *
   * Nothing is lost by dropping it: the backend takes automatic snapshots itself
   * (`tasks/manager.py::_maybe_update_snapshot_balances`, which checks `balance_save_frequency`,
   * runs `maybe_detect_new_tokens` first and passes `requested_save_data=True`). Explicit user
   * snapshots go through {@link fetchBalances} from `forceSave`, which is unchanged.
   *
   * ⚠️ The result of that call was discarded anyway (`mapResult(…, () => {})`) — it was only ever
   * made for the backend side effect, never for data this app reads.
   */
  const refreshFromChain = async (): Promise<void> => withDetection(async (detect) => {
    logger.debug(detect
      ? 'refreshFromChain: detect-then-query, every chain'
      : `refreshFromChain: query only (${autoDetectSkipReason() ?? 'unknown'}), every chain`);

    // ⭐ One call for every chain, detecting or not. This used to split into "fire detection for
    // the EVM chains and separately refresh the non-EVM ones", because detection ended in its own
    // balance read and refreshing an EVM chain as well would have queried it twice. With detection
    // a stage *inside* the chain job that reads its result, a chain is one job either way and the
    // split has nothing left to express — a chain that cannot hold tokens simply has no detect
    // stage.
    await refreshBlockchainBalances({}, 'background', { detect });
  });

  const fetch = async (): Promise<void> => {
    await fetchCached();
    startPromise(refreshFromChain());
  };

  /**
   * §6's periodic flow: every chain, entering at the job, no detection.
   *
   * 🔴 The tick never asked a chain anything. It passed `{ periodic: true }` to `refreshAccounts`,
   * whose no-chain branch is a *cached* read — the DB, not the network — so "Automatic balance
   * refresh" re-read balances the backend had already written on its own schedule and never
   * triggered a query itself. The `periodic` refresh mode, the one that settles SKIPPED on a busy
   * chain rather than joining it, had no caller that could reach it at all.
   *
   * ⚠️ This does now cost network calls on a timer, which is why it belongs behind a setting the
   * user turns on: `refreshPeriod` defaults to `-1` and the scheduler only starts when it is
   * positive. A chain still mid-refresh is skipped rather than queued, so ticks cannot pile up.
   */
  const autoRefresh = async (): Promise<void> => {
    await Promise.allSettled([
      fetchManualBalances(),
      fetchAccounts({ refreshEns: true }),
      fetchConnectedExchangeBalances(),
      fetchNetValue(),
    ]);

    await Promise.allSettled([
      refreshBlockchainBalances({}, 'periodic'),
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
