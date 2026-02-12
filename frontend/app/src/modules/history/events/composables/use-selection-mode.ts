import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import { get, set } from '@vueuse/shared';

export interface SelectionState {
  isActive: boolean;
  isAllSelected: boolean;
  isPartiallySelected: boolean;
  selectedCount: number;
  selectedIds: Set<number>;
  hasAvailableEvents: boolean;
  selectAllMatching: boolean;
  totalMatchingCount: number;
}

interface SelectionActions {
  clear: () => void;
  exit: () => void;
  toggle: () => void;
  toggleAll: () => void;
  toggleEvent: (eventId: number) => void;
  toggleSwap: (eventIds: number[]) => void;
  toggleSelectAllMatching: () => void;
}

export interface UseHistoryEventsSelectionModeReturn {
  actions: SelectionActions;
  getSelectedIds: () => number[];
  setAvailableIds: (events: HistoryEventEntry[]) => void;
  setTotalMatchingCount: (count: number) => void;
  state: ComputedRef<SelectionState>;
  isEventSelected: (eventId: number) => boolean;
  selectedEvents: Ref<Set<number>>;
  isSelectionMode: Readonly<Ref<boolean>>;
  isSelectAllMatching: Readonly<Ref<boolean>>;
}

export function useHistoryEventsSelectionMode(): UseHistoryEventsSelectionModeReturn {
  const isActive = ref<boolean>(false);
  const selectedIds = shallowRef<Set<number>>(new Set());
  const availableIds = ref<number[]>([]);
  const selectAllMatching = ref<boolean>(false);
  const totalMatchingCount = ref<number>(0);

  // Unified state object
  const state = computed<SelectionState>(() => {
    const isSelectAll = get(selectAllMatching);
    const availableIdsLength = get(availableIds).length;
    const selectedIdsVal = get(selectedIds);
    const selectedIdsLength = selectedIdsVal.size;

    return {
      hasAvailableEvents: availableIdsLength > 0,
      isActive: get(isActive),
      isAllSelected: availableIdsLength > 0
        && get(availableIds).every(id => selectedIdsVal.has(id)),
      isPartiallySelected: selectedIdsLength > 0
        && selectedIdsLength < availableIdsLength
        && !isSelectAll,
      selectAllMatching: isSelectAll,
      selectedCount: isSelectAll ? get(totalMatchingCount) : selectedIdsLength,
      selectedIds: selectedIdsVal,
      totalMatchingCount: get(totalMatchingCount),
    };
  });

  const actions: SelectionActions = {
    clear: () => {
      set(selectedIds, new Set());
      set(selectAllMatching, false);
    },
    exit: () => {
      set(isActive, false);
      actions.clear();
    },
    toggle: () => {
      set(isActive, !get(isActive));
      if (!get(isActive))
        actions.clear();
    },
    toggleAll: () => {
      // If selectAllMatching is enabled, disable it and clear
      if (get(selectAllMatching)) {
        actions.clear();
        return;
      }

      if (get(state).isAllSelected)
        actions.clear();
      else
        set(selectedIds, new Set(get(availableIds)));
    },
    toggleEvent: (eventId: number) => {
      // Disable selectAllMatching when manually toggling events
      if (get(selectAllMatching))
        set(selectAllMatching, false);

      const ids = new Set(get(selectedIds));
      if (ids.has(eventId))
        ids.delete(eventId);
      else
        ids.add(eventId);

      set(selectedIds, ids);
    },
    toggleSwap: (eventIds: number[]) => {
      // Disable selectAllMatching when manually toggling events
      if (get(selectAllMatching))
        set(selectAllMatching, false);

      const ids = new Set(get(selectedIds));
      const allSelected = eventIds.every(id => ids.has(id));

      if (allSelected)
        eventIds.forEach(id => ids.delete(id));
      else
        eventIds.forEach(id => ids.add(id));

      set(selectedIds, ids);
    },
    toggleSelectAllMatching: () => {
      const newValue = !get(selectAllMatching);
      set(selectAllMatching, newValue);
      // When toggling off, clear the selection
      if (!newValue)
        set(selectedIds, new Set());
    },
  };

  // Public API
  const getSelectedIds = (): number[] => Array.from(get(selectedIds));

  const setAvailableIds = (events: HistoryEventEntry[]): void => {
    const ids = events.map(event => event.identifier);
    set(availableIds, ids);
  };

  const setTotalMatchingCount = (count: number): void => {
    set(totalMatchingCount, count);
  };

  const isEventSelected = (eventId: number): boolean => get(selectAllMatching) || get(selectedIds).has(eventId);

  return {
    actions,
    getSelectedIds,
    isEventSelected,
    isSelectAllMatching: readonly(selectAllMatching),
    isSelectionMode: readonly(isActive),
    selectedEvents: selectedIds,
    setAvailableIds,
    setTotalMatchingCount,
    state,
  };
}
