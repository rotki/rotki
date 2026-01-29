import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockCheckAsset = vi.fn();
const mockAssetImageUrl = vi.fn();

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: vi.fn(() => ({
    assetImageUrl: mockAssetImageUrl,
    checkAsset: mockCheckAsset,
  })),
}));

vi.mock('@/types/blockchain/chains', () => ({
  isBlockchain: vi.fn(() => false),
}));

vi.mock('@shared/utils', () => ({
  wait: vi.fn(async () => Promise.resolve()),
}));

vi.mock('@/utils/logging', () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

describe('store/assets/icon', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
    mockCheckAsset.mockReset();
    mockAssetImageUrl.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  describe('checkIfAssetExists', () => {
    it('should return cached result when within TTL', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      // First call - should hit the API
      mockCheckAsset.mockResolvedValueOnce(200);
      const result1 = await store.checkIfAssetExists('ETH', {});

      expect(result1).toBe(true);
      expect(mockCheckAsset).toHaveBeenCalledTimes(1);

      // Second call within TTL - should return cached result
      const result2 = await store.checkIfAssetExists('ETH', {});

      expect(result2).toBe(true);
      expect(mockCheckAsset).toHaveBeenCalledTimes(1); // No additional call
    });

    it('should fetch again when cache TTL expires', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      // First call
      mockCheckAsset.mockResolvedValueOnce(200);
      await store.checkIfAssetExists('ETH', {});

      expect(mockCheckAsset).toHaveBeenCalledTimes(1);

      // Advance time past TTL (5 minutes + 1ms)
      vi.advanceTimersByTime(5 * 60 * 1000 + 1);

      // Second call after TTL - should fetch again
      mockCheckAsset.mockResolvedValueOnce(200);
      await store.checkIfAssetExists('ETH', {});

      expect(mockCheckAsset).toHaveBeenCalledTimes(2);
    });

    it('should deduplicate concurrent requests for the same identifier', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      // Create a delayed response
      let resolveCheck: (value: number) => void;
      const checkPromise = new Promise<number>((resolve) => {
        resolveCheck = resolve;
      });
      mockCheckAsset.mockReturnValueOnce(checkPromise);

      // Start two concurrent requests
      const request1 = store.checkIfAssetExists('ETH', {});
      const request2 = store.checkIfAssetExists('ETH', {});

      // Resolve the check
      resolveCheck!(200);

      const [result1, result2] = await Promise.all([request1, request2]);

      expect(result1).toBe(true);
      expect(result2).toBe(true);
      expect(mockCheckAsset).toHaveBeenCalledTimes(1); // Only one API call
    });

    it('should cache true for 200 response', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      mockCheckAsset.mockResolvedValueOnce(200);
      const result = await store.checkIfAssetExists('ETH', {});

      expect(result).toBe(true);

      // Verify cached by checking no new API call
      const result2 = await store.checkIfAssetExists('ETH', {});
      expect(result2).toBe(true);
      expect(mockCheckAsset).toHaveBeenCalledTimes(1);
    });

    it('should cache false for 404 response', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      mockCheckAsset.mockResolvedValueOnce(404);
      const result = await store.checkIfAssetExists('UNKNOWN', {});

      expect(result).toBe(false);

      // Verify cached by checking no new API call
      const result2 = await store.checkIfAssetExists('UNKNOWN', {});
      expect(result2).toBe(false);
      expect(mockCheckAsset).toHaveBeenCalledTimes(1);
    });

    it('should handle different identifiers separately', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      mockCheckAsset.mockResolvedValueOnce(200);
      mockCheckAsset.mockResolvedValueOnce(404);

      const result1 = await store.checkIfAssetExists('ETH', {});
      const result2 = await store.checkIfAssetExists('BTC', {});

      expect(result1).toBe(true);
      expect(result2).toBe(false);
      expect(mockCheckAsset).toHaveBeenCalledTimes(2);
    });

    it('should remove pending request after completion', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      mockCheckAsset.mockResolvedValueOnce(200);
      await store.checkIfAssetExists('ETH', {});

      // Advance past TTL to force new request
      vi.advanceTimersByTime(5 * 60 * 1000 + 1);

      // Should make a new API call since pending was cleared
      mockCheckAsset.mockResolvedValueOnce(200);
      await store.checkIfAssetExists('ETH', {});

      expect(mockCheckAsset).toHaveBeenCalledTimes(2);
    });

    it('should return false when request is aborted', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      const abortController = new AbortController();

      // Mock a non-200/404 response to trigger retry loop
      mockCheckAsset.mockResolvedValue(500);

      // Start request and abort immediately
      const requestPromise = store.checkIfAssetExists('ETH', { abortController });
      abortController.abort();

      const result = await requestPromise;

      expect(result).toBe(false);
    });

    it('should return false on error', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      mockCheckAsset.mockRejectedValueOnce(new Error('Network error'));

      const result = await store.checkIfAssetExists('ETH', {});

      expect(result).toBe(false);
    });
  });

  describe('setLastRefreshedAssetIcon', () => {
    it('should clear cache when called', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      // Populate cache
      mockCheckAsset.mockResolvedValueOnce(200);
      await store.checkIfAssetExists('ETH', {});
      expect(mockCheckAsset).toHaveBeenCalledTimes(1);

      // Refresh icons (clears cache via watcher)
      store.setLastRefreshedAssetIcon();
      await nextTick();

      // Should fetch again since cache was cleared
      mockCheckAsset.mockResolvedValueOnce(200);
      await store.checkIfAssetExists('ETH', {});
      expect(mockCheckAsset).toHaveBeenCalledTimes(2);
    });
  });

  describe('getAssetImageUrl', () => {
    it('should return asset image URL', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      mockAssetImageUrl.mockReturnValue('https://example.com/eth.png');

      const url = store.getAssetImageUrl('ETH');

      expect(url).toBe('https://example.com/eth.png');
      expect(mockAssetImageUrl).toHaveBeenCalledWith('ETH', expect.any(Number));
    });
  });
});
