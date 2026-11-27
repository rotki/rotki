import type { HistoryEventEntryType } from '@rotki/common';
import type { EventTypeCombination } from '@/modules/history/events/event-type';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, type Ref, watch, type WritableComputedRef } from 'vue';
import { type EventActionRow, useEventActionPicker } from '@/modules/history/events/action-picker/use-event-action-picker';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

interface CombinationOption {
  readonly key: string;
  readonly label: string;
}

interface UseEventActionSelectionReturn {
  readonly rows: ComputedRef<readonly EventActionRow[]>;
  readonly selectedRow: ComputedRef<EventActionRow | undefined>;
  readonly combinationOptions: ComputedRef<CombinationOption[]>;
  readonly selectedCombinationKey: WritableComputedRef<string | undefined>;
  readonly combinationLabel: (combination: EventTypeCombination) => string;
  readonly selectRow: (row: EventActionRow) => void;
}

export function combinationKey(combination: EventTypeCombination): string {
  return `${combination.eventType}:${combination.eventSubtype}`;
}

/**
 * Ties the picker rows to the stored (eventType, eventSubtype) pair. A row
 * groups every pair that shares an action, e.g. Receive covers receive/none,
 * receive/receive wrapped and receive/return wrapped. Accounting tells them
 * apart, so the exact pair stays pickable within the selected row.
 */
export function useEventActionSelection(
  modelValue: Ref<EventTypeCombination | undefined>,
  entryType?: MaybeRefOrGetter<HistoryEventEntryType | undefined>,
  location?: MaybeRefOrGetter<string | null | undefined>,
): UseEventActionSelectionReturn {
  const { findRowByTypeSubtype, rows } = useEventActionPicker(entryType, location);
  const { getHistoryEventSubTypeName, getHistoryEventTypeName } = useHistoryEventMappings();

  const selectedRow = computed<EventActionRow | undefined>(() => {
    const value = get(modelValue);
    if (!value)
      return undefined;

    return findRowByTypeSubtype(value.eventType, value.eventSubtype);
  });

  const combinationOptions = computed<CombinationOption[]>(() =>
    get(selectedRow)?.combinations.map(combination => ({
      key: combinationKey(combination),
      label: combinationLabel(combination),
    })) ?? [],
  );

  const selectedCombinationKey = computed<string | undefined>({
    get: () => {
      const value = get(modelValue);
      return value ? combinationKey(value) : undefined;
    },
    set: (key) => {
      const combination = get(selectedRow)?.combinations.find(item => combinationKey(item) === key);
      if (combination)
        set(modelValue, { eventSubtype: combination.eventSubtype, eventType: combination.eventType });
    },
  });

  function combinationLabel(combination: EventTypeCombination): string {
    return `${getHistoryEventTypeName(combination.eventType)} · ${getHistoryEventSubTypeName(combination.eventSubtype)}`;
  }

  /**
   * Keeps the stored pair when it already belongs to the picked row, so
   * re-picking the current action never resets a chosen subtype. Otherwise
   * the row's first pair is stored.
   */
  function selectRow(row: EventActionRow): void {
    const current = get(modelValue);
    if (current && row.combinations.some(item => combinationKey(item) === combinationKey(current)))
      return;

    const first = row.combinations[0];
    if (first)
      set(modelValue, { eventSubtype: first.eventSubtype, eventType: first.eventType });
  }

  // Clear a pair no row can show (e.g. after an entry-type switch) so the required picker flags it.
  watch([selectedRow, rows], ([row, currentRows]) => {
    if (!get(modelValue) || row || currentRows.length === 0)
      return;

    set(modelValue, undefined);
  });

  return {
    combinationLabel,
    combinationOptions,
    rows,
    selectedCombinationKey,
    selectedRow,
    selectRow,
  };
}
