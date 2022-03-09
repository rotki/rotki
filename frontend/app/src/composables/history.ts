import { computed, Ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { getPremium } from '@/composables/session';
import i18n from '@/i18n';
import { EntryMeta } from '@/services/history/types';
import { useHistory } from '@/store/history';
import { IgnoreActionPayload, IgnoreActionType } from '@/store/history/types';
import { useMainStore } from '@/store/store';
import { ActionStatus } from '@/store/types';
import { Collection } from '@/types/collection';
import { uniqueStrings } from '@/utils/data';

export const getCollectionData = <T>(collection: Ref<Collection<T>>) => {
  const data = computed<T[]>(() => {
    return get(collection).data as T[];
  });
  const limit = computed<number>(() => get(collection).limit);
  const found = computed<number>(() => get(collection).found);
  const total = computed<number>(() => get(collection).total);

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
  const premium = getPremium();

  const itemLength = computed(() => {
    const isPremium = get(premium);
    const totalFound = get(found);
    if (isPremium) {
      return totalFound;
    }

    const entryLimit = get(limit);
    return Math.min(totalFound, entryLimit);
  });

  const showUpgradeRow = computed(() => {
    return get(limit) <= get(total) && get(limit) > 0;
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
  const { setMessage } = useMainStore();

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
    const ids = get(items)
      .filter(item => {
        const { ignoredInAccounting } = item;
        const identifier = getIdentifier(item);
        return (
          (ignored ? !ignoredInAccounting : ignoredInAccounting) &&
          get(selected)
            .map(item => getIdentifier(item))
            .includes(identifier)
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
      set(selected, []);
    }
  };

  return {
    ignore
  };
};
