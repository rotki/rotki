import type { EventActionRow } from '@/modules/history/events/action-picker/use-event-action-picker';
import type { EventTypeCombination } from '@/modules/history/events/event-type';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref, shallowRef } from 'vue';
import { combinationKey, useEventActionSelection } from '@/modules/history/events/action-picker/use-event-action-selection';

function buildRow(verbKey: string, combinations: EventTypeCombination[]): EventActionRow {
  return {
    combinations,
    direction: 'neutral',
    groupId: 'trade',
    icon: 'lu-coins',
    label: verbKey,
    verbKey,
  };
}

const receiveRow = buildRow('receive', [
  { eventSubtype: 'receive wrapped', eventType: 'receive' },
  { eventSubtype: 'return wrapped', eventType: 'receive' },
  { eventSubtype: 'none', eventType: 'receive' },
]);

const swapOutRow = buildRow('swap out', [{ eventSubtype: 'spend', eventType: 'trade' }]);

const rowsRef = shallowRef<readonly EventActionRow[]>([]);

vi.mock('@/modules/history/events/action-picker/use-event-action-picker', () => ({
  useEventActionPicker: (): unknown => ({
    findRowByTypeSubtype: (eventType: string, eventSubtype: string): EventActionRow | undefined =>
      rowsRef.value.find(row => row.combinations.some(c => c.eventType === eventType && c.eventSubtype === eventSubtype)),
    rows: rowsRef,
  }),
}));

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: (): unknown => ({
    getHistoryEventSubTypeName: (subtype: string): string => `Sub ${subtype}`,
    getHistoryEventTypeName: (type: string): string => `Type ${type}`,
  }),
}));

describe('useEventActionSelection', () => {
  beforeEach(() => {
    rowsRef.value = [swapOutRow, receiveRow];
  });

  it('should build the key from the event type and subtype', () => {
    expect(combinationKey({ eventSubtype: 'receive wrapped', eventType: 'receive' })).toBe('receive:receive wrapped');
  });

  it('should resolve the row that holds the stored pair', () => {
    const model = ref<EventTypeCombination | undefined>({ eventSubtype: 'none', eventType: 'receive' });
    const { selectedRow } = useEventActionSelection(model);

    expect(selectedRow.value).toBe(receiveRow);
  });

  it('should list every pair of the selected row as a labelled option', () => {
    const model = ref<EventTypeCombination | undefined>({ eventSubtype: 'none', eventType: 'receive' });
    const { combinationOptions } = useEventActionSelection(model);

    expect(combinationOptions.value).toEqual([
      { key: 'receive:receive wrapped', label: 'Type receive · Sub receive wrapped' },
      { key: 'receive:return wrapped', label: 'Type receive · Sub return wrapped' },
      { key: 'receive:none', label: 'Type receive · Sub none' },
    ]);
  });

  it('should have no options when nothing is stored', () => {
    const model = ref<EventTypeCombination | undefined>(undefined);
    const { combinationOptions, selectedCombinationKey, selectedRow } = useEventActionSelection(model);

    expect(selectedRow.value).toBeUndefined();
    expect(combinationOptions.value).toEqual([]);
    expect(selectedCombinationKey.value).toBeUndefined();
  });

  it('should change the subtype within the selected row through the combination key', () => {
    const model = ref<EventTypeCombination | undefined>({ eventSubtype: 'none', eventType: 'receive' });
    const { selectedCombinationKey } = useEventActionSelection(model);

    expect(selectedCombinationKey.value).toBe('receive:none');

    selectedCombinationKey.value = 'receive:return wrapped';

    expect(model.value).toEqual({ eventSubtype: 'return wrapped', eventType: 'receive' });
  });

  it('should ignore a combination key that is not in the selected row', () => {
    const model = ref<EventTypeCombination | undefined>({ eventSubtype: 'none', eventType: 'receive' });
    const { selectedCombinationKey } = useEventActionSelection(model);

    selectedCombinationKey.value = 'trade:spend';

    expect(model.value).toEqual({ eventSubtype: 'none', eventType: 'receive' });
  });

  it('should keep the stored pair when its row is picked again', () => {
    const model = ref<EventTypeCombination | undefined>({ eventSubtype: 'return wrapped', eventType: 'receive' });
    const { selectRow } = useEventActionSelection(model);

    selectRow(receiveRow);

    expect(model.value).toEqual({ eventSubtype: 'return wrapped', eventType: 'receive' });
  });

  it('should store the first pair of a newly picked row', () => {
    const model = ref<EventTypeCombination | undefined>({ eventSubtype: 'spend', eventType: 'trade' });
    const { selectRow } = useEventActionSelection(model);

    selectRow(receiveRow);

    expect(model.value).toEqual({ eventSubtype: 'receive wrapped', eventType: 'receive' });
  });

  it('should leave the model alone when the picked row has no pairs', () => {
    const model = ref<EventTypeCombination | undefined>({ eventSubtype: 'spend', eventType: 'trade' });
    const { selectRow } = useEventActionSelection(model);

    selectRow(buildRow('empty', []));

    expect(model.value).toEqual({ eventSubtype: 'spend', eventType: 'trade' });
  });

  it('should clear a stored pair that no row maps to once rows are loaded', async () => {
    rowsRef.value = [];
    const model = ref<EventTypeCombination | undefined>({ eventSubtype: 'unknown', eventType: 'receive' });
    useEventActionSelection(model);
    rowsRef.value = [swapOutRow, receiveRow];
    await nextTick();

    expect(model.value).toBeUndefined();
  });

  it('should keep an unmapped pair while the rows are still empty', async () => {
    rowsRef.value = [];
    const model = ref<EventTypeCombination | undefined>({ eventSubtype: 'unknown', eventType: 'receive' });
    useEventActionSelection(model);
    rowsRef.value = [];
    await nextTick();

    expect(model.value).toEqual({ eventSubtype: 'unknown', eventType: 'receive' });
  });
});
