import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useDataLoader } from '@/composables/session/load';

const mockOnBalancesLoaded = vi.fn();
const mockFetch = vi.fn();
const mockFetchIgnoredAssets = vi.fn();
const mockFetchWhitelistedAssets = vi.fn();
const mockFetchNetValue = vi.fn();
const mockRefreshPrices = vi.fn();
const mockFetchTags = vi.fn();
const mockFetchAllTradeLocations = vi.fn();
const mockSetStatus = vi.fn();
const mockShouldFetchData = ref<boolean>(true);

vi.mock('@/composables/session/use-scheduler-state', () => ({
  useSchedulerState: vi.fn(() => ({
    onBalancesLoaded: mockOnBalancesLoaded,
  })),
}));

vi.mock('@/composables/balances', () => ({
  useBalances: vi.fn(() => ({
    fetch: mockFetch,
  })),
}));

vi.mock('@/store/assets/ignored', () => ({
  useIgnoredAssetsStore: vi.fn(() => ({
    fetchIgnoredAssets: mockFetchIgnoredAssets,
  })),
}));

vi.mock('@/store/assets/whitelisted', () => ({
  useWhitelistedAssetsStore: vi.fn(() => ({
    fetchWhitelistedAssets: mockFetchWhitelistedAssets,
  })),
}));

vi.mock('@/store/statistics', () => ({
  useStatisticsStore: vi.fn(() => ({
    fetchNetValue: mockFetchNetValue,
  })),
}));

vi.mock('@/modules/prices/use-price-refresh', () => ({
  usePriceRefresh: vi.fn(() => ({
    refreshPrices: mockRefreshPrices,
  })),
}));

vi.mock('@/store/session/tags', () => ({
  useTagStore: vi.fn(() => ({
    fetchTags: mockFetchTags,
  })),
}));

vi.mock('@/store/locations', () => ({
  useLocationStore: vi.fn(() => ({
    fetchAllTradeLocations: mockFetchAllTradeLocations,
  })),
}));

vi.mock('@/store/session/auth', () => ({
  useSessionAuthStore: vi.fn(() => ({
    shouldFetchData: mockShouldFetchData,
  })),
}));

vi.mock('@/composables/status', () => ({
  useStatusUpdater: vi.fn(() => ({
    setStatus: mockSetStatus,
  })),
}));

vi.mock('@/utils/logging', () => ({
  logger: {
    info: vi.fn(),
  },
}));

describe('composables::session::load', () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);

    set(mockShouldFetchData, true);

    mockFetch.mockResolvedValue(undefined);
    mockFetchIgnoredAssets.mockResolvedValue(undefined);
    mockFetchWhitelistedAssets.mockResolvedValue(undefined);
    mockFetchNetValue.mockResolvedValue(undefined);
    mockRefreshPrices.mockResolvedValue(undefined);
    mockFetchTags.mockResolvedValue(undefined);
    mockFetchAllTradeLocations.mockResolvedValue(undefined);
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
      expect(mockFetch).toHaveBeenCalled();
      expect(mockFetchIgnoredAssets).toHaveBeenCalled();
      expect(mockFetchWhitelistedAssets).toHaveBeenCalled();
      expect(mockFetchNetValue).toHaveBeenCalled();
      expect(mockRefreshPrices).toHaveBeenCalled();
      expect(mockOnBalancesLoaded).toHaveBeenCalled();
    });

    it('should not call onBalancesLoaded when shouldFetchData is false', async () => {
      set(mockShouldFetchData, false);

      const { load } = useDataLoader();

      load();
      await flushPromises();

      expect(mockOnBalancesLoaded).not.toHaveBeenCalled();
    });

    it('should call onBalancesLoaded even if some fetches fail', async () => {
      mockFetch.mockRejectedValue(new Error('Fetch failed'));

      const { load } = useDataLoader();

      load();
      await flushPromises();

      // onBalancesLoaded should still be called because Promise.allSettled is used
      expect(mockOnBalancesLoaded).toHaveBeenCalledTimes(1);
    });
  });
});
