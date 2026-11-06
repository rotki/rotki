import type { Ref } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type {
  IgnorePayload,
} from '@/modules/history/ignored';
import type { EntryMeta } from '@/modules/history/meta';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useHistoryIgnoringApi } from '@/modules/history/api/use-history-ignoring-api';

interface CommonIgnoreAction<T extends EntryMeta> {
  toData: (t: T) => string;
}

interface UseIgnoreReturn<T extends EntryMeta> {
  ignore: (ignored: boolean) => Promise<ActionStatus>;
  ignoreSingle: (item: T, ignored: boolean) => Promise<ActionStatus>;
  toggle: (item: T) => Promise<void>;
}

export function useIgnore<T extends EntryMeta>(
  { toData }: CommonIgnoreAction<T>,
  selected: Ref<T[]>,
  refresh: () => any,
): UseIgnoreReturn<T> {
  const { showErrorMessage } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
  const api = useHistoryIgnoringApi();

  const ignoreInAccounting = async (payload: IgnorePayload, ignore: boolean): Promise<ActionStatus> => {
    try {
      if (ignore) {
        await api.ignoreActions(payload);
      }
      else {
        await api.unignoreActions(payload);
      }
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      if (ignore)
        showErrorMessage(t('actions.ignore.error.title'), t('actions.ignore.error.description', { error: message }));
      else
        showErrorMessage(t('actions.unignore.error.title'), t('actions.unignore.error.description', { error: message }));
      return { message, success: false };
    }

    return { success: true };
  };

  const ignoreActions = async (payload: IgnorePayload): Promise<ActionStatus> =>
    ignoreInAccounting(payload, true);

  const unignoreActions = async (payload: IgnorePayload): Promise<ActionStatus> =>
    ignoreInAccounting(payload, false);

  const ignore = async (ignored: boolean): Promise<ActionStatus> => {
    const data = get(selected).filter((item) => {
      const { ignoredInAccounting } = item;
      return ignored ? !ignoredInAccounting : ignoredInAccounting;
    });

    const payload: IgnorePayload = {
      data: data.map(toData).filter(uniqueStrings),
    };

    let status: ActionStatus;

    if (data.length === 0) {
      const choice = ignored ? 1 : 2;
      const message = t('ignore.no_items.description', choice);
      showErrorMessage(t('ignore.no_items.title', choice), message);
      return { message, success: false };
    }

    if (ignored)
      status = await ignoreActions(payload);
    else
      status = await unignoreActions(payload);

    if (status.success) {
      refresh();
      set(selected, []);
    }
    return status;
  };

  async function toggle(item: T): Promise<void> {
    set(selected, [item]);
    await ignore(!item.ignoredInAccounting);
  }

  async function ignoreSingle(item: T, ignored: boolean): Promise<ActionStatus> {
    set(selected, [item]);
    return ignore(ignored);
  }

  return {
    ignore,
    ignoreSingle,
    toggle,
  };
}
