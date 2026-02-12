import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type EvmHistoryEvent, HistoryEventAccountingRuleStatus, type HistoryEventEntry } from '@/types/history/events/schemas';
import { useHistorySwapItem } from './use-history-swap-item';

const mockIsAssetIgnored = vi.fn<(asset: string) => boolean>().mockReturnValue(false);
const mockAssetInfoMap = new Map<string, { protocol?: string }>();

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChain: vi.fn((location: string) => location),
  })),
}));

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({
    assetInfo: (assetRef: Ref<string>): ComputedRef<{ protocol?: string }> => computed(() => mockAssetInfoMap.get(get(assetRef)) ?? {}),
    getAssetSymbol: vi.fn((asset: string) => asset.toUpperCase()),
  })),
}));

vi.mock('@/store/assets/ignored', () => ({
  useIgnoredAssetsStore: vi.fn(() => ({
    isAssetIgnored: mockIsAssetIgnored,
  })),
}));

vi.mock('@/utils/history/events', () => ({
  isEventMissingAccountingRule: vi.fn((event: HistoryEventEntry) =>
    event.eventAccountingRuleStatus === HistoryEventAccountingRuleStatus.NOT_PROCESSED),
}));

// Create EvmHistoryEvent which has counterparty property
function createMockEvent(overrides: Partial<EvmHistoryEvent & { eventAccountingRuleStatus: HistoryEventAccountingRuleStatus }> = {}): HistoryEventEntry {
  const event: EvmHistoryEvent & { eventAccountingRuleStatus: HistoryEventAccountingRuleStatus } = {
    identifier: 1,
    entryType: HistoryEventEntryType.EVM_EVENT,
    asset: 'ETH',
    amount: bigNumberify('1.5'),
    timestamp: 1700000000000,
    location: 'ethereum',
    eventType: 'trade',
    eventSubtype: 'spend',
    groupIdentifier: 'tx-123',
    address: null,
    counterparty: null,
    extraData: null,
    txRef: 'tx-ref-123',
    locationLabel: null,
    sequenceIndex: 0,
    eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.HAS_RULE,
    ...overrides,
  };
  return event as HistoryEventEntry;
}

function createSwapEvents(): HistoryEventEntry[] {
  return [
    createMockEvent({
      identifier: 1,
      asset: 'ETH',
      amount: bigNumberify('1.0'),
      eventSubtype: 'spend',
    }),
    createMockEvent({
      identifier: 2,
      asset: 'USDC',
      amount: bigNumberify('2000'),
      eventSubtype: 'receive',
    }),
  ];
}

