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
}

interface SelectionActions {
  clear: () => void;
  exit: () => void;
  toggle: () => void;
  toggleAll: () => void;
  toggleEvent: (eventId: number) => void;
  toggleSwap: (eventIds: number[]) => void;
}

export interface UseHistoryEventsSelectionModeReturn {
  actions: SelectionActions;
  getSelectedIds: () => number[];
  setAvailableIds: (events: HistoryEventEntry[]) => void;
  state: ComputedRef<SelectionState>;
  isEventSelected: (eventId: number) => boolean;
  selectedEvents: Ref<Set<number>>;
  isSelectionMode: Readonly<Ref<boolean>>;
}

export function useHistoryEventsSelectionMode(): UseHistoryEventsSelectionModeReturn {
  const isActive = ref<boolean>(false);
  const selectedIds = ref<Set<number>>(new Set());
  const availableIds = ref<number[]>([]);

  // Unified state object
  const state = computed<SelectionState>(() => ({
    hasAvailableEvents: get(availableIds).length > 0,
    isActive: get(isActive),
    isAllSelected: get(availableIds).length > 0
      && get(availableIds).every(id => get(selectedIds).has(id)),
    isPartiallySelected: get(selectedIds).size > 0
      && get(selectedIds).size < get(availableIds).length,
    selectedCount: get(selectedIds).size,
    selectedIds: get(selectedIds),
  }));

  const actions: SelectionActions = {
    clear: () => {
      set(selectedIds, new Set());
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
      if (get(state).isAllSelected)
        actions.clear();
      else
        set(selectedIds, new Set(get(availableIds)));
    },
    toggleEvent: (eventId: number) => {
      const ids = new Set(get(selectedIds));
      if (ids.has(eventId))
        ids.delete(eventId);
      else
        ids.add(eventId);

      set(selectedIds, ids);
    },
    toggleSwap: (eventIds: number[]) => {
      const ids = new Set(get(selectedIds));
      const allSelected = eventIds.every(id => ids.has(id));

      if (allSelected)
        eventIds.forEach(id => ids.delete(id));
      else
        eventIds.forEach(id => ids.add(id));

      set(selectedIds, ids);
    },
  };

  // Public API
  const getSelectedIds = (): number[] => Array.from(get(selectedIds));

  const setAvailableIds = (events: HistoryEventEntry[]): void => {
    const ids = events.map(event => event.identifier);
    set(availableIds, ids);
  };

  const isEventSelected = (eventId: number): boolean => get(selectedIds).has(eventId);

  return {
    actions,
    getSelectedIds,
    isEventSelected,
    isSelectionMode: readonly(isActive),
    selectedEvents: selectedIds,
    setAvailableIds,
    state,
  };
}
