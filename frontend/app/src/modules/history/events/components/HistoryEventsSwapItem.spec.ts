import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import HistoryEventsSwapItem from '@/modules/history/events/components/HistoryEventsSwapItem.vue';
import HistoryEventType from '@/modules/history/events/HistoryEventType.vue';

function swapLeg(identifier: number, eventSubtype: 'spend' | 'receive', asset: string): HistoryEventEntry {
  return createMock<HistoryEventEntry>({
    amount: bigNumberify('1'),
    asset,
    entryType: HistoryEventEntryType.SWAP_EVENT,
    eventSubtype,
    eventType: 'trade',
    groupIdentifier: 'swap1',
    hidden: false,
    identifier,
    ignoredInAccounting: false,
    location: 'kraken',
    sequenceIndex: identifier,
    states: [],
  });
}

const events = [swapLeg(1, 'spend', 'ETH'), swapLeg(2, 'receive', 'USD')];

function mountItem(variant: 'row' | 'card'): VueWrapper {
  return mount(HistoryEventsSwapItem, {
    global: {
      plugins: [createCustomPinia()],
      provide: libraryDefaults,
      // `shallow` would stub the component under test too; only its children should be stubs.
      stubs: { HistoryEventsSwapItem: false },
    },
    props: { completeGroupEvents: events, events, variant },
    shallow: true,
  });
}

describe('modules/history/events/components/HistoryEventsSwapItem', () => {
  it.each(['row', 'card'] as const)('should render the collapsed %s type as neutral', (variant) => {
    const wrapper = mountItem(variant);

    expect(wrapper.findComponent(HistoryEventType).props('neutral')).toBe(true);
  });
});
