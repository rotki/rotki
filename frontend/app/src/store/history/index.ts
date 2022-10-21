import { useHistoryIgnoringApi } from '@/services/history/history-ignoring-api';
import { IgnoreActionPayload } from '@/store/history/types';
import { useMessageStore } from '@/store/message';
import { useNotifications } from '@/store/notifications';
import { ActionStatus } from '@/store/types';
import { IgnoredActions } from '@/types/history/ignored';
import { logger } from '@/utils/logging';

export const useHistory = defineStore('history', () => {
  const ignored = ref<IgnoredActions>({});

  const { notify } = useNotifications();
  const { setMessage } = useMessageStore();
  const { t } = useI18n();

  const api = useHistoryIgnoringApi();

  const fetchIgnored = async () => {
    try {
      set(ignored, await api.fetchIgnored());
    } catch (e: any) {
      logger.error(e);
      const message = e?.message ?? e ?? '';
      notify({
        title: t('actions.history.fetch_ignored.error.title').toString(),
        message: t('actions.history.fetch_ignored.error.message', {
          message
        }).toString(),
        display: true
      });
    }
  };

  const ignoreInAccounting = async (
    { actionIds, type }: IgnoreActionPayload,
    ignore: boolean
  ): Promise<ActionStatus> => {
    try {
      ignore
        ? await api.ignoreActions(actionIds, type)
        : await api.unignoreActions(actionIds, type);
      await fetchIgnored();
    } catch (e: any) {
      let title: string;
      let description: string;
      if (ignore) {
        title = t('actions.ignore.error.title').toString();
      } else {
        title = t('actions.unignore.error.title').toString();
      }

      if (ignore) {
        description = t('actions.ignore.error.description', {
          error: e.message
        }).toString();
      } else {
        description = t('actions.unignore.error.description', {
          error: e.message
        }).toString();
      }
      setMessage({
        success: false,
        title,
        description
      });
      return { success: false, message: 'failed' };
    }

    return { success: true };
  };

  return {
    ignored,
    fetchIgnored,
    ignoreInAccounting
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useHistory, import.meta.hot));
}
