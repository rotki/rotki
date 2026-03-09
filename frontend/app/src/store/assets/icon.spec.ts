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
    it('should delegate to useAssetIconCheck', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      mockCheckAsset.mockResolvedValueOnce(200);
      const result = await store.checkIfAssetExists('ETH', {});

      expect(result).toBe(true);
      expect(mockCheckAsset).toHaveBeenCalledTimes(1);

      const result2 = await store.checkIfAssetExists('ETH', {});
      expect(result2).toBe(true);
      expect(mockCheckAsset).toHaveBeenCalledTimes(1);
    });
  });

  describe('setLastRefreshedAssetIcon', () => {
    it('should clear cache when called', async () => {
      const { useAssetIconStore } = await import('./icon');
      const store = useAssetIconStore();

      mockCheckAsset.mockResolvedValueOnce(200);
      await store.checkIfAssetExists('ETH', {});
      expect(mockCheckAsset).toHaveBeenCalledTimes(1);

      store.setLastRefreshedAssetIcon();
      await nextTick();

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
