import type { Ref } from 'vue';
import type { Collection } from '@/types/collection';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type InternalTxConflict, InternalTxConflictStatuses } from './types';
import { useInternalTxConflicts } from './use-internal-tx-conflicts';

const { spies } = vi.hoisted(() => ({
  spies: {
    fetchInternalTxConflicts: vi.fn<() => Promise<Collection<InternalTxConflict>>>(),
  },
}));

vi.mock('./internal-tx-conflicts-api', () => ({
  useInternalTxConflictsApi: (): object => ({
    fetchInternalTxConflicts: spies.fetchInternalTxConflicts,
  }),
}));

vi.mock('@/store/message', () => ({
  useMessageStore: (): object => ({
    setMessage: vi.fn(),
  }),
}));

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: (): object => ({
    evmChainsData: ref([]),
    getEvmChainName: (chain: string): string => chain,
  }),
}));

vi.mock('@/store/notifications', () => ({
  useNotificationsStore: (): object => ({
    notify: vi.fn(),
  }),
}));

vi.mock('@/store/settings/frontend', () => ({
  useFrontendSettingsStore: (): object => ({
    dateInputFormat: ref('%d/%m/%Y %H:%M'),
  }),
}));

vi.mock('@/utils/date', () => ({
  dateDeserializer: (): ((v: string) => string) => (v: string): string => v,
  dateRangeValidator: (): ((v: string) => boolean) => (): boolean => true,
  dateSerializer: (): ((v: string) => string) => (v: string): string => v,
  getDateInputISOFormat: (): string => 'DD/MM/YYYY HH:mm',
}));

vi.mock('@/composables/session/use-items-per-page', () => ({
  useItemsPerPage: (): Ref<number> => ref(10),
}));

function createMockCollection(
  data: InternalTxConflict[] = [],
  found: number = 0,
  total: number = 0,
): Collection<InternalTxConflict> {
  return {
    data,
    found,
    limit: 20,
    total,
  };
}

function createMockConflict(overrides: Partial<InternalTxConflict> = {}): InternalTxConflict {
  return {
    action: 'repull',
    chain: 'ethereum',
    groupIdentifier: null,
    lastError: null,
    lastRetryTs: null,
    redecodeReason: null,
    repullReason: 'all_zero_gas',
    timestamp: null,
    txHash: '0xabc',
    ...overrides,
  };
}

describe('use-internal-tx-conflicts', () => {
  let composable: ReturnType<typeof useInternalTxConflicts>;

  beforeEach(() => {
    vi.clearAllMocks();
    spies.fetchInternalTxConflicts.mockResolvedValue(createMockCollection());
    composable = useInternalTxConflicts();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('fetchPendingCount', () => {
    it('updates pendingCount from API total', async () => {
      spies.fetchInternalTxConflicts.mockResolvedValue(createMockCollection([], 4, 5));

      await composable.fetchPendingCount();

      expect(get(composable.pendingCount)).toBe(4);
      expect(spies.fetchInternalTxConflicts).toHaveBeenCalledWith({
        failed: false,
        fixed: false,
        limit: 0,
        offset: 0,
      });
    });
  });

  describe('fetchConflicts', () => {
    it('loads data for the active filter', async () => {
      const mockConflict = createMockConflict();
      spies.fetchInternalTxConflicts.mockResolvedValue(createMockCollection([mockConflict], 1, 1));

      await composable.fetchConflicts();

      expect(get(composable.conflicts)).toHaveLength(1);
      expect(get(composable.conflicts)[0].txHash).toBe('0xabc');
      expect(get(composable.totalFound)).toBe(1);
    });
  });

  describe('setFilter', () => {
    it('changes active filter and triggers refetch', async () => {
      spies.fetchInternalTxConflicts.mockResolvedValue(createMockCollection());

      composable.setFilter(InternalTxConflictStatuses.FAILED);

      await vi.waitFor(() => {
        expect(spies.fetchInternalTxConflicts).toHaveBeenCalled();
      });

      expect(get(composable.activeFilter)).toBe(InternalTxConflictStatuses.FAILED);
    });
  });
});
