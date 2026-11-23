import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import CostBasisOverlayCell from '@/modules/history/cost-basis/CostBasisOverlayCell.vue';
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

function mountItem(variant: 'row' | 'card', swapEvents: HistoryEventEntry[] = events): VueWrapper {
  return mount(HistoryEventsSwapItem, {
    global: {
      plugins: [createCustomPinia()],
      provide: libraryDefaults,
      // `shallow` would stub the component under test too; only its children should be stubs.
      stubs: { HistoryEventsSwapItem: false },
    },
    props: { completeGroupEvents: swapEvents, events: swapEvents, variant },
    shallow: true,
  });
}

/** The identifiers of what the swap hands its cost basis cell. */
function costBasisCellIdentifiers(wrapper: VueWrapper): { event?: number; fallback?: number; siblings?: number[] } {
  const cell = wrapper.findComponent(CostBasisOverlayCell);
  expect(cell.exists()).toBe(true);
  return {
    event: cell.props('event').identifier,
    fallback: cell.props('fallbackEvent')?.identifier,
    siblings: cell.props('siblingEvents')?.map(({ identifier }) => identifier),
  };
}

describe('modules/history/events/components/HistoryEventsSwapItem', () => {
  it.each(['row', 'card'] as const)('should render the collapsed %s type as neutral', (variant) => {
    const wrapper = mountItem(variant);

    expect(wrapper.findComponent(HistoryEventType).props('neutral')).toBe(true);
  });

  it('should give the cost basis cell the spend, the receive to fall back on and the other spends', () => {
    const extraSpend = swapLeg(3, 'spend', 'USDC');
    expect(costBasisCellIdentifiers(mountItem('row', [events[0], extraSpend, events[1]])))
      .toEqual({ event: 1, fallback: 2, siblings: [3] });
  });

  it('should show the receive in the cost basis cell of a swap without a spend', () => {
    const { event, fallback, siblings } = costBasisCellIdentifiers(mountItem('row', [events[1]]));
    expect(event).toBe(2);
    expect(fallback).toBeUndefined();
    expect(siblings ?? []).toEqual([]);
  });
});
