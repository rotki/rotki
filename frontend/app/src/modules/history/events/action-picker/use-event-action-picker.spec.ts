import type { EventCategoryGroupDetail, EventTypeCombination, HistoryEventCategoryMapping } from '@/modules/history/events/event-type';
import { HistoryEventEntryType } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, ref } from 'vue';
import { useEventActionPicker } from '@/modules/history/events/action-picker/use-event-action-picker';

const eventTypeCombinationsByVerb = ref<Record<string, EventTypeCombination[]>>({});
const transactionEventTypesData = ref<HistoryEventCategoryMapping>({});
const entryTypeMappings = ref<Record<string, Record<string, Record<string, string>>>>({});
const eventCategoryGroups = ref<Record<string, EventCategoryGroupDetail>>({});

vi.mock('@/modules/history/events/mapping/use-history-event-mappings', () => ({
  useHistoryEventMappings: (): unknown => ({
    eventTypeCombinationsByVerb: computed(() => eventTypeCombinationsByVerb.value),
    historyEventTypeData: computed(() => ({
      entryTypeMappings: entryTypeMappings.value,
      eventCategoryGroups: eventCategoryGroups.value,
    })),
    transactionEventTypesData: computed(() => transactionEventTypesData.value),
  }),
}));

function setMappings(options: {
  combinations: Record<string, EventTypeCombination[]>;
  details: HistoryEventCategoryMapping;
  entryTypeMappings?: Record<string, Record<string, Record<string, string>>>;
  groups?: Record<string, EventCategoryGroupDetail>;
}): void {
  eventTypeCombinationsByVerb.value = options.combinations;
  transactionEventTypesData.value = options.details;
  entryTypeMappings.value = options.entryTypeMappings ?? {};
  eventCategoryGroups.value = options.groups ?? { expense: { icon: 'lu-receipt', order: 70 }, trade: { icon: 'lu-arrow-left-right', order: 10 } };
}

function buildDetails(verbs: Record<string, { label: string; direction?: 'in' | 'out' | 'neutral'; group?: string }>): HistoryEventCategoryMapping {
  const result: HistoryEventCategoryMapping = {};
  for (const verbKey in verbs) {
    const { direction = 'neutral', group = 'trade', label } = verbs[verbKey];
    result[verbKey] = {
      counterpartyMappings: { default: { icon: 'lu-coins', label } },
      direction,
      group,
    };
  }
  return result;
}

describe('useEventActionPicker', () => {
  beforeEach(() => {
    setMappings({ combinations: {}, details: {} });
  });

  it('should produce one row per verb joined with its combinations', () => {
    setMappings({
      combinations: {
        'swap in': [{ eventSubtype: 'receive', eventType: 'trade' }],
        'swap out': [{ eventSubtype: 'spend', eventType: 'trade' }],
      },
      details: buildDetails({
        'swap in': { direction: 'in', group: 'trade', label: 'Swap in' },
        'swap out': { direction: 'out', group: 'trade', label: 'Swap out' },
      }),
    });

    const { rows } = useEventActionPicker();
    expect(rows.value.map(r => r.verbKey).sort()).toEqual(['swap in', 'swap out']);
    expect(rows.value.find(r => r.verbKey === 'swap out')?.direction).toBe('out');
    expect(rows.value.find(r => r.verbKey === 'swap in')?.groupId).toBe('trade');
  });

  it('should skip verbs that have no combinations', () => {
    setMappings({
      combinations: { 'swap in': [{ eventSubtype: 'receive', eventType: 'trade' }] },
      details: buildDetails({ 'swap in': { label: 'Swap in' }, 'unused verb': { label: 'Unused' } }),
    });

    const { rows } = useEventActionPicker();
    expect(rows.value).toHaveLength(1);
    expect(rows.value[0].verbKey).toBe('swap in');
  });

  it('should pre-sort rows by the backend-supplied group order', () => {
    setMappings({
      combinations: {
        'fee': [{ eventSubtype: 'fee', eventType: 'spend' }],
        'swap out': [{ eventSubtype: 'spend', eventType: 'trade' }],
      },
      details: buildDetails({
        'fee': { group: 'expense', label: 'fee' },
        'swap out': { group: 'trade', label: 'Swap out' },
      }),
    });

    const { rows } = useEventActionPicker();
    expect(rows.value.map(r => r.verbKey)).toEqual(['swap out', 'fee']);
  });

  it('should place verbs whose group is unknown at the end', () => {
    setMappings({
      combinations: {
        'mystery': [{ eventSubtype: 'm', eventType: 'm' }],
        'swap out': [{ eventSubtype: 'spend', eventType: 'trade' }],
      },
      details: buildDetails({
        'mystery': { group: 'unknown_group', label: 'Mystery' },
        'swap out': { group: 'trade', label: 'Swap out' },
      }),
    });

    const { rows } = useEventActionPicker();
    expect(rows.value.map(r => r.verbKey)).toEqual(['swap out', 'mystery']);
  });

  it('should narrow combinations by entryType when entryTypeMappings has an entry', () => {
    const entryType = HistoryEventEntryType.ETH_WITHDRAWAL_EVENT;
    setMappings({
      combinations: {
        'swap out': [{ eventSubtype: 'spend', eventType: 'trade' }],
        'unstake': [{ eventSubtype: 'remove asset', eventType: 'staking' }],
      },
      details: buildDetails({ 'swap out': { label: 'Swap out' }, 'unstake': { label: 'Unstake' } }),
      entryTypeMappings: { [entryType]: { staking: { 'remove asset': 'unstake' } } },
    });

    const { rows } = useEventActionPicker(() => entryType);
    expect(rows.value.map(r => r.verbKey)).toEqual(['unstake']);
  });

  it('should return all rows when entryType has no mapping entry', () => {
    setMappings({
      combinations: {
        'swap out': [{ eventSubtype: 'spend', eventType: 'trade' }],
      },
      details: buildDetails({ 'swap out': { label: 'Swap out' } }),
    });

    const { rows } = useEventActionPicker(() => HistoryEventEntryType.EVM_EVENT);
    expect(rows.value).toHaveLength(1);
  });

  it('should find a row from a (type, subtype) pair', () => {
    setMappings({
      combinations: {
        'swap out': [{ eventSubtype: 'spend', eventType: 'trade' }],
      },
      details: buildDetails({ 'swap out': { label: 'Swap out' } }),
    });

    const { findRowByTypeSubtype } = useEventActionPicker();
    expect(findRowByTypeSubtype('trade', 'spend')?.verbKey).toBe('swap out');
    expect(findRowByTypeSubtype('trade', 'receive')).toBeUndefined();
  });
});
