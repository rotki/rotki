import type { Ref } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type {
  IgnorePayload,
} from '@/modules/history/ignored';
import type { EntryMeta } from '@/modules/history/meta';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';
import { useHistoryIgnoringApi } from '@/modules/history/api/use-history-ignoring-api';

interface CommonIgnoreAction<T extends EntryMeta> {
  toData: (t: T) => string;
}

interface UseIgnoreReturn<T extends EntryMeta> {
  ignore: (ignored: boolean) => Promise<ActionStatus>;
  ignoreSingle: (item: T, ignored: boolean) => Promise<ActionStatus>;
  toggle: (item: T) => Promise<ActionStatus>;
}

/**
 * Excludes the selected entries from accounting, or includes them again.
 *
 * @remarks
 * Reports nothing itself: every action returns its status, the backend's message on a failure, for
 * the surface that started it to name.
 */
export function useIgnore<T extends EntryMeta>(
  { toData }: CommonIgnoreAction<T>,
  selected: Ref<T[]>,
  refresh: () => any,
): UseIgnoreReturn<T> {
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
      return { message: getErrorMessage(error), success: false };
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

    if (data.length === 0)
      return { message: t('ignore.no_items.description', ignored ? 1 : 2), success: false };

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

  async function toggle(item: T): Promise<ActionStatus> {
    set(selected, [item]);
    return ignore(!item.ignoredInAccounting);
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
