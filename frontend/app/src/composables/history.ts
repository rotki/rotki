import { type Ref } from 'vue';
import { useHistory } from '@/store/history';
import { useMessageStore } from '@/store/message';
import { type ActionStatus } from '@/store/types';
import { type EntryMeta } from '@/types/history/meta';
import {
  type CommonIgnorePayload,
  type EvmTransaction,
  type EvmTxIgnorePayload,
  IgnoreActionType,
  type IgnorePayload
} from '@/types/history/ignored';

interface EvmTxIgnoreAction<T extends EntryMeta> {
  actionType: IgnoreActionType.EVM_TRANSACTIONS;
  toData: (t: T) => EvmTransaction;
}

interface CommonIgnoreAction<T extends EntryMeta> {
  actionType: Exclude<IgnoreActionType, IgnoreActionType.EVM_TRANSACTIONS>;
  toData: (t: T) => string;
}

export const useIgnore = <T extends EntryMeta>(
  { actionType, toData }: EvmTxIgnoreAction<T> | CommonIgnoreAction<T>,
  selected: Ref<T[]>,
  refresh: () => any
) => {
  const { setMessage } = useMessageStore();
  const { ignoreInAccounting } = useHistory();
  const { tc } = useI18n();

  const ignoreActions = async (
    payload: IgnorePayload
  ): Promise<ActionStatus> => {
    return await ignoreInAccounting(payload, true);
  };

  const unignoreActions = async (
    payload: IgnorePayload
  ): Promise<ActionStatus> => {
    return await ignoreInAccounting(payload, false);
  };

  const ignore = async (ignored: boolean) => {
    let payload: IgnorePayload;

    const data = get(selected).filter(item => {
      const { ignoredInAccounting } = item;
      return ignored ? !ignoredInAccounting : ignoredInAccounting;
    });

    if (actionType === IgnoreActionType.EVM_TRANSACTIONS) {
      payload = {
        data: data.map(toData),
        actionType
      } satisfies EvmTxIgnorePayload;
    } else {
      payload = {
        data: data.map(toData),
        actionType
      } satisfies CommonIgnorePayload;
    }

    let status: ActionStatus;

    if (data.length === 0) {
      const choice = ignored ? 1 : 2;
      setMessage({
        success: false,
        title: tc('ignore.no_items.title', choice),
        description: tc('ignore.no_items.description', choice)
      });
      return;
    }

    if (ignored) {
      status = await ignoreActions(payload);
    } else {
      status = await unignoreActions(payload);
    }

    if (status.success) {
      refresh();
      set(selected, []);
    }
  };

  return {
    ignore
  };
};
