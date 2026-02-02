import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  type AssetMovementEvent,
  type EvmHistoryEvent,
  HistoryEventAccountingRuleStatus,
  type HistoryEventEntry,
} from '@/types/history/events/schemas';

import { useHistoryMatchedMovementItem } from './use-history-matched-movement-item';

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChain: vi.fn((location: string) => location),
  })),
}));

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({
    getAssetSymbol: vi.fn((asset: string) => asset.toUpperCase()),
  })),
}));

vi.mock('@/utils/history/events', () => ({
  isEventMissingAccountingRule: vi.fn((event: HistoryEventEntry) =>
    (event as any).eventAccountingRuleStatus === HistoryEventAccountingRuleStatus.NOT_PROCESSED),
}));

type MockEventOverrides = Partial<EvmHistoryEvent | AssetMovementEvent> & {
  eventAccountingRuleStatus?: HistoryEventAccountingRuleStatus;
};

function createMockEvent(
  entryType: HistoryEventEntryType = HistoryEventEntryType.EVM_EVENT,
  overrides: Omit<MockEventOverrides, 'entryType'> = {},
): HistoryEventEntry {
  const baseEvent = {
    identifier: 1,
    asset: 'ETH',
    amount: bigNumberify('1.5'),
    timestamp: 1700000000000,
    location: 'ethereum',
    eventType: 'deposit',
    eventSubtype: 'none',
    groupIdentifier: 'tx-123',
    locationLabel: null,
    sequenceIndex: 0,
    eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.HAS_RULE,
  };

  if (entryType === HistoryEventEntryType.EVM_EVENT) {
    return {
      ...baseEvent,
      entryType: HistoryEventEntryType.EVM_EVENT,
      address: null,
      counterparty: null,
      extraData: null,
      txRef: 'tx-ref-123',
      ...overrides,
    };
  }

  const assetMovementEvent: AssetMovementEvent & { eventAccountingRuleStatus: HistoryEventAccountingRuleStatus } = {
    ...baseEvent,
    entryType: HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    extraData: null as AssetMovementEvent['extraData'],
    ...overrides as Partial<AssetMovementEvent>,
  };
  return assetMovementEvent as HistoryEventEntry;
}

function createMatchedMovementEvents(): HistoryEventEntry[] {
  return [
    createMockEvent(HistoryEventEntryType.ASSET_MOVEMENT_EVENT, {
      identifier: 1,
      asset: 'ETH',
      amount: bigNumberify('1.0'),
      eventType: 'deposit',
      eventSubtype: 'none',
      location: 'kraken',
      locationLabel: 'Kraken Exchange',
    }),
    createMockEvent(HistoryEventEntryType.EVM_EVENT, {
      identifier: 2,
      asset: 'ETH',
      amount: bigNumberify('1.0'),
      eventType: 'spend',
      eventSubtype: 'none',
      location: 'ethereum',
      locationLabel: '0x1234...5678',
    }),
  ];
}

