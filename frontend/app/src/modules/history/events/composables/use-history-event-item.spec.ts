import { bigNumberify, HistoryEventEntryType } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  type EthBlockEvent,
  type EvmHistoryEvent,
  HistoryEventAccountingRuleStatus,
  type HistoryEventEntry,
} from '@/types/history/events/schemas';
import { useHistoryEventItem } from './use-history-event-item';

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChain: vi.fn((location: string) => location),
  })),
}));

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({
    assetInfo: vi.fn(() => ref({ protocol: undefined })),
  })),
}));

vi.mock('@/store/assets/ignored', () => ({
  useIgnoredAssetsStore: vi.fn(() => ({
    useIsAssetIgnored: vi.fn(() => ref(false)),
  })),
}));

vi.mock('@/utils/history/events', () => ({
  isEventMissingAccountingRule: vi.fn((event: HistoryEventEntry) =>
    event.eventAccountingRuleStatus === HistoryEventAccountingRuleStatus.NOT_PROCESSED),
}));

// Pick specific properties from the event types that have them
type EventSpecificOverrides =
  & Partial<Pick<EvmHistoryEvent, 'counterparty' | 'extraData'>>
  & Partial<Pick<EthBlockEvent, 'validatorIndex' | 'blockNumber'>>;

type Overrides = Omit<Partial<HistoryEventEntry>, 'entryType'> & EventSpecificOverrides;

