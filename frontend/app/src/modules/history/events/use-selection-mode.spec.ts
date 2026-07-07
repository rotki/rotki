import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import { useHistoryEventsSelectionMode } from './use-selection-mode';

// selection mode only reads `identifier`, so a minimal stub is enough here.
function event(identifier: number): HistoryEventEntry {
  return createMock<HistoryEventEntry>({ identifier });
}

describe('useHistoryEventsSelectionMode', () => {
  it('should start inactive with an empty selection', () => {
    const { state } = useHistoryEventsSelectionMode();
    expect(get(state)).toMatchObject({
      hasAvailableEvents: false,
      isActive: false,
      isAllSelected: false,
      isPartiallySelected: false,
      selectAllMatching: false,
      selectedCount: 0,
    });
    expect(get(state).selectedIds.size).toBe(0);
  });

  it('should toggle selection mode on and off, clearing on exit', () => {
    const { actions, isSelectionMode, state } = useHistoryEventsSelectionMode();
    actions.toggle();
    expect(get(isSelectionMode)).toBe(true);

    actions.toggleEvent(1);
    expect(get(state).selectedCount).toBe(1);

    // toggling off clears the selection
    actions.toggle();
    expect(get(isSelectionMode)).toBe(false);
    expect(get(state).selectedCount).toBe(0);
  });

  it('should toggle individual events', () => {
    const { actions, isEventSelected, getSelectedIds } = useHistoryEventsSelectionMode();
    actions.toggleEvent(1);
    actions.toggleEvent(2);
    expect(getSelectedIds().sort()).toEqual([1, 2]);
    expect(isEventSelected(1)).toBe(true);

    actions.toggleEvent(1);
    expect(getSelectedIds()).toEqual([2]);
    expect(isEventSelected(1)).toBe(false);
  });

  it('should report all/partial selection against the available ids', () => {
    const { actions, setAvailableIds, state } = useHistoryEventsSelectionMode();
    setAvailableIds([event(1), event(2), event(3)]);
    expect(get(state).hasAvailableEvents).toBe(true);

    actions.toggleEvent(1);
    expect(get(state).isPartiallySelected).toBe(true);
    expect(get(state).isAllSelected).toBe(false);

    actions.toggleAll();
    expect(get(state).isAllSelected).toBe(true);
    expect(get(state).isPartiallySelected).toBe(false);
    expect(get(state).selectedCount).toBe(3);

    // toggleAll again clears when everything is selected
    actions.toggleAll();
    expect(get(state).selectedCount).toBe(0);
  });

  it('should toggle a swap group as a unit', () => {
    const { actions, getSelectedIds } = useHistoryEventsSelectionMode();
    actions.toggleSwap([1, 2, 3]);
    expect(getSelectedIds().sort()).toEqual([1, 2, 3]);

    // all present -> removes the whole group
    actions.toggleSwap([1, 2, 3]);
    expect(getSelectedIds()).toEqual([]);

    // partial presence -> adds the missing ones
    actions.toggleEvent(1);
    actions.toggleSwap([1, 2]);
    expect(getSelectedIds().sort()).toEqual([1, 2]);
  });

  it('should handle select-all-matching and disable it on manual toggles', () => {
    const { actions, isSelectAllMatching, setTotalMatchingCount, state } = useHistoryEventsSelectionMode();
    setTotalMatchingCount(42);
    actions.toggleSelectAllMatching();
    expect(get(isSelectAllMatching)).toBe(true);
    expect(get(state).selectedCount).toBe(42);

    // manually toggling an event turns off select-all-matching
    actions.toggleEvent(1);
    expect(get(isSelectAllMatching)).toBe(false);
  });

  it('should treat every event as selected while select-all-matching is on', () => {
    const { actions, isEventSelected } = useHistoryEventsSelectionMode();
    actions.toggleSelectAllMatching();
    expect(isEventSelected(999)).toBe(true);
  });

  it('should clear select-all-matching when toggled off', () => {
    const { actions, isSelectAllMatching, getSelectedIds } = useHistoryEventsSelectionMode();
    actions.toggleEvent(1);
    actions.toggleSelectAllMatching();
    actions.toggleSelectAllMatching();
    expect(get(isSelectAllMatching)).toBe(false);
    expect(getSelectedIds()).toEqual([]);
  });

  it('should exit and reset every piece of state', () => {
    const { actions, setAvailableIds, isSelectionMode, state } = useHistoryEventsSelectionMode();
    setAvailableIds([event(1)]);
    actions.toggle();
    actions.toggleEvent(1);
    actions.exit();
    expect(get(isSelectionMode)).toBe(false);
    expect(get(state).selectedCount).toBe(0);
  });
});
