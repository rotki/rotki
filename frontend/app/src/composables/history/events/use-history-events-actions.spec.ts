import type { Blockchain } from '@rotki/common';
import type { Ref } from 'vue';
import type { HistoryEventAction } from '@/composables/history/events/types';
import type { Collection } from '@/types/collection';
import type { HistoryEventRow } from '@/types/history/events/schemas';
import { afterEach, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { useHistoryEventsActions } from './use-history-events-actions';

const mockRefreshTransactions = vi.fn();

vi.mock('@/composables/history/events/tx', () => ({
  useHistoryTransactions: vi.fn(() => ({
    refreshTransactions: mockRefreshTransactions,
  })),
}));

vi.mock('@/composables/history/events/tx/decoding', () => ({
  useHistoryTransactionDecoding: vi.fn(() => ({
    fetchUndecodedTransactionsStatus: vi.fn(),
    pullAndRecodeEthBlockEvents: vi.fn(),
    pullAndRedecodeTransactions: vi.fn(),
    redecodeTransactions: vi.fn(),
  })),
}));

vi.mock('@/composables/history/events/mapping', () => ({
  useHistoryEventMappings: vi.fn(() => ({
    refresh: vi.fn(),
  })),
}));

vi.mock('@/store/confirm', () => ({
  useConfirmStore: vi.fn(() => ({
    show: vi.fn(),
  })),
}));

vi.mock('@/store/history', () => ({
  useHistoryStore: vi.fn(() => ({
    fetchAssociatedLocations: vi.fn(),
    fetchLocationLabels: vi.fn(),
    resetUndecodedTransactionsStatus: vi.fn(),
  })),
}));

vi.mock('@/modules/history/events/use-history-events-auto-fetch', () => ({
  useHistoryEventsAutoFetch: vi.fn(),
}));

describe('useHistoryEventsActions', () => {
  function createOptions(): {
    currentAction: Ref<HistoryEventAction>;
    entryTypes: Ref<undefined>;
    fetchData: Mock<() => Promise<void>>;
    groups: Ref<Collection<HistoryEventRow>>;
    onlyChains: Ref<Blockchain[]>;
  } {
    return {
      currentAction: ref('query'),
      entryTypes: ref(undefined),
      fetchData: vi.fn().mockResolvedValue(undefined),
      groups: ref<Collection<HistoryEventRow>>({ data: [], found: 0, limit: 10, total: 0 }),
      onlyChains: ref<Blockchain[]>([]),
    };
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    mockRefreshTransactions.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('dialogHandlers.onRepullTransactions', () => {
    it('should call refreshTransactions with specific account when both chain and address provided', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      await dialogHandlers.onRepullTransactions?.({
        address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
        chain: 'eth',
      });

      expect(mockRefreshTransactions).toHaveBeenCalledWith({
        chains: [],
        disableEvmEvents: false,
        payload: {
          accounts: [{ address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', chain: 'eth' }],
        },
        userInitiated: true,
      });
    });

    it('should call refreshTransactions with specific chain when only chain provided', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      await dialogHandlers.onRepullTransactions?.({
        chain: 'optimism',
      });

      expect(mockRefreshTransactions).toHaveBeenCalledWith({
        chains: ['optimism'],
        disableEvmEvents: false,
        payload: undefined,
        userInitiated: true,
      });
    });

    it('should call refreshTransactions with empty chains when chain is undefined', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      await dialogHandlers.onRepullTransactions?.({
        chain: undefined,
      });

      expect(mockRefreshTransactions).toHaveBeenCalledWith({
        chains: [],
        disableEvmEvents: false,
        payload: undefined,
        userInitiated: true,
      });
    });

    it('should call refreshTransactions with empty chains when payload is undefined', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      await dialogHandlers.onRepullTransactions?.();

      expect(mockRefreshTransactions).toHaveBeenCalledWith({
        chains: [],
        disableEvmEvents: false,
        payload: undefined,
        userInitiated: true,
      });
    });

    it('should call refreshTransactions with empty chains when both chain and address are undefined', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      await dialogHandlers.onRepullTransactions?.({
        address: undefined,
        chain: undefined,
      });

      expect(mockRefreshTransactions).toHaveBeenCalledWith({
        chains: [],
        disableEvmEvents: false,
        payload: undefined,
        userInitiated: true,
      });
    });

    it('should call refreshTransactions with chain only when address is empty string', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      await dialogHandlers.onRepullTransactions?.({
        address: '',
        chain: 'eth',
      });

      // Empty string is falsy, so it takes the else branch
      expect(mockRefreshTransactions).toHaveBeenCalledWith({
        chains: ['eth'],
        disableEvmEvents: false,
        payload: undefined,
        userInitiated: true,
      });
    });

    it('should call refreshTransactions for all chains when address provided but chain is undefined', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      await dialogHandlers.onRepullTransactions?.({
        address: '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c',
        chain: undefined,
      });

      // chain is undefined, so it takes the else branch
      expect(mockRefreshTransactions).toHaveBeenCalledWith({
        chains: [],
        disableEvmEvents: false,
        payload: undefined,
        userInitiated: true,
      });
    });
  });

  describe('dialogHandlers.onRepullExchangeEvents', () => {
    it('should call refreshTransactions with exchanges payload', async () => {
      const options = createOptions();
      const { dialogHandlers } = useHistoryEventsActions(options);

      const exchanges = [{ location: 'kraken', name: 'My Kraken' }];
      await dialogHandlers.onRepullExchangeEvents?.(exchanges as any);

      expect(mockRefreshTransactions).toHaveBeenCalledWith({
        disableEvmEvents: true,
        payload: {
          exchanges,
        },
        userInitiated: true,
      });
    });
  });
});
