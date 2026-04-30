import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useDataLoader } from '@/modules/auth/use-session-load';

const mockOnBalancesLoaded = vi.fn();
const mockFetchCached = vi.fn();
const mockRefreshFromChain = vi.fn();
const mockFetchIgnoredAssets = vi.fn();
const mockFetchWhitelistedAssets = vi.fn();
const mockFetchNetValue = vi.fn();
const mockRefreshPrices = vi.fn();
const mockSeedFromHistoric = vi.fn();
const mockFetchTags = vi.fn();
const mockFetchAllLocations = vi.fn();
const mockSetStatus = vi.fn();
const mockShouldFetchData = ref<boolean>(true);

vi.mock('@/modules/session/use-scheduler-state', () => ({
  useSchedulerState: vi.fn(() => ({
    onBalancesLoaded: mockOnBalancesLoaded,
  })),
}));

vi.mock('@/modules/balances/use-balance-fetching', () => ({
  useBalanceFetching: vi.fn(() => ({
    fetchCached: mockFetchCached,
    refreshFromChain: mockRefreshFromChain,
  })),
}));

vi.mock('@/modules/assets/prices/use-price-seed', () => ({
  usePriceSeed: vi.fn(() => ({
    seedFromHistoric: mockSeedFromHistoric,
  })),
}));

vi.mock('@/modules/assets/use-ignored-asset-operations', () => ({
  useIgnoredAssetOperations: vi.fn(() => ({
    fetchIgnoredAssets: mockFetchIgnoredAssets,
  })),
}));

vi.mock('@/modules/assets/use-whitelisted-asset-operations', () => ({
  useWhitelistedAssetOperations: vi.fn(() => ({
    fetchWhitelistedAssets: mockFetchWhitelistedAssets,
  })),
}));

vi.mock('@/modules/statistics/use-statistics-data-fetching', () => ({
  useStatisticsDataFetching: vi.fn(() => ({
    fetchNetValue: mockFetchNetValue,
  })),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: vi.fn(() => ({
    refreshPrices: mockRefreshPrices,
  })),
}));

vi.mock('@/modules/tags/use-tag-operations', () => ({
  useTagOperations: vi.fn(() => ({
    fetchTags: mockFetchTags,
  })),
}));

vi.mock('@/modules/history/api/use-history-api', () => ({
  useHistoryApi: vi.fn(() => ({
    fetchAllLocations: mockFetchAllLocations,
  })),
}));

vi.mock('@/modules/core/common/use-location-store', () => ({
  useLocationStore: vi.fn(() => ({
    allLocations: ref({}),
  })),
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: vi.fn(() => ({
    shouldFetchData: mockShouldFetchData,
  })),
}));

vi.mock('@/modules/shell/sync-progress/use-status-updater', () => ({
  useStatusUpdater: vi.fn(() => ({
    setStatus: mockSetStatus,
  })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: {
    info: vi.fn(),
  },
}));

describe('composables::session::load', () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);

    set(mockShouldFetchData, true);

    mockFetchCached.mockResolvedValue(undefined);
    mockRefreshFromChain.mockReturnValue(undefined);
    mockFetchIgnoredAssets.mockResolvedValue(undefined);
    mockFetchWhitelistedAssets.mockResolvedValue(undefined);
    mockFetchNetValue.mockResolvedValue(undefined);
    mockRefreshPrices.mockResolvedValue(undefined);
    mockSeedFromHistoric.mockResolvedValue(undefined);
    mockFetchTags.mockResolvedValue(undefined);
    mockFetchAllLocations.mockResolvedValue({ locations: {} });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('load', () => {
    it('should call onBalancesLoaded after refreshData completes', async () => {
      const { load } = useDataLoader();

      load();
      await flushPromises();

      expect(mockOnBalancesLoaded).toHaveBeenCalledTimes(1);
    });

    it('should call onBalancesLoaded after all data fetching completes', async () => {
      const { load } = useDataLoader();

      load();
      await flushPromises();

      // Verify data fetching happened before onBalancesLoaded
      expect(mockFetchCached).toHaveBeenCalled();
      expect(mockFetchIgnoredAssets).toHaveBeenCalled();
      expect(mockFetchWhitelistedAssets).toHaveBeenCalled();
      expect(mockFetchNetValue).toHaveBeenCalled();
      expect(mockSeedFromHistoric).toHaveBeenCalled();
      expect(mockRefreshPrices).toHaveBeenCalled();
      expect(mockRefreshFromChain).toHaveBeenCalled();
      expect(mockOnBalancesLoaded).toHaveBeenCalled();

      // Seed must run before live refresh and chain refetch
      const seedOrder = mockSeedFromHistoric.mock.invocationCallOrder[0];
      const refreshOrder = mockRefreshPrices.mock.invocationCallOrder[0];
      const chainOrder = mockRefreshFromChain.mock.invocationCallOrder[0];
      expect(seedOrder).toBeLessThan(refreshOrder);
      expect(seedOrder).toBeLessThan(chainOrder);
    });

    it('should not call onBalancesLoaded when shouldFetchData is false', async () => {
      set(mockShouldFetchData, false);

      const { load } = useDataLoader();

      load();
      await flushPromises();

      expect(mockOnBalancesLoaded).not.toHaveBeenCalled();
    });

    it('should call onBalancesLoaded even if some fetches fail', async () => {
      mockFetchCached.mockRejectedValue(new Error('Fetch failed'));

      const { load } = useDataLoader();

      load();
      await flushPromises();

      // onBalancesLoaded should still be called because Promise.allSettled is used
      expect(mockOnBalancesLoaded).toHaveBeenCalledTimes(1);
    });
  });
});