// Create EvmHistoryEvent which has counterparty, address, etc.
function createMockEvent(overrides: Overrides = {}): HistoryEventEntry {
  return {
    identifier: 1,
    entryType: HistoryEventEntryType.EVM_EVENT,
    asset: 'ETH',
    amount: bigNumberify('1.5'),
    timestamp: 1700000000000,
    location: 'ethereum',
    eventType: 'receive',
    eventSubtype: 'none',
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
}

describe('useHistoryEventItem', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('basic event data', () => {
    it('should return chain from event location', () => {
      const event = ref(createMockEvent({ location: 'optimism' }));
      const { chain } = useHistoryEventItem({ event });

      expect(get(chain)).toBe('optimism');
    });

    it('should return notes from userNotes if available', () => {
      const event = ref(createMockEvent({
        userNotes: 'User note',
        autoNotes: 'Auto note',
      }));
      const { notes } = useHistoryEventItem({ event });

      expect(get(notes)).toBe('User note');
    });

    it('should return notes from autoNotes if userNotes not available', () => {
      const event = ref(createMockEvent({
        autoNotes: 'Auto note',
      }));
      const { notes } = useHistoryEventItem({ event });

      expect(get(notes)).toBe('Auto note');
    });

    it('should return undefined notes if neither available', () => {
      const event = ref(createMockEvent());
      const { notes } = useHistoryEventItem({ event });

      expect(get(notes)).toBeUndefined();
    });

    it('should return counterparty from event', () => {
      const event = ref(createMockEvent({
        counterparty: 'uniswap-v3',
      }));
      const { counterparty } = useHistoryEventItem({ event });

      expect(get(counterparty)).toBe('uniswap-v3');
    });

    it('should return undefined counterparty if not present', () => {
      const event = ref(createMockEvent());
      const { counterparty } = useHistoryEventItem({ event });

      expect(get(counterparty)).toBeUndefined();
    });

    it('should return validatorIndex from event', () => {
      const event = ref(createMockEvent({
        validatorIndex: 12345,
      }));
      const { validatorIndex } = useHistoryEventItem({ event });

      expect(get(validatorIndex)).toBe(12345);
    });

    it('should return blockNumber from event', () => {
      const event = ref(createMockEvent({
        blockNumber: 18000000,
      }));
      const { blockNumber } = useHistoryEventItem({ event });

      expect(get(blockNumber)).toBe(18000000);
    });

    it('should return extraData from event', () => {
      const extraData = { key: 'value' };
      const event = ref(createMockEvent({
        extraData,
      }));
      const { extraData: result } = useHistoryEventItem({ event });

      expect(get(result)).toEqual(extraData);
    });
  });

  describe('selection state without selection prop', () => {
    it('should return false for showCheckbox when no selection provided', () => {
      const event = ref(createMockEvent());
      const { showCheckbox } = useHistoryEventItem({ event });

      expect(get(showCheckbox)).toBe(false);
    });

    it('should return false for isCheckboxDisabled when no selection provided', () => {
      const event = ref(createMockEvent());
      const { isCheckboxDisabled } = useHistoryEventItem({ event });

      expect(get(isCheckboxDisabled)).toBe(false);
    });

    it('should return false for isSelected when no selection provided', () => {
      const event = ref(createMockEvent());
      const { isSelected } = useHistoryEventItem({ event });

      expect(get(isSelected)).toBe(false);
    });

    it('should not throw when toggleSelected called without selection', () => {
      const event = ref(createMockEvent());
      const { toggleSelected } = useHistoryEventItem({ event });

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

    it('should return true for showCheckbox when selection mode is active', () => {
      const event = ref(createMockEvent());
      const selection = createMockSelection({ isSelectionMode: true });
      const { showCheckbox } = useHistoryEventItem({ event, selection: selection as any });

      expect(get(showCheckbox)).toBe(true);
    });

    it('should return true for isCheckboxDisabled when selectAllMatching is active', () => {
      const event = ref(createMockEvent());
      const selection = createMockSelection({ isSelectAllMatching: true });
      const { isCheckboxDisabled } = useHistoryEventItem({ event, selection: selection as any });

      expect(get(isCheckboxDisabled)).toBe(true);
    });

    it('should return true for isSelected when event is in selection', () => {
      const event = ref(createMockEvent({ identifier: 123 }));
      const selection = createMockSelection({ selectedEventIds: [123] });
      const { isSelected } = useHistoryEventItem({ event, selection: selection as any });

      expect(get(isSelected)).toBe(true);
    });

    it('should return false for isSelected when event is not in selection', () => {
      const event = ref(createMockEvent({ identifier: 123 }));
      const selection = createMockSelection({ selectedEventIds: [456] });
      const { isSelected } = useHistoryEventItem({ event, selection: selection as any });

      expect(get(isSelected)).toBe(false);
    });

    it('should call toggleEvent when toggleSelected is called', () => {
      const event = ref(createMockEvent({ identifier: 123 }));
      const selection = createMockSelection();
      const { toggleSelected } = useHistoryEventItem({ event, selection: selection as any });

      toggleSelected();

      expect(selection.actions.toggleEvent).toHaveBeenCalledWith(123);
    });
  });

  describe('missing rule detection', () => {
    it('should return hasMissingRule based on event', () => {
      const event = ref(createMockEvent({ eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.NOT_PROCESSED }));
      const { hasMissingRule } = useHistoryEventItem({ event });

      expect(get(hasMissingRule)).toBe(true);
    });

    it('should return false for hasMissingRule when not missing', () => {
      const event = ref(createMockEvent({ eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.HAS_RULE }));
      const { hasMissingRule } = useHistoryEventItem({ event });

      expect(get(hasMissingRule)).toBe(false);
    });
  });

  describe('hidden event state', () => {
    it('should compute hiddenEvent as combination of isIgnoredAsset and isSpam', () => {
      const event = ref(createMockEvent());
      const { hiddenEvent, isIgnoredAsset, isSpam } = useHistoryEventItem({ event });

      // With mocks returning false for both, hiddenEvent should be false
      expect(get(hiddenEvent)).toBe(false);
      expect(get(isIgnoredAsset)).toBe(false);
      expect(get(isSpam)).toBe(false);
    });
  });

  describe('reactivity', () => {
    it('should update chain when event location changes', () => {
      const event = ref(createMockEvent({ location: 'ethereum' }));
      const { chain } = useHistoryEventItem({ event });

      expect(get(chain)).toBe('ethereum');

      set(event, createMockEvent({ location: 'polygon_pos' }));

      expect(get(chain)).toBe('polygon_pos');
    });

    it('should update notes when event notes change', () => {
      const event = ref(createMockEvent({ userNotes: 'Initial note' }));
      const { notes } = useHistoryEventItem({ event });

      expect(get(notes)).toBe('Initial note');

      set(event, createMockEvent({ userNotes: 'Updated note' }));

      expect(get(notes)).toBe('Updated note');
    });
  });
});
