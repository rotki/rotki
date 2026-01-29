import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { type ComponentMountingOptions, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type AssetMovementEvent, type EvmHistoryEvent, type EvmSwapEvent, HistoryEventAccountingRuleStatus, type HistoryEventEntry } from '@/types/history/events/schemas';
import HistoryEventsListSubgroup from './HistoryEventsListSubgroup.vue';

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({
    getAssetSymbol: vi.fn((asset: string) => asset),
  })),
}));

vi.mock('@/composables/history/events/mapping', () => ({
  useHistoryEventMappings: vi.fn(() => ({
    getEventTypeData: vi.fn(() => ref({ icon: 'lu-arrow-right-left' })),
  })),
}));

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChain: vi.fn(() => 'ethereum'),
  })),
}));

const BASE_EVENT = {
  amount: bigNumberify('100'),
  asset: 'ETH',
  states: [],
  eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
  groupIdentifier: 'group1',
  hidden: false,
  identifier: 1,
  ignoredInAccounting: false,
  location: 'ethereum',
  locationLabel: 'Account 1',
  sequenceIndex: 0,
  timestamp: 1000000,
};

const EVM_EVENT_EXTRAS = {
  address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
  counterparty: null,
  extraData: null,
  txRef: '0x123',
};

function createEvmSwapEvent(overrides: Partial<EvmSwapEvent> = {}): HistoryEventEntry {
  return {
    ...BASE_EVENT,
    ...EVM_EVENT_EXTRAS,
    entryType: HistoryEventEntryType.EVM_SWAP_EVENT,
    eventSubtype: 'spend',
    eventType: 'trade',
    ...overrides,
  };
}

function createAssetMovementEvent(overrides: Partial<AssetMovementEvent> = {}): HistoryEventEntry {
  return {
    ...BASE_EVENT,
    entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    eventSubtype: 'deposit',
    eventType: 'deposit',
    extraData: null,
    ...overrides,
  };
}

function createEvmEvent(overrides: Partial<EvmHistoryEvent> = {}): HistoryEventEntry {
  return {
    ...BASE_EVENT,
    ...EVM_EVENT_EXTRAS,
    entryType: HistoryEventEntryType.EVM_EVENT,
    eventSubtype: 'fee',
    eventType: 'spend',
    ...overrides,
  };
}

function createMockSelectionMode(isActive: boolean): UseHistoryEventsSelectionModeReturn {
  return {
    actions: {
      clear: vi.fn(),
      exit: vi.fn(),
      toggle: vi.fn(),
      toggleAll: vi.fn(),
      toggleEvent: vi.fn(),
      toggleSwap: vi.fn(),
      toggleSelectAllMatching: vi.fn(),
    },
    setTotalMatchingCount: vi.fn(),
    isSelectAllMatching: ref<boolean>(false),
    getSelectedIds: vi.fn(() => []),
    isEventSelected: vi.fn(() => false),
    isSelectionMode: ref<boolean>(isActive),
    selectedEvents: ref<Set<number>>(new Set()),
    setAvailableIds: vi.fn(),
    state: computed(() => ({
      hasAvailableEvents: false,
      isActive,
      isAllSelected: false,
      isPartiallySelected: false,
      selectedCount: 0,
      selectedIds: new Set<number>(),
      selectAllMatching: false,
      totalMatchingCount: 0,
    })),
  };
}

