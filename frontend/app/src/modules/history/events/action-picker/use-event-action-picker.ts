import type { HistoryEventEntryType } from '@rotki/common';
import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { EventTypeCombination } from '@/modules/history/events/event-type';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

export interface EventActionRow {
  readonly verbKey: string;
  readonly label: string;
  readonly icon: RuiIcons;
  readonly direction: 'in' | 'out' | 'neutral';
  readonly groupId: string;
  readonly combinations: readonly EventTypeCombination[];
}

interface UseEventActionPickerReturn {
  readonly rows: ComputedRef<readonly EventActionRow[]>;
  readonly findRowByTypeSubtype: (eventType: string, eventSubtype: string) => EventActionRow | undefined;
}

/**
 * Builds the verb-based picker model from the backend-driven mappings. Iterates
 * the verbs exposed by `eventCategoryDetails` and joins each one with the
 * `(eventType, eventSubtype)` pairs that resolve to it, producing one row per
 * verb. Rows are pre-sorted by the backend's `eventCategoryGroups[groupId].order`
 * so RuiAutoComplete's group bucketing follows the curated order.
 *
 * When `entryType` is supplied, rows are restricted to combinations the entry
 * type actually accepts (currently only meaningful for ETH_WITHDRAWAL_EVENT).
 */
export function useEventActionPicker(
  entryType?: MaybeRefOrGetter<HistoryEventEntryType | undefined>,
): UseEventActionPickerReturn {
  const {
    eventTypeCombinationsByVerb,
    historyEventTypeData,
    transactionEventTypesData,
  } = useHistoryEventMappings();

  const allowedCombinationFilter = computed<((c: EventTypeCombination) => boolean) | undefined>(() => {
    const value = toValue(entryType);
    if (!value)
      return undefined;

    const mapping = get(historyEventTypeData).entryTypeMappings[value];
    if (!mapping)
      return undefined;

    return (combination: EventTypeCombination): boolean => {
      const subtypeMap = mapping[combination.eventType];
      return !!subtypeMap && combination.eventSubtype in subtypeMap;
    };
  });

  const rows = computed<readonly EventActionRow[]>(() => {
    const combinationsByVerb = get(eventTypeCombinationsByVerb);
    const details = get(transactionEventTypesData);
    const groups = get(historyEventTypeData).eventCategoryGroups;
    const filter = get(allowedCombinationFilter);
    const out: EventActionRow[] = [];

    for (const verbKey in details) {
      const detail = details[verbKey];
      const defaultDetail = detail.counterpartyMappings.default;
      if (!defaultDetail)
        continue;

      const rawCombinations = combinationsByVerb[verbKey] ?? [];
      const combinations = filter ? rawCombinations.filter(filter) : rawCombinations;
      if (combinations.length === 0)
        continue;

      out.push({
        combinations,
        direction: detail.direction,
        groupId: detail.group,
        icon: defaultDetail.icon,
        label: defaultDetail.label,
        verbKey,
      });
    }

    return out.sort((a, b) => {
      const orderDiff = (groups[a.groupId]?.order ?? Number.MAX_SAFE_INTEGER)
        - (groups[b.groupId]?.order ?? Number.MAX_SAFE_INTEGER);
      return orderDiff !== 0 ? orderDiff : a.label.localeCompare(b.label);
    });
  });

  function findRowByTypeSubtype(eventType: string, eventSubtype: string): EventActionRow | undefined {
    return get(rows).find(row =>
      row.combinations.some(c => c.eventType === eventType && c.eventSubtype === eventSubtype),
    );
  }

  return {
    findRowByTypeSubtype,
    rows,
  };
}
