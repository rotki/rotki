import { useMessageStore } from '@/store/message';
import { type ActionStatus } from '@/store/types';
import { type IgnorePayload } from '@/types/history/ignored';

export const useHistory = defineStore('history', () => {
  const { setMessage } = useMessageStore();
  const { t } = useI18n();

  const api = useHistoryIgnoringApi();

  const ignoreInAccounting = async (
    payload: IgnorePayload,
    ignore: boolean
  ): Promise<ActionStatus> => {
    try {
      ignore
        ? await api.ignoreActions(payload)
        : await api.unignoreActions(payload);
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
    ignoreInAccounting
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useHistory, import.meta.hot));
}
