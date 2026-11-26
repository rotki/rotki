import type { AllBalancePayload } from '@/modules/accounts/blockchain-accounts';
import type { ActivityId } from '@/modules/task-center/core/types';
import { err, map as mapResult, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { useBalancesApi } from '@/modules/balances/api/use-balances-api';
import { allBalancesActivity, allBalancesLoginActivity } from '@/modules/balances/balances.activity';
import { useSnapshotSchedule } from '@/modules/balances/use-snapshot-schedule';
import { Skipped, type TaskError } from '@/modules/core/tasks/task-result';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseAllBalancesQueryReturn {
  /** Submits the all-balances snapshot query; `ignoreErrors` is named in the task's subtitle. */
  fetchBalances: (payload?: Partial<AllBalancePayload>) => Promise<void>;
  queueSnapshot: (chainIds: ActivityId[], parent: ActivityId | undefined) => Promise<void>;
}

/**
 * The all-balances snapshot query, the one that aggregates every source and may save a snapshot.
 */
export function useAllBalancesQuery(): UseAllBalancesQueryReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { queryBalancesAsync } = useBalancesApi();
  const { submitTask } = useNativeTask();
  const { isSnapshotDue } = useSnapshotSchedule();

  const fetchBalances = async (payload: Partial<AllBalancePayload> = {}): Promise<void> => {
    const description = payload.ignoreErrors
      ? `${t('actions.balances.all_balances.task.description')} ${t('actions.balances.all_balances.task.ignore_errors_note')}`
      : t('actions.balances.all_balances.task.description');

    // Singleton all-balances snapshot query; liveness is read off the orchestrator.
    await submitTask({
      id: allBalancesActivity.id(),
      kind: allBalancesActivity.kind,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask(async () => queryBalancesAsync(payload)),
        () => {},
      ),
      subtitle: description,
      title: t('task_center.group.all_balances'),
    });
  };

  /**
   * Submits the login load's snapshot query, to run once every chain job in `chainIds` settled.
   *
   * @remarks
   * Declared with the chains rather than submitted after them, so the batch owns it from the start:
   * a logout drops it before it runs, and cancelling the batch cancels it. The aggregate query must
   * never run alongside the chain queries: querying while they were still repopulating chains is
   * what wrote 0-value rows into the net-worth history.
   *
   * Its own id, {@link allBalancesLoginActivity} rather than the bare one, so a forced save during the load is a second query
   * rather than a join onto this one. It carries no payload on purpose: the backend saves when
   * `requested_save_data or should_save_balances(...)`, so this asks for a snapshot rather than
   * forcing one. The schedule is read again when it runs, since the chains can take long enough for
   * a snapshot to have been saved meanwhile.
   */
  const queueSnapshot = async (chainIds: ActivityId[], parent: ActivityId | undefined): Promise<void> => {
    await submitTask({
      deps: chainIds,
      id: allBalancesLoginActivity.id(),
      kind: allBalancesLoginActivity.kind,
      parent,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => {
        if (!(await isSnapshotDue()))
          return err(Skipped({ message: t('actions.balances.all_balances.skipped.not_due') }));

        return mapResult(await runTask(async () => queryBalancesAsync({})), () => {});
      },
      subtitle: t('actions.balances.all_balances.task.description'),
      title: t('task_center.group.all_balances'),
    });
  };

  return {
    fetchBalances,
    queueSnapshot,
  };
}
