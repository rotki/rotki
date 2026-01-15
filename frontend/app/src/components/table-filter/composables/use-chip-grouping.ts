import type { ComputedRef, Ref } from 'vue';
import type { Suggestion } from '@/types/filtering';
import { isEqual } from 'es-toolkit';

export type ChipDisplayType = 'normal' | 'grouped' | 'hidden';

const MAX_CHIPS_PER_KEY = 3;

interface UseChipGroupingReturn {
  expandedGroupKey: Ref<string | undefined>;
  groupedKeysCounts: ComputedRef<Record<string, number>>;
  groupedKeys: ComputedRef<Set<string>>;
  isKeyGrouped: (key: string) => boolean;
  getGroupedItemsForKey: (item: Suggestion) => Suggestion[];
  getChipDisplayType: (item: Suggestion) => ChipDisplayType;
  getGroupedOverflowCount: (item: Suggestion) => number;
  toggleGroupMenu: (key: string) => void;
  removeGroupedItem: (item: Suggestion) => void;
  removeAllItemsForKey: (key: string) => void;
}

export function useChipGrouping(
  selection: Ref<Suggestion[]>,
  updateMatches: (pairs: Suggestion[]) => void,
): UseChipGroupingReturn {
  const expandedGroupKey = ref<string>();

  const groupedKeysCounts = computed<Record<string, number>>(() => {
    const counts: Record<string, number> = {};
    for (const item of get(selection)) {
      counts[item.key] = (counts[item.key] || 0) + 1;
    }
    return counts;
  });

  const groupedKeys = computed<Set<string>>(() => {
    const result = new Set<string>();
    const counts = get(groupedKeysCounts);
    for (const [key, count] of Object.entries(counts)) {
      if (count > MAX_CHIPS_PER_KEY)
        result.add(key);
    }
    return result;
  });

  function isKeyGrouped(key: string): boolean {
    return get(groupedKeys).has(key);
  }

  function getGroupedItemsForKey(item: Suggestion): Suggestion[] {
    return get(selection).filter(s => s.key === item.key);
  }

  function getChipDisplayType(item: Suggestion): ChipDisplayType {
    if (!isKeyGrouped(item.key))
      return 'normal';

    const items = getGroupedItemsForKey(item);
    if (isEqual(items[0], item))
      return 'grouped';

    return 'hidden';
  }

  /**
   * Returns the overflow count for grouped chips.
   * Subtracts 1 from the total because the first item is shown separately.
   */
  function getGroupedOverflowCount(item: Suggestion): number {
    const total = get(groupedKeysCounts)[item.key] || 0;
    return total - 1;
  }

  function toggleGroupMenu(key: string): void {
    if (get(expandedGroupKey) === key) {
      set(expandedGroupKey, undefined);
    }
    else {
      set(expandedGroupKey, key);
    }
  }

  function removeGroupedItem(item: Suggestion): void {
    const newSelection = get(selection).filter(s => s.key !== item.key || s.value !== item.value);
    updateMatches(newSelection);
  }

  function removeAllItemsForKey(key: string): void {
    const newSelection = get(selection).filter(s => s.key !== key);
    updateMatches(newSelection);
    set(expandedGroupKey, undefined);
  }

  return {
    expandedGroupKey,
    getChipDisplayType,
    getGroupedItemsForKey,
    getGroupedOverflowCount,
    groupedKeys,
    groupedKeysCounts,
    isKeyGrouped,
    removeAllItemsForKey,
    removeGroupedItem,
    toggleGroupMenu,
  };
}
