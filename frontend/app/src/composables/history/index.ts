import type { ActionStatus } from '@/types/action';
import type { EntryMeta } from '@/types/history/meta';
import type { Ref } from 'vue';
import { useHistoryIgnoringApi } from '@/composables/api/history/ignore';
import { useMessageStore } from '@/store/message';
import {
  type CommonIgnorePayload,
  type EvmTransaction,
  type EvmTxIgnorePayload,
  IgnoreActionType,
  type IgnorePayload,
} from '@/types/history/ignored';

interface EvmTxIgnoreAction<T extends EntryMeta> {
  actionType: IgnoreActionType.EVM_TRANSACTIONS;
  toData: (t: T) => EvmTransaction;
}

interface CommonIgnoreAction<T extends EntryMeta> {
  actionType: Exclude<IgnoreActionType, IgnoreActionType.EVM_TRANSACTIONS>;
  toData: (t: T) => string;
}

interface UseIgnoreReturn<T extends EntryMeta> {
  ignore: (ignored: boolean) => Promise<void>;
  ignoreSingle: (item: T, ignored: boolean) => Promise<void>;
  toggle: (item: T) => Promise<void>;
}

export function useIgnore<T extends EntryMeta>(
  { actionType, toData }: EvmTxIgnoreAction<T> | CommonIgnoreAction<T>,
  selected: Ref<T[]>,
  refresh: () => any,
): UseIgnoreReturn<T> {
  const { setMessage } = useMessageStore();
  const { t } = useI18n();
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
    catch (error: any) {
      let title: string;
      let description: string;
      if (ignore)
        title = t('actions.ignore.error.title');
      else title = t('actions.unignore.error.title');

      if (ignore) {
        description = t('actions.ignore.error.description', {
          error: error.message,
        }).toString();
      }
      else {
        description = t('actions.unignore.error.description', {
          error: error.message,
        }).toString();
      }
      setMessage({
        description,
        success: false,
        title,
      });
      return { message: 'failed', success: false };
    }

    return { success: true };
  };

  const ignoreActions = async (payload: IgnorePayload): Promise<ActionStatus> =>
    ignoreInAccounting(payload, true);

  const unignoreActions = async (payload: IgnorePayload): Promise<ActionStatus> =>
    ignoreInAccounting(payload, false);

  const ignore = async (ignored: boolean): Promise<void> => {
    let payload: IgnorePayload;

    const data = get(selected).filter((item) => {
      const { ignoredInAccounting } = item;
      return ignored ? !ignoredInAccounting : ignoredInAccounting;
    });

    if (actionType === IgnoreActionType.EVM_TRANSACTIONS) {
      payload = {
        actionType,
        data: data.map(toData),
      } satisfies EvmTxIgnorePayload;
    }
    else {
      payload = {
        actionType,
        data: data.map(toData),
      } satisfies CommonIgnorePayload;
    }

    let status: ActionStatus;

    if (data.length === 0) {
      const choice = ignored ? 1 : 2;
      setMessage({
        description: t('ignore.no_items.description', choice),
        success: false,
        title: t('ignore.no_items.title', choice),
      });
      return;
    }

    if (ignored)
      status = await ignoreActions(payload);
    else
      status = await unignoreActions(payload);

    if (status.success) {
      refresh();
      set(selected, []);
    }
  };

  async function toggle(item: T): Promise<void> {
    set(selected, [item]);
    await ignore(!item.ignoredInAccounting);
  }

  async function ignoreSingle(item: T, ignored: boolean): Promise<void> {
    set(selected, [item]);
    await ignore(ignored);
  }

  return {
    ignore,
    ignoreSingle,
    toggle,
  };
}
