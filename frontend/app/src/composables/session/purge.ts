import type { TaskMeta } from '@/modules/tasks/types';
import { useSessionApi } from '@/composables/api/session';
import { Section } from '@/modules/common/status';
import { useStatusStore } from '@/modules/common/use-status-store';
import { useProtocolCacheStatusStore } from '@/modules/history/use-protocol-cache-status-store';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { Purgeable } from '@/modules/session/purge';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskHandler } from '@/modules/tasks/use-task-handler';

interface UseSessionPurge {
  purgeCache: (purgeable: Purgeable, value: string) => void;
  refreshGeneralCache: (source: string) => Promise<void>;
}

export function useSessionPurge(): UseSessionPurge {
  const { refreshGeneralCacheTask } = useSessionApi();
  const { resetStatus } = useStatusStore();
  const { runTask } = useTaskHandler();
  const { notifyError } = useNotifications();
  const { markAllProtocolCacheCancelled, resetProtocolCacheUpdatesStatus } = useProtocolCacheStatusStore();
  const { t } = useI18n({ useScope: 'global' });

  const purgeCache = (purgeable: Purgeable): void => {
    if (purgeable === Purgeable.CENTRALIZED_EXCHANGES || purgeable === Purgeable.TRANSACTIONS) {
      resetStatus(Section.HISTORY);
    }
  };

  const refreshGeneralCache = async (source: string): Promise<void> => {
    resetProtocolCacheUpdatesStatus();
    const outcome = await runTask<boolean, TaskMeta>(
      async () => refreshGeneralCacheTask(source),
      { type: TaskType.REFRESH_GENERAL_CACHE, meta: { title: t('actions.session.refresh_general_cache.task.title', { name: source }) } },
    );

    if (!outcome.success) {
      if (outcome.cancelled) {
        markAllProtocolCacheCancelled();
        return;
      }
      if (!outcome.skipped) {
        notifyError(
          t('actions.session.refresh_general_cache.task.title', { name: source }),
          t('actions.session.refresh_general_cache.error.message', {
            message: outcome.message,
            name: source,
          }),
        );
      }
    }
  };

  return {
    purgeCache,
    refreshGeneralCache,
  };
}
