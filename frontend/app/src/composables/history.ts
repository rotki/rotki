import { computed, Ref } from '@vue/composition-api';
import i18n from '@/i18n';
import { EntryMeta } from '@/services/history/types';
import { useHistory } from '@/store/history';
import { IgnoreActionPayload, IgnoreActionType } from '@/store/history/types';
import store from '@/store/store';
import { ActionStatus, Message } from '@/store/types';
import { useStore } from '@/store/utils';
import { Collection } from '@/types/collection';
import { uniqueStrings } from '@/utils/data';

export const getCollectionData = <T>(collection: Ref<Collection<T>>) => {
  const data = computed<T[]>(() => {
    return collection.value.data as T[];
  });
  const limit = computed<number>(() => collection.value.limit);
  const found = computed<number>(() => collection.value.found);
  const total = computed<number>(() => collection.value.total);

  return {
    data,
    limit,
    found,
    total
  };
};

export const setupEntryLimit = (
  limit: Ref<number>,
  found: Ref<number>,
  total: Ref<number>
) => {
  const store = useStore();

  const premium = computed(() => {
    return store.state.session!!.premium;
  });

  const itemLength = computed(() => {
    const isPremium = premium.value;
    const totalFound = found.value;
    if (isPremium) {
      return totalFound;
    }

    const entryLimit = limit.value;
    return Math.min(totalFound, entryLimit);
  });

  const showUpgradeRow = computed(() => {
    return limit.value <= total.value && limit.value > 0;
  });

  return {
    itemLength,
    showUpgradeRow
  };
};

export const setupIgnore = <T extends EntryMeta>(
  type: IgnoreActionType,
  selected: Ref<T[]>,
  items: Ref<T[]>,
  refresh: () => any,
  getIdentifier: (item: T) => string
) => {
  const setMessage = (message: Message) => {
    store.commit('setMessage', message);
  };

  const { ignoreInAccounting } = useHistory();

  const ignoreActions = async (
    payload: IgnoreActionPayload
  ): Promise<ActionStatus> => {
    return await ignoreInAccounting(payload, true);
  };

  const unignoreActions = async (
    payload: IgnoreActionPayload
  ): Promise<ActionStatus> => {
    return await ignoreInAccounting(payload, false);
  };

  const ignore = async (ignored: boolean) => {
    const ids = items.value
      .filter(item => {
        const { ignoredInAccounting } = item;
        const identifier = getIdentifier(item);
        return (
          (ignored ? !ignoredInAccounting : ignoredInAccounting) &&
          selected.value.map(item => getIdentifier(item)).includes(identifier)
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
