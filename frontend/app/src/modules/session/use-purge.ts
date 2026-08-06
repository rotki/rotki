import type { Purgeable } from '@/modules/session/purge';
import { err, isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, isCancellation, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useProtocolCacheStatusStore } from '@/modules/history/use-protocol-cache-status-store';
import { useSessionApi } from '@/modules/session/api/use-session-api';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseSessionPurge {
  purgeData: (purgeable: Purgeable, value: string, deleteData: () => Promise<void>) => Promise<void>;
  refreshGeneralCache: (source: string) => Promise<void>;
}

export function useSessionPurge(): UseSessionPurge {
  const { refreshGeneralCacheTask } = useSessionApi();
  const { submitTask } = useNativeTask();
  const { notifyError } = useNotifications();
  const { markAllProtocolCacheCancelled, resetProtocolCacheUpdatesStatus } = useProtocolCacheStatusStore();
  const { t } = useI18n({ useScope: 'global' });

  /**
   * Run one purge as an activity. The caller still owns *how* each source is deleted — the
   * endpoints differ per source — while the orchestrator owns that it happened, under an id that
   * names the source (`purge:transactions:eth`). Whatever derives from that data declares a
   * `staleAfter` edge against this kind rather than anyone reaching in to reset its status.
   */
  const purgeData = async (purgeable: Purgeable, value: string, deleteData: () => Promise<void>): Promise<void> => {
    const parts = value ? [purgeable, value] : [purgeable];
    await submitTask({
      id: makeActivityId(ActivityKind.PURGE, ...parts),
      kind: ActivityKind.PURGE,
      run: async (): Promise<Result<void, TaskError>> => {
        try {
          await deleteData();
          return ok(undefined);
        }
        catch (error: unknown) {
          return err(TaskFailed({ cause: error, message: getErrorMessage(error) }));
        }
      },
      subtitle: value ? activityLabelFor(msg.$t('task_center.activity.purge.target'), { target: value }) : undefined,
      title: t('task_center.group.purge'),
    });
  };

  const refreshGeneralCache = async (source: string): Promise<void> => {
    resetProtocolCacheUpdatesStatus();
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.PROTOCOL_CACHE),
      kind: ActivityKind.PROTOCOL_CACHE,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => refreshGeneralCacheTask(source),
        ),
        () => {},
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.protocol_cache.source'), { source }),
      title: t('task_center.group.protocol_cache'),
    });

    if (isErr(outcome)) {
      if (isCancellation(outcome.error)) {
        markAllProtocolCacheCancelled();
        return;
      }
      if (isActionable(outcome.error)) {
        notifyError(
          t('actions.session.refresh_general_cache.task.title', { name: source }),
          t('actions.session.refresh_general_cache.error.message', {
            message: outcome.error.message,
            name: source,
          }),
        );
      }
    }
  };

  return {
    purgeData,
    refreshGeneralCache,
  };
}
