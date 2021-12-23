import { Ref } from '@vue/composition-api';
import i18n from '@/i18n';
import { EntryMeta } from '@/services/history/types';
import { HistoryActions } from '@/store/history/consts';
import { IgnoreActionPayload, IgnoreActionType } from '@/store/history/types';
import store from '@/store/store';
import { ActionStatus, Message } from '@/store/types';
import { uniqueStrings } from '@/utils/data';

export const setupIgnore = <T extends EntryMeta>(
  type: IgnoreActionType,
  selected: Ref<string[]>,
  items: Ref<T[]>,
  refresh: () => any,
  getIdentifier: (item: T) => string
) => {
  const setMessage = (message: Message) => {
    store.commit('setMessage', message);
  };
  const ignoreActions = async (payload: IgnoreActionPayload) => {
    return (await store.dispatch(
      `history/${HistoryActions.IGNORE_ACTIONS}`,
      payload
    )) as ActionStatus;
  };

  const unignoreActions = async (payload: IgnoreActionPayload) => {
    return (await store.dispatch(
      `history/${HistoryActions.UNIGNORE_ACTION}`,
      payload
    )) as ActionStatus;
  };
  const ignore = async (ignored: boolean) => {
    const ids = items.value
      .filter(item => {
        const { ignoredInAccounting } = item;
        const identifier = getIdentifier(item);
        return (
          (ignored ? !ignoredInAccounting : ignoredInAccounting) &&
          selected.value.includes(identifier)
        );
      })
      .map(item => getIdentifier(item))
      .filter(uniqueStrings);

    let status: ActionStatus;

    if (ids.length === 0) {
      const choice = ignored ? 1 : 2;
      setMessage({
        success: false,
        title: i18n.tc('ignore.no_items.title', choice).toString(),
        description: i18n.tc('ignore.no_items.description', choice).toString()
      });
      return;
    }
    const payload: IgnoreActionPayload = {
      actionIds: ids,
      type: type
    };
    if (ignored) {
      status = await ignoreActions(payload);
    } else {
      status = await unignoreActions(payload);
    }

    if (status.success) {
      refresh();
      selected.value = [];
    }
  };

  return {
    ignore
  };
};
