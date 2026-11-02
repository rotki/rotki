import type { ComputedRef } from 'vue';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { shallowMount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import HistoryEventsGroupItem from '@/modules/history/events/components/HistoryEventsGroupItem.vue';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntry } from '@/modules/history/events/schemas';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

vi.mock('@/modules/history/events/use-event-redecode-status', () => ({
  useEventRedecodeStatus: (): ComputedRef<boolean> => computed<boolean>(() => false),
}));

const bankEvent: HistoryEventEntry = {
  amount: bigNumberify(1),
  asset: 'EUR',
  entryType: HistoryEventEntryType.BANK_TRANSACTION_EVENT,
  eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
  eventSubtype: 'none',
  eventType: 'receive',
  extraData: {
    bankAccountId: 'account-1',
    calendarDate: '2026-11-02',
    kind: 'transfer',
  },
  groupIdentifier: 'bank-event-1',
  identifier: 1,
  location: 'fints',
  locationLabel: 'My DKB',
  sequenceIndex: 0,
  timestamp: Date.UTC(2026, 10, 2),
};

describe('historyEventsGroupItem', () => {
  it('should display date-only bank transactions without a time', () => {
    const wrapper = shallowMount(HistoryEventsGroupItem, {
      props: { group: bankEvent },
    });
    const date = wrapper.getComponent(DateDisplay);

    expect(date.props('calendarDate')).toBe('2026-11-02');
    expect(date.props('noTime')).toBe(true);
  });

  it('should infer the calendar date for existing FinTS midnight events', () => {
    const wrapper = shallowMount(HistoryEventsGroupItem, {
      props: {
        group: {
          ...bankEvent,
          extraData: { bankAccountId: 'account-1', kind: 'transfer' },
        },
      },
    });
    const date = wrapper.getComponent(DateDisplay);

    expect(date.props('calendarDate')).toBe('2026-11-02');
    expect(date.props('noTime')).toBe(true);
  });
});
