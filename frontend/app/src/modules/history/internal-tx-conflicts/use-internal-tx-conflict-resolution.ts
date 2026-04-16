import type { Ref } from 'vue';
import type { InternalTxConflict } from './types';
import { NotificationGroup, Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { logger } from '@/modules/core/common/logging/logging';
import { createPersistentSharedComposable } from '@/modules/core/common/use-persistent-shared-composable';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useHistoryTransactionDecoding } from '@/modules/history/events/tx/use-history-transaction-decoding';
import { useInternalTxConflictSelection } from './use-internal-tx-conflict-selection';
import { getConflictKey } from './use-internal-tx-conflicts';

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
  const { cancelDecoding, pullAndDecodeTransactionsRaw } = useHistoryTransactionDecoding();
  const { removeKeys } = useInternalTxConflictSelection();
  const { notify, removeMatching } = useNotifications();

  const progress = ref<ResolutionProgress>(defaultProgress());
  const cancelRequested = ref<boolean>(false);
  const resolvingKeys = ref<Set<string>>(new Set());

  function isResolving(conflict: InternalTxConflict): boolean {
    return get(resolvingKeys).has(getConflictKey(conflict));
  }

  // Both REPULL and FIX_REDECODE resolve via the same backend API (pull + redecode).
  // The action type distinction is visual — it categorizes the problem for the user,
  // not the resolution strategy.
  // Uses pullAndDecodeTransactionsRaw which throws on failure,
  // so errors are properly tracked by the resolution progress.
  async function executeResolution(conflict: InternalTxConflict): Promise<void> {
    const chain = getChain(conflict.chain);

    await pullAndDecodeTransactionsRaw({
      chain,
      txRefs: [conflict.txHash],
    });
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

      notify({
        group: NotificationGroup.INTERNAL_TX_CONFLICT_RESOLUTION,
        message: t('internal_tx_conflicts.notifications.started', { total }),
        severity: Severity.INFO,
        title: t('internal_tx_conflicts.notifications.title'),
      });

      const resolvedKeys: string[] = [];

      for (const conflict of conflicts) {
        if (get(cancelRequested))
          break;

        set(progress, { ...get(progress), current: conflict });

        try {
          await executeResolution(conflict);
          resolvedKeys.push(getConflictKey(conflict));
          const completed = get(progress).completed + 1;
          set(progress, { ...get(progress), completed });
          notify({
            group: NotificationGroup.INTERNAL_TX_CONFLICT_RESOLUTION,
            message: t('internal_tx_conflicts.notifications.progress', { completed, total }),
            severity: Severity.INFO,
            title: t('internal_tx_conflicts.notifications.title'),
          });
        }
        catch (error: any) {
          logger.error('Failed to resolve conflict:', error);
          set(progress, { ...get(progress), failed: get(progress).failed + 1 });
        }

        if (resolvedKeys.length > 0) {
          removeKeys([...resolvedKeys]);
          resolvedKeys.length = 0;
        }

        await callbacks.onComplete();
      }

      const { completed, failed } = get(progress);
      const cancelled = get(cancelRequested);

      set(progress, { ...get(progress), current: undefined, isRunning: false });
      set(progress, defaultProgress());

      removeMatching(({ group }) => group === NotificationGroup.INTERNAL_TX_CONFLICT_RESOLUTION);

      if (cancelled) {
        notify({
          message: t('internal_tx_conflicts.notifications.cancelled', { completed, total }),
          severity: Severity.WARNING,
          title: t('internal_tx_conflicts.notifications.title'),
        });
      }
      else if (failed > 0) {
        notify({
          message: t('internal_tx_conflicts.notifications.completed_with_errors', { completed, failed, total }),
          severity: Severity.WARNING,
          title: t('internal_tx_conflicts.notifications.title'),
        });
      }
      else {
        notify({
          message: t('internal_tx_conflicts.notifications.completed', { total }),
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
    startPromise(cancelDecoding());
  }

  return {
    cancelResolution,
    isResolving,
    progress,
    resolveMany,
    resolveOne,
  };
});
