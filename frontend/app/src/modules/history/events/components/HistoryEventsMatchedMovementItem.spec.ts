import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import HistoryEventsMatchedMovementItem from '@/modules/history/events/components/HistoryEventsMatchedMovementItem.vue';
import HistoryEventType from '@/modules/history/events/HistoryEventType.vue';

function movementLeg(identifier: number, entryType: HistoryEventEntryType, location: string): HistoryEventEntry {
  return createMock<HistoryEventEntry>({
    amount: bigNumberify('2'),
    asset: 'ETH',
    entryType,
    eventSubtype: 'deposit asset',
    eventType: 'deposit',
    groupIdentifier: 'move1',
    hidden: false,
    identifier,
    ignoredInAccounting: false,
    location,
    sequenceIndex: 0,
    states: [],
  });
}

const events = [
  movementLeg(1, HistoryEventEntryType.ASSET_MOVEMENT_EVENT, 'kraken'),
  movementLeg(2, HistoryEventEntryType.EVM_EVENT, 'ethereum'),
];

function mountItem(variant: 'row' | 'card'): VueWrapper {
  return mount(HistoryEventsMatchedMovementItem, {
    global: {
      plugins: [createCustomPinia()],
      provide: libraryDefaults,
      // `shallow` would stub the component under test too; only its children should be stubs.
      stubs: { HistoryEventsMatchedMovementItem: false },
    },
    props: { completeGroupEvents: events, events, variant },
    shallow: true,
  });
}

describe('modules/history/events/components/HistoryEventsMatchedMovementItem', () => {
  it.each(['row', 'card'] as const)('should render the collapsed %s type as neutral', (variant) => {
    const wrapper = mountItem(variant);

    expect(wrapper.findComponent(HistoryEventType).props('neutral')).toBe(true);
  });
});