describe('useHistoryMatchedMovementItem', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('primaryEvent', () => {
    it('should return first non-fee asset movement event as primary', () => {
      const events = ref(createMatchedMovementEvents());
      const { primaryEvent } = useHistoryMatchedMovementItem({ events });

      expect(get(primaryEvent).entryType).toBe(HistoryEventEntryType.ASSET_MOVEMENT_EVENT);
      expect(get(primaryEvent).identifier).toBe(1);
    });

    it('should skip fee events when finding primary', () => {
      const events = ref([
        createMockEvent(HistoryEventEntryType.ASSET_MOVEMENT_EVENT, {
          identifier: 1,
          eventSubtype: 'fee',
        }),
        createMockEvent(HistoryEventEntryType.ASSET_MOVEMENT_EVENT, {
          identifier: 2,
          eventSubtype: 'none',
        }),
      ]);
      const { primaryEvent } = useHistoryMatchedMovementItem({ events });

      expect(get(primaryEvent).identifier).toBe(2);
    });

    it('should fallback to first event if no asset movement found', () => {
      const events = ref([
        createMockEvent(HistoryEventEntryType.EVM_EVENT, {
          identifier: 1,
        }),
      ]);
      const { primaryEvent } = useHistoryMatchedMovementItem({ events });

      expect(get(primaryEvent).identifier).toBe(1);
    });
  });

  describe('secondaryEvent', () => {
    it('should return non-asset-movement event as secondary', () => {
      const events = ref(createMatchedMovementEvents());
      const { secondaryEvent } = useHistoryMatchedMovementItem({ events });

      expect(get(secondaryEvent)?.entryType).toBe(HistoryEventEntryType.EVM_EVENT);
      expect(get(secondaryEvent)?.identifier).toBe(2);
    });

    it('should return undefined when no secondary event exists', () => {
      const events = ref([
        createMockEvent(HistoryEventEntryType.ASSET_MOVEMENT_EVENT, {
          identifier: 1,
        }),
      ]);
      const { secondaryEvent } = useHistoryMatchedMovementItem({ events });

      expect(get(secondaryEvent)).toBeUndefined();
    });
  });

  describe('chain', () => {
    it('should prefer secondary event location for chain', () => {
      const events = ref(createMatchedMovementEvents());
      const { chain } = useHistoryMatchedMovementItem({ events });

      expect(get(chain)).toBe('ethereum');
    });

    it('should use primary event location when no secondary', () => {
      const events = ref([
        createMockEvent(HistoryEventEntryType.ASSET_MOVEMENT_EVENT, {
          identifier: 1,
          location: 'kraken',
        }),
      ]);
      const { chain } = useHistoryMatchedMovementItem({ events });

      expect(get(chain)).toBe('kraken');
    });
  });

  describe('canUnlink', () => {
    it('should return true when primary event has actualGroupIdentifier', () => {
      const events = ref([
        createMockEvent(HistoryEventEntryType.ASSET_MOVEMENT_EVENT, {
          identifier: 1,
          actualGroupIdentifier: 'actual-group-123',
        }),
      ]);
      const { canUnlink } = useHistoryMatchedMovementItem({ events });

      expect(get(canUnlink)).toBe(true);
    });

    it('should return false when no actualGroupIdentifier', () => {
      const events = ref(createMatchedMovementEvents());
      const { canUnlink } = useHistoryMatchedMovementItem({ events });

      expect(get(canUnlink)).toBe(false);
    });
  });

  describe('movementEventIds', () => {
    it('should return all event identifiers', () => {
      const events = ref(createMatchedMovementEvents());
      const { movementEventIds } = useHistoryMatchedMovementItem({ events });

      expect(get(movementEventIds)).toEqual([1, 2]);
    });

    it('should update when events change', () => {
      const events = ref(createMatchedMovementEvents());
      const { movementEventIds } = useHistoryMatchedMovementItem({ events });

      expect(get(movementEventIds)).toEqual([1, 2]);

      set(events, [
        ...createMatchedMovementEvents(),
        createMockEvent(HistoryEventEntryType.EVM_EVENT, { identifier: 3, eventSubtype: 'fee' }),
      ]);

      expect(get(movementEventIds)).toEqual([1, 2, 3]);
    });
  });

  describe('eventTypeLabel', () => {
    it('should return deposit label for deposit events', () => {
      const events = ref([
        createMockEvent(HistoryEventEntryType.ASSET_MOVEMENT_EVENT, {
          identifier: 1,
          eventType: 'deposit',
        }),
      ]);
      const { eventTypeLabel } = useHistoryMatchedMovementItem({ events });

      // Since we're mocking t(), it will return the key
      expect(get(eventTypeLabel)).toBeDefined();
    });

    it('should return withdrawal label for withdrawal events', () => {
      const events = ref([
        createMockEvent(HistoryEventEntryType.ASSET_MOVEMENT_EVENT, {
          identifier: 1,
          eventType: 'withdrawal',
        }),
      ]);
      const { eventTypeLabel } = useHistoryMatchedMovementItem({ events });

      expect(get(eventTypeLabel)).toBeDefined();
    });
  });

  describe('selection state without selection prop', () => {
    it('should return false for showCheckbox', () => {
      const events = ref(createMatchedMovementEvents());
      const { showCheckbox } = useHistoryMatchedMovementItem({ events });

      expect(get(showCheckbox)).toBe(false);
    });

    it('should return false for isCheckboxDisabled', () => {
      const events = ref(createMatchedMovementEvents());
      const { isCheckboxDisabled } = useHistoryMatchedMovementItem({ events });

      expect(get(isCheckboxDisabled)).toBe(false);
    });

    it('should return false for isSelected', () => {
      const events = ref(createMatchedMovementEvents());
      const { isSelected } = useHistoryMatchedMovementItem({ events });

      expect(get(isSelected)).toBe(false);
    });

    it('should not throw when toggleSelected called', () => {
      const events = ref(createMatchedMovementEvents());
      const { toggleSelected } = useHistoryMatchedMovementItem({ events });

      expect(() => toggleSelected()).not.toThrow();
    });
  });

  describe('selection state with selection prop', () => {
    interface MockSelectionOptions {
      isSelectionMode: boolean;
      isSelectAllMatching: boolean;
      selectedEventIds: number[];
    }

    function createMockSelection(overrides: Partial<MockSelectionOptions> = {}): {
      isSelectionMode: Ref<boolean>;
      isSelectAllMatching: Ref<boolean>;
      isEventSelected: (id: number) => boolean;
      actions: { toggleEvent: ReturnType<typeof vi.fn>; toggleSwap: ReturnType<typeof vi.fn> };
    } {
      const selectedIds = new Set(overrides.selectedEventIds ?? []);
      return {
        isSelectionMode: ref(overrides.isSelectionMode ?? false),
        isSelectAllMatching: ref(overrides.isSelectAllMatching ?? false),
        isEventSelected: (id: number): boolean => selectedIds.has(id),
        actions: {
          toggleEvent: vi.fn(),
          toggleSwap: vi.fn(),
        },
      };
    }

    it('should return true for showCheckbox when selection mode active', () => {
      const events = ref(createMatchedMovementEvents());
      const selection = createMockSelection({ isSelectionMode: true });
      const { showCheckbox } = useHistoryMatchedMovementItem({ events, selection: selection as any });

      expect(get(showCheckbox)).toBe(true);
    });

    it('should return true for isSelected when all events selected', () => {
      const events = ref(createMatchedMovementEvents());
      const selection = createMockSelection({ selectedEventIds: [1, 2] });
      const { isSelected } = useHistoryMatchedMovementItem({ events, selection: selection as any });

      expect(get(isSelected)).toBe(true);
    });

    it('should return false for isSelected when not all events selected', () => {
      const events = ref(createMatchedMovementEvents());
      const selection = createMockSelection({ selectedEventIds: [1] });
      const { isSelected } = useHistoryMatchedMovementItem({ events, selection: selection as any });

      expect(get(isSelected)).toBe(false);
    });

    it('should call toggleSwap with all event IDs when toggled', () => {
      const events = ref(createMatchedMovementEvents());
      const selection = createMockSelection();
      const { toggleSelected } = useHistoryMatchedMovementItem({ events, selection: selection as any });

      toggleSelected();

      expect(selection.actions.toggleSwap).toHaveBeenCalledWith([1, 2]);
    });
  });

  describe('hasMissingRule', () => {
    it('should return true when primary event has missing rule', () => {
      const events = ref([
        createMockEvent(HistoryEventEntryType.ASSET_MOVEMENT_EVENT, {
          identifier: 1,
          eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.NOT_PROCESSED,
        }),
      ]);
      const { hasMissingRule } = useHistoryMatchedMovementItem({ events });

      expect(get(hasMissingRule)).toBe(true);
    });

    it('should return false when primary event has no missing rule', () => {
      const events = ref(createMatchedMovementEvents());
      const { hasMissingRule } = useHistoryMatchedMovementItem({ events });

      expect(get(hasMissingRule)).toBe(false);
    });
  });

  describe('reactivity', () => {
    it('should update primaryEvent when events change', () => {
      const events = ref(createMatchedMovementEvents());
      const { primaryEvent } = useHistoryMatchedMovementItem({ events });

      expect(get(primaryEvent).identifier).toBe(1);

      const newEvents = createMatchedMovementEvents();
      newEvents[0].identifier = 999;
      set(events, newEvents);

      expect(get(primaryEvent).identifier).toBe(999);
    });

    it('should update chain when events change', () => {
      const events = ref(createMatchedMovementEvents());
      const { chain } = useHistoryMatchedMovementItem({ events });

      expect(get(chain)).toBe('ethereum');

      const newEvents = createMatchedMovementEvents();
      newEvents[1].location = 'optimism';
      set(events, newEvents);

      expect(get(chain)).toBe('optimism');
    });
  });
});
