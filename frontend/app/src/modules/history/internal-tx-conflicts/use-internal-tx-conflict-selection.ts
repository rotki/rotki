import type { ComputedRef, Ref } from 'vue';
import type { InternalTxConflict } from './types';
import { getConflictKey } from './use-internal-tx-conflicts';

interface UseInternalTxConflictSelectionReturn {
  areAllSelected: (pageConflicts: InternalTxConflict[]) => boolean;
  clearSelection: () => void;
  isSelected: (conflict: InternalTxConflict) => boolean;
  removeKeys: (keys: string[]) => void;
  selectedConflicts: ComputedRef<InternalTxConflict[]>;
  selectedCount: ComputedRef<number>;
  selectedKeys: Ref<Set<string>>;
  toggleAllOnPage: (pageConflicts: InternalTxConflict[]) => void;
  toggleSelection: (conflict: InternalTxConflict) => void;
}

export const useInternalTxConflictSelection = createSharedComposable((): UseInternalTxConflictSelectionReturn => {
  const selectedKeys = ref<Set<string>>(new Set());
  const selectedConflictsMap = ref<Map<string, InternalTxConflict>>(new Map());

  const selectedCount = computed<number>(() => get(selectedKeys).size);
  const selectedConflicts = computed<InternalTxConflict[]>(() => [...get(selectedConflictsMap).values()]);

  function areAllSelected(pageConflicts: InternalTxConflict[]): boolean {
    if (pageConflicts.length === 0)
      return false;
    const keys = get(selectedKeys);
    return pageConflicts.every(c => keys.has(getConflictKey(c)));
  }

  function isSelected(conflict: InternalTxConflict): boolean {
    return get(selectedKeys).has(getConflictKey(conflict));
  }

  function toggleSelection(conflict: InternalTxConflict): void {
    const key = getConflictKey(conflict);
    const keys = new Set(get(selectedKeys));
    const map = new Map(get(selectedConflictsMap));
    if (keys.has(key)) {
      keys.delete(key);
      map.delete(key);
    }
    else {
      keys.add(key);
      map.set(key, conflict);
    }
    set(selectedKeys, keys);
    set(selectedConflictsMap, map);
  }

  function toggleAllOnPage(pageConflicts: InternalTxConflict[]): void {
    const keys = new Set(get(selectedKeys));
    const map = new Map(get(selectedConflictsMap));
    const allSelected = areAllSelected(pageConflicts);

    if (allSelected) {
      for (const conflict of pageConflicts) {
        const key = getConflictKey(conflict);
        keys.delete(key);
        map.delete(key);
      }
    }
    else {
      for (const conflict of pageConflicts) {
        const key = getConflictKey(conflict);
        keys.add(key);
        map.set(key, conflict);
      }
    }
    set(selectedKeys, keys);
    set(selectedConflictsMap, map);
  }

  function clearSelection(): void {
    set(selectedKeys, new Set());
    set(selectedConflictsMap, new Map());
  }

  function removeKeys(keysToRemove: string[]): void {
    const keys = new Set(get(selectedKeys));
    const map = new Map(get(selectedConflictsMap));
    for (const key of keysToRemove) {
      keys.delete(key);
      map.delete(key);
    }
    set(selectedKeys, keys);
    set(selectedConflictsMap, map);
  }

  return {
    areAllSelected,
    clearSelection,
    isSelected,
    removeKeys,
    selectedConflicts,
    selectedCount,
    selectedKeys,
    toggleAllOnPage,
    toggleSelection,
  };
});