describe('historyEventsListSubgroup', () => {
  function createWrapper(options: ComponentMountingOptions<typeof HistoryEventsListSubgroup> = {}): ReturnType<typeof mount<typeof HistoryEventsListSubgroup>> {
    return mount(HistoryEventsListSubgroup, {
      global: {
        stubs: {
          HistoryEventNote: true,
          HistoryEventType: true,
          HistoryEventsListItem: {
            props: ['item'],
            template: '<div class="mock-item" :data-id="item.identifier" :data-subtype="item.eventSubtype" />',
          },
          HistoryEventsListItemAction: true,
          RuiButton: true,
          RuiIcon: true,
        },
      },
      ...options,
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('usedEvents computed - swap groups', () => {
    it('returns all events when expanded via selection mode', () => {
      const events: HistoryEventEntry[] = [
        createEvmSwapEvent({ eventSubtype: 'spend', identifier: 1 }),
        createEvmSwapEvent({ eventSubtype: 'receive', identifier: 2 }),
        createEvmSwapEvent({ eventSubtype: 'fee', identifier: 3 }),
      ];

      const wrapper = createWrapper({
        props: {
          allEvents: events,
          events,
          isLast: false,
          selection: createMockSelectionMode(true),
        },
      });

      const items = wrapper.findAll('.mock-item');
      // When expanded, all events including fee should be shown
      expect(items).toHaveLength(3);
    });

    it('filters out fee events and alternates spend/receive when collapsed', () => {
      const events: HistoryEventEntry[] = [
        createEvmSwapEvent({ eventSubtype: 'spend', identifier: 1 }),
        createEvmSwapEvent({ eventSubtype: 'receive', identifier: 2 }),
        createEvmSwapEvent({ eventSubtype: 'fee', identifier: 3 }),
      ];

      const wrapper = createWrapper({
        props: {
          allEvents: events,
          events,
          isLast: false,
        },
      });

      const items = wrapper.findAll('.mock-item');
      // Should only show spend and receive, not fee
      expect(items).toHaveLength(2);
      expect(items[0].attributes('data-subtype')).toBe('spend');
      expect(items[1].attributes('data-subtype')).toBe('receive');
    });

    it('alternates multiple spend/receive pairs correctly', () => {
      const events: HistoryEventEntry[] = [
        createEvmSwapEvent({ eventSubtype: 'spend', identifier: 1 }),
        createEvmSwapEvent({ eventSubtype: 'spend', identifier: 2 }),
        createEvmSwapEvent({ eventSubtype: 'receive', identifier: 3 }),
        createEvmSwapEvent({ eventSubtype: 'receive', identifier: 4 }),
      ];

      const wrapper = createWrapper({
        props: {
          allEvents: events,
          events,
          isLast: false,
        },
      });

      const items = wrapper.findAll('.mock-item');
      expect(items).toHaveLength(4);
      // Should alternate: spend, receive, spend, receive
      expect(items[0].attributes('data-subtype')).toBe('spend');
      expect(items[1].attributes('data-subtype')).toBe('receive');
      expect(items[2].attributes('data-subtype')).toBe('spend');
      expect(items[3].attributes('data-subtype')).toBe('receive');
    });

    it('handles more spend events than receive events', () => {
      const events: HistoryEventEntry[] = [
        createEvmSwapEvent({ eventSubtype: 'spend', identifier: 1 }),
        createEvmSwapEvent({ eventSubtype: 'spend', identifier: 2 }),
        createEvmSwapEvent({ eventSubtype: 'spend', identifier: 3 }),
        createEvmSwapEvent({ eventSubtype: 'receive', identifier: 4 }),
      ];

      const wrapper = createWrapper({
        props: {
          allEvents: events,
          events,
          isLast: false,
        },
      });

      const items = wrapper.findAll('.mock-item');
      expect(items).toHaveLength(4);
      // First pair alternates, then remaining spend events
      expect(items[0].attributes('data-subtype')).toBe('spend');
      expect(items[1].attributes('data-subtype')).toBe('receive');
      expect(items[2].attributes('data-subtype')).toBe('spend');
      expect(items[3].attributes('data-subtype')).toBe('spend');
    });

    it('handles more receive events than spend events', () => {
      const events: HistoryEventEntry[] = [
        createEvmSwapEvent({ eventSubtype: 'spend', identifier: 1 }),
        createEvmSwapEvent({ eventSubtype: 'receive', identifier: 2 }),
        createEvmSwapEvent({ eventSubtype: 'receive', identifier: 3 }),
        createEvmSwapEvent({ eventSubtype: 'receive', identifier: 4 }),
      ];

      const wrapper = createWrapper({
        props: {
          allEvents: events,
          events,
          isLast: false,
        },
      });

      const items = wrapper.findAll('.mock-item');
      expect(items).toHaveLength(4);
      // First pair alternates, then remaining receive events
      expect(items[0].attributes('data-subtype')).toBe('spend');
      expect(items[1].attributes('data-subtype')).toBe('receive');
      expect(items[2].attributes('data-subtype')).toBe('receive');
      expect(items[3].attributes('data-subtype')).toBe('receive');
    });

    it('handles only spend events (no receive)', () => {
      const events: HistoryEventEntry[] = [
        createEvmSwapEvent({ eventSubtype: 'spend', identifier: 1 }),
        createEvmSwapEvent({ eventSubtype: 'spend', identifier: 2 }),
        createEvmSwapEvent({ eventSubtype: 'fee', identifier: 3 }),
      ];

      const wrapper = createWrapper({
        props: {
          allEvents: events,
          events,
          isLast: false,
        },
      });

      const items = wrapper.findAll('.mock-item');
      expect(items).toHaveLength(2);
      expect(items[0].attributes('data-subtype')).toBe('spend');
      expect(items[1].attributes('data-subtype')).toBe('spend');
    });

    it('handles only receive events (no spend)', () => {
      const events: HistoryEventEntry[] = [
        createEvmSwapEvent({ eventSubtype: 'receive', identifier: 1 }),
        createEvmSwapEvent({ eventSubtype: 'receive', identifier: 2 }),
      ];

      const wrapper = createWrapper({
        props: {
          allEvents: events,
          events,
          isLast: false,
        },
      });

      const items = wrapper.findAll('.mock-item');
      expect(items).toHaveLength(2);
      expect(items[0].attributes('data-subtype')).toBe('receive');
      expect(items[1].attributes('data-subtype')).toBe('receive');
    });
  });

  describe('usedEvents computed - non-swap groups', () => {
    it('returns only primary event for asset movement groups when collapsed', () => {
      const events: HistoryEventEntry[] = [
        createAssetMovementEvent({ eventSubtype: 'deposit', identifier: 1 }),
        createEvmEvent({ eventSubtype: 'fee', identifier: 2 }),
      ];

      const wrapper = createWrapper({
        props: {
          allEvents: events,
          events,
          isLast: false,
        },
      });

      const items = wrapper.findAll('.mock-item');
      // Should only show the primary asset movement event
      expect(items).toHaveLength(1);
      expect(items[0].attributes('data-id')).toBe('1');
    });
  });
});