describe('useHistorySwapItem', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockIsAssetIgnored.mockReturnValue(false);
    mockAssetInfoMap.clear();
  });

  describe('primaryEvent', () => {
    it('should return first event as primary', () => {
      const events = ref(createSwapEvents());
      const { primaryEvent } = useHistorySwapItem({ events });

      expect(get(primaryEvent).identifier).toBe(1);
    });

    it('should update when events change', () => {
      const events = ref(createSwapEvents());
      const { primaryEvent } = useHistorySwapItem({ events });

      expect(get(primaryEvent).identifier).toBe(1);

      const newEvents = createSwapEvents();
      newEvents[0].identifier = 999;
      set(events, newEvents);

      expect(get(primaryEvent).identifier).toBe(999);
    });
  });

  describe('chain', () => {
    it('should return chain from primary event location', () => {
      const events = ref(createSwapEvents());
      events.value[0].location = 'optimism';
      const { chain } = useHistorySwapItem({ events });

      expect(get(chain)).toBe('optimism');
    });
  });

  describe('spend and receive events', () => {
    it('should separate spend events', () => {
      const events = ref(createSwapEvents());
      const { spendEvents, spendEvent } = useHistorySwapItem({ events });

      expect(get(spendEvents)).toHaveLength(1);
      expect(get(spendEvent)?.asset).toBe('ETH');
    });

    it('should separate receive events', () => {
      const events = ref(createSwapEvents());
      const { receiveEvents, receiveEvent } = useHistorySwapItem({ events });

      expect(get(receiveEvents)).toHaveLength(1);
      expect(get(receiveEvent)?.asset).toBe('USDC');
    });

    it('should handle multiple spend events', () => {
      const events = ref([
        createMockEvent({ identifier: 1, asset: 'ETH', eventSubtype: 'spend' }),
        createMockEvent({ identifier: 2, asset: 'WETH', eventSubtype: 'spend' }),
        createMockEvent({ identifier: 3, asset: 'USDC', eventSubtype: 'receive' }),
      ]);
      const { spendEvents, isMultiSpend, isMultiReceive } = useHistorySwapItem({ events });

      expect(get(spendEvents)).toHaveLength(2);
      expect(get(isMultiSpend)).toBe(true);
      expect(get(isMultiReceive)).toBe(false);
    });

    it('should handle multiple receive events', () => {
      const events = ref([
        createMockEvent({ identifier: 1, asset: 'ETH', eventSubtype: 'spend' }),
        createMockEvent({ identifier: 2, asset: 'USDC', eventSubtype: 'receive' }),
        createMockEvent({ identifier: 3, asset: 'DAI', eventSubtype: 'receive' }),
      ]);
      const { receiveEvents, isMultiSpend, isMultiReceive } = useHistorySwapItem({ events });

      expect(get(receiveEvents)).toHaveLength(2);
      expect(get(isMultiSpend)).toBe(false);
      expect(get(isMultiReceive)).toBe(true);
    });

    it('should return undefined for spendEvent when no spend events', () => {
      const events = ref([
        createMockEvent({ identifier: 1, asset: 'USDC', eventSubtype: 'receive' }),
      ]);
      const { spendEvent } = useHistorySwapItem({ events });

      expect(get(spendEvent)).toBeUndefined();
    });

    it('should return undefined for receiveEvent when no receive events', () => {
      const events = ref([
        createMockEvent({ identifier: 1, asset: 'ETH', eventSubtype: 'spend' }),
      ]);
      const { receiveEvent } = useHistorySwapItem({ events });

      expect(get(receiveEvent)).toBeUndefined();
    });
  });

  describe('swapEventIds', () => {
    it('should return all event identifiers', () => {
      const events = ref(createSwapEvents());
      const { swapEventIds } = useHistorySwapItem({ events });

      expect(get(swapEventIds)).toEqual([1, 2]);
    });

    it('should update when events change', () => {
      const events = ref(createSwapEvents());
      const { swapEventIds } = useHistorySwapItem({ events });

      expect(get(swapEventIds)).toEqual([1, 2]);

      set(events, [
        ...createSwapEvents(),
        createMockEvent({ identifier: 3, eventSubtype: 'fee' }),
      ]);

      expect(get(swapEventIds)).toEqual([1, 2, 3]);
    });
  });

  describe('counterparty', () => {
    it('should return counterparty from primary event', () => {
      const events = ref([
        createMockEvent({ eventSubtype: 'spend', counterparty: 'uniswap-v3' }),
        createMockEvent({ identifier: 2, asset: 'USDC', eventSubtype: 'receive' }),
      ]);
      const { counterparty } = useHistorySwapItem({ events });

      expect(get(counterparty)).toBe('uniswap-v3');
    });

    it('should return undefined when no counterparty', () => {
      const events = ref(createSwapEvents());
      const { counterparty } = useHistorySwapItem({ events });

      expect(get(counterparty)).toBeUndefined();
    });
  });

  describe('selection state without selection prop', () => {
    it('should return false for showCheckbox', () => {
      const events = ref(createSwapEvents());
      const { showCheckbox } = useHistorySwapItem({ events });

      expect(get(showCheckbox)).toBe(false);
    });

    it('should return false for isCheckboxDisabled', () => {
      const events = ref(createSwapEvents());
      const { isCheckboxDisabled } = useHistorySwapItem({ events });

      expect(get(isCheckboxDisabled)).toBe(false);
    });

    it('should return false for isSelected', () => {
      const events = ref(createSwapEvents());
      const { isSelected } = useHistorySwapItem({ events });

      expect(get(isSelected)).toBe(false);
    });

    it('should not throw when toggleSelected called', () => {
      const events = ref(createSwapEvents());
      const { toggleSelected } = useHistorySwapItem({ events });

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
      const events = ref(createSwapEvents());
      const selection = createMockSelection({ isSelectionMode: true });
      const { showCheckbox } = useHistorySwapItem({ events, selection: selection as any });

      expect(get(showCheckbox)).toBe(true);
    });

    it('should return true for isSelected when all events are selected', () => {
      const events = ref(createSwapEvents());
      const selection = createMockSelection({ selectedEventIds: [1, 2] });
      const { isSelected } = useHistorySwapItem({ events, selection: selection as any });

      expect(get(isSelected)).toBe(true);
    });

    it('should return false for isSelected when not all events selected', () => {
      const events = ref(createSwapEvents());
      const selection = createMockSelection({ selectedEventIds: [1] });
      const { isSelected } = useHistorySwapItem({ events, selection: selection as any });

      expect(get(isSelected)).toBe(false);
    });

    it('should call toggleSwap with all event IDs when toggled', () => {
      const events = ref(createSwapEvents());
      const selection = createMockSelection();
      const { toggleSelected } = useHistorySwapItem({ events, selection: selection as any });

      toggleSelected();

      expect(selection.actions.toggleSwap).toHaveBeenCalledWith([1, 2]);
    });
  });

  describe('hasMissingRule', () => {
    it('should return true when primary event has missing rule', () => {
      const events = ref([
        createMockEvent({ eventSubtype: 'spend', eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.NOT_PROCESSED }),
        createMockEvent({ identifier: 2, asset: 'USDC', eventSubtype: 'receive' }),
      ]);
      const { hasMissingRule } = useHistorySwapItem({ events });

      expect(get(hasMissingRule)).toBe(true);
    });

    it('should return false when primary event has no missing rule', () => {
      const events = ref(createSwapEvents());
      const { hasMissingRule } = useHistorySwapItem({ events });

      expect(get(hasMissingRule)).toBe(false);
    });
  });

  describe('compactNotes', () => {
    it('should return undefined when no spend events', () => {
      const events = ref([
        createMockEvent({ identifier: 1, eventSubtype: 'receive' }),
      ]);
      const { compactNotes } = useHistorySwapItem({ events });

      expect(get(compactNotes)).toBeUndefined();
    });

    it('should return undefined when no receive events', () => {
      const events = ref([
        createMockEvent({ identifier: 1, eventSubtype: 'spend' }),
      ]);
      const { compactNotes } = useHistorySwapItem({ events });

      expect(get(compactNotes)).toBeUndefined();
    });
  });

  describe('isSpendHidden and isReceiveHidden', () => {
    it('should return false when neither asset is ignored or spam', () => {
      const events = ref(createSwapEvents());
      const { isSpendHidden, isReceiveHidden } = useHistorySwapItem({ events });

      expect(get(isSpendHidden)).toBe(false);
      expect(get(isReceiveHidden)).toBe(false);
    });

    it('should return true for isSpendHidden when spend asset is ignored', () => {
      mockIsAssetIgnored.mockImplementation((asset: string) => asset === 'ETH');

      const events = ref(createSwapEvents());
      const { isSpendHidden, isReceiveHidden } = useHistorySwapItem({ events });

      expect(get(isSpendHidden)).toBe(true);
      expect(get(isReceiveHidden)).toBe(false);
    });

    it('should return true for isReceiveHidden when receive asset is ignored', () => {
      mockIsAssetIgnored.mockImplementation((asset: string) => asset === 'USDC');

      const events = ref(createSwapEvents());
      const { isSpendHidden, isReceiveHidden } = useHistorySwapItem({ events });

      expect(get(isSpendHidden)).toBe(false);
      expect(get(isReceiveHidden)).toBe(true);
    });

    it('should return true for isSpendHidden when spend asset is spam', () => {
      mockAssetInfoMap.set('ETH', { protocol: 'spam' });

      const events = ref(createSwapEvents());
      const { isSpendHidden, isReceiveHidden } = useHistorySwapItem({ events });

      expect(get(isSpendHidden)).toBe(true);
      expect(get(isReceiveHidden)).toBe(false);
    });

    it('should return true for isReceiveHidden when receive asset is spam', () => {
      mockAssetInfoMap.set('USDC', { protocol: 'spam' });

      const events = ref(createSwapEvents());
      const { isSpendHidden, isReceiveHidden } = useHistorySwapItem({ events });

      expect(get(isSpendHidden)).toBe(false);
      expect(get(isReceiveHidden)).toBe(true);
    });

    it('should return true for both when both assets are ignored', () => {
      mockIsAssetIgnored.mockReturnValue(true);

      const events = ref(createSwapEvents());
      const { isSpendHidden, isReceiveHidden } = useHistorySwapItem({ events });

      expect(get(isSpendHidden)).toBe(true);
      expect(get(isReceiveHidden)).toBe(true);
    });

    it('should return false when there is no spend or receive event', () => {
      const events = ref([
        createMockEvent({ identifier: 1, eventSubtype: 'fee' }),
      ]);
      const { isSpendHidden, isReceiveHidden } = useHistorySwapItem({ events });

      expect(get(isSpendHidden)).toBe(false);
      expect(get(isReceiveHidden)).toBe(false);
    });
  });
});
