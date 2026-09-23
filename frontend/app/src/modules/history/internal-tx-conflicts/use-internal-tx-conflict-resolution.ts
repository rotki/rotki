import type { Ref } from 'vue';
import type { InternalTxConflict } from './types';
import { Priority, Severity } from '@rotki/common';
import { err, getOr, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { logger } from '@/modules/core/common/logging/logging';
import { createPersistentSharedComposable } from '@/modules/core/common/use-persistent-shared-composable';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useHistoryTransactionDecoding } from '@/modules/history/events/tx/use-history-transaction-decoding';
import { useTargetedRedecode } from '@/modules/history/events/tx/use-targeted-redecode';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { UMBRELLA_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { type ActivityContext, useNativeTask } from '@/modules/task-center/use-native-task';
import { useInternalTxConflictSelection } from './use-internal-tx-conflict-selection';
import { getConflictKey } from './use-internal-tx-conflicts';

/**
 * The dock row for a bulk resolution, which carries its progress and parents each conflict's decode.
 *
 * @remarks
 * A re-pull, since that is what resolving does. The `RUN` part keeps it apart from the other re-pull
 * ids, and one id is enough because the panel runs a single bulk resolution at a time.
 */
const RESOLUTION_ACTIVITY_ID = makeActivityId(ActivityKind.REPULLING, ActivityPart.RUN, 'internal-tx-conflicts');

export interface ResolutionProgress {
  completed: number;
  current: InternalTxConflict | undefined;
  failed: number;
  isRunning: boolean;
  total: number;
}

function defaultProgress(): ResolutionProgress {
  return {
    completed: 0,
    current: undefined,
    failed: 0,
    isRunning: false,
    total: 0,
  };
}

interface UseInternalTxConflictResolutionReturn {
  cancelResolution: () => void;
  isResolving: (conflict: InternalTxConflict) => boolean;
  progress: Ref<ResolutionProgress>;
  resolveMany: (conflicts: InternalTxConflict[], callbacks: ResolutionCallbacks) => Promise<void>;
  resolveOne: (conflict: InternalTxConflict, callbacks: ResolutionCallbacks) => Promise<void>;
}

export interface ResolutionCallbacks {
  onComplete: () => Promise<void>;
}

export const useInternalTxConflictResolution = createPersistentSharedComposable(({ acquireBusy, releaseBusy }): UseInternalTxConflictResolutionReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const { getChain } = useSupportedChains();
  const { cancelDecoding } = useHistoryTransactionDecoding();
  const { pullAndDecodeTransactionsRaw } = useTargetedRedecode();
  const { removeKeys } = useInternalTxConflictSelection();
  const { notify } = useNotifications();
  const { submitTask } = useNativeTask();

  const progress = ref<ResolutionProgress>(defaultProgress());
  const cancelRequested = ref<boolean>(false);
  const resolvingKeys = ref<Set<string>>(new Set());

  function isResolving(conflict: InternalTxConflict): boolean {
    return get(resolvingKeys).has(getConflictKey(conflict));
  }

  /**
   * Resolves one conflict by pulling and re-decoding its transaction.
   *
   * @remarks
   * REPULL and FIX_REDECODE both resolve through this same call; the action type is a visual
   * categorisation of the problem for the user, not a different strategy. Uses the `Raw` variant,
   * which throws on failure, so the resolution progress tracks errors.
   */
  async function executeResolution(conflict: InternalTxConflict, parent?: ActivityId): Promise<void> {
    const chain = getChain(conflict.chain);

    await pullAndDecodeTransactionsRaw({
      chain,
      txRefs: [conflict.txHash],
    }, parent);
  }

  async function resolveOne(conflict: InternalTxConflict, callbacks: ResolutionCallbacks): Promise<void> {
    const key = getConflictKey(conflict);
    set(resolvingKeys, new Set([...get(resolvingKeys), key]));
    acquireBusy();

    try {
      await executeResolution(conflict);
      removeKeys([key]);
    }
    catch (error: any) {
      logger.error('Failed to resolve conflict:', error);
    }
    finally {
      const keys = new Set(get(resolvingKeys));
      keys.delete(key);
      set(resolvingKeys, keys);
      try {
        await callbacks.onComplete();
      }
      finally {
        releaseBusy();
      }
    }
  }

  /**
   * Works through the conflicts one at a time, stopping between two when either the panel or the
   * task dock cancels.
   *
   * @returns whether the run was cancelled before it reached the last conflict
   */
  async function resolveInTurn(
    conflicts: InternalTxConflict[],
    callbacks: ResolutionCallbacks,
    { cancelled, report }: ActivityContext,
  ): Promise<boolean> {
    const total = conflicts.length;
    const stopped = (): boolean => get(cancelRequested) || cancelled();

    for (const [index, conflict] of conflicts.entries()) {
      if (stopped())
        return true;

      report({ current: index, total });
      set(progress, { ...get(progress), current: conflict });

      try {
        await executeResolution(conflict, RESOLUTION_ACTIVITY_ID);
        removeKeys([getConflictKey(conflict)]);
        set(progress, { ...get(progress), completed: get(progress).completed + 1 });
      }
      catch (error: any) {
        logger.error('Failed to resolve conflict:', error);
        set(progress, { ...get(progress), failed: get(progress).failed + 1 });
      }

      await callbacks.onComplete();
    }

    report({ current: total, total });
    return false;
  }

  async function resolveMany(conflicts: InternalTxConflict[], callbacks: ResolutionCallbacks): Promise<void> {
    set(cancelRequested, false);
    acquireBusy();

    try {
      const total = conflicts.length;
      set(progress, {
        completed: 0,
        current: undefined,
        failed: 0,
        isRunning: true,
        total,
      });

      const outcome = await submitTask<boolean>({
        id: RESOLUTION_ACTIVITY_ID,
        kind: ActivityKind.REPULLING,
        lane: UMBRELLA_LANE,
        rerunnable: false,
        run: async (context): Promise<Result<boolean, TaskError>> => {
          const stopped = await resolveInTurn(conflicts, callbacks, context);
          const { completed, failed } = get(progress);
          if (!stopped && failed > 0)
            return err(TaskFailed({ message: t('internal_tx_conflicts.notifications.completed_with_errors', { completed, failed, total }) }));
          return ok(stopped);
        },
        subtitle: activityLabelFor(msg.$t('task_center.count.transactions'), { count: total }, total),
        title: t('internal_tx_conflicts.notifications.title'),
        userStarted: true,
      });

      const cancelled = getOr(outcome, false);
      const { completed, failed } = get(progress);
      set(progress, defaultProgress());

      if (cancelled) {
        notify({
          message: t('internal_tx_conflicts.notifications.cancelled', { completed, total }),
          priority: Priority.NORMAL,
          severity: Severity.WARNING,
          title: t('internal_tx_conflicts.notifications.title'),
        });
      }
      else if (failed > 0) {
        notify({
          message: t('internal_tx_conflicts.notifications.completed_with_errors', { completed, failed, total }),
          priority: Priority.NORMAL,
          severity: Severity.WARNING,
          title: t('internal_tx_conflicts.notifications.title'),
        });
      }
      else {
        notify({
          message: t('internal_tx_conflicts.notifications.completed', { total }),
          priority: Priority.NORMAL,
          severity: Severity.INFO,
          title: t('internal_tx_conflicts.notifications.title'),
        });
      }
    }
    finally {
      releaseBusy();
    }
  }

  function cancelResolution(): void {
    set(cancelRequested, true);
    cancelDecoding();
  }

  return {
    cancelResolution,
    isResolving,
    progress,
    resolveMany,
    resolveOne,
  };
});
