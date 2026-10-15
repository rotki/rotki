import type { DatabaseUploadProgress, DbUploadResult } from '@/modules/core/messaging/types';
import { startPromise } from '@shared/utils';
import { err, ok, type Result } from 'plainfp/result';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useSync } from '@/modules/session/use-session-sync';
import { Priority } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseSyncActivityReturn {
  /** Feeds an upload progress message into the sync row it belongs to. */
  onProgress: (progress: DatabaseUploadProgress) => void;
  /** Settles the automatic backup row with the backend's verdict. */
  onResult: (result: DbUploadResult) => void;
}

/**
 * Shows database uploads in the dock, where the rest of the background work reports.
 *
 * @remarks
 * A backup the user starts already has a row, the force sync itself, so its upload progress only
 * feeds that row, and its outcome is that row's to report. The backend also uploads on its own
 * schedule, which the frontend only learns about from the progress and result messages; such an
 * upload gets a row of its own, opened by the first message and settled by the result, failing
 * with the backend's reason. Its id is stable, so a backup failing every hour replaces its row
 * rather than piling up.
 */
export const useSyncActivity = createSharedComposable((): UseSyncActivityReturn => {
  const { reportProgress, submitTask } = useNativeTask();
  const { manualSyncActive } = useSync();
  const { t } = useI18n({ useScope: 'global' });

  const manualId = makeActivityId(ActivityKind.SYNC);
  const automaticId = makeActivityId(ActivityKind.SYNC, 'automatic');

  /** Settles the automatic row while one is open. */
  let settleAutomatic: ((outcome: Result<void, TaskError>) => void) | undefined;

  function openAutomatic(): void {
    if (settleAutomatic)
      return;

    const outcome = new Promise<Result<void, TaskError>>((resolve) => {
      settleAutomatic = resolve;
    });

    startPromise(submitTask({
      id: automaticId,
      kind: ActivityKind.SYNC,
      priority: Priority.BACKGROUND,
      rerunnable: false,
      run: async (): Promise<Result<void, TaskError>> => outcome,
      subtitle: t('sync_indicator.activity.automatic'),
      title: t('task_center.group.sync'),
    }));
  }

  function settle(outcome: Result<void, TaskError>): void {
    settleAutomatic?.(outcome);
    settleAutomatic = undefined;
  }

  function onProgress(progress: DatabaseUploadProgress): void {
    let id = manualId;
    if (!get(manualSyncActive)) {
      openAutomatic();
      id = automaticId;
    }

    if (progress.type === 'uploading')
      reportProgress(id, { current: progress.currentChunk, total: progress.totalChunks });
  }

  function onResult(result: DbUploadResult): void {
    if (get(manualSyncActive))
      return;

    if (result.uploaded) {
      settle(ok(undefined));
      return;
    }

    openAutomatic();
    settle(err(TaskFailed({ message: result.message ?? t('sync_indicator.activity.failed') })));
  }

  return { onProgress, onResult };
});
