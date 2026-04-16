import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useWhitelistedAssetOperations } from '@/modules/assets/use-whitelisted-asset-operations';

const mockGetWhitelistedAssets = vi.fn();
const mockAddAssetToWhitelist = vi.fn();
const mockRemoveAssetFromWhitelist = vi.fn();

vi.mock('@/modules/assets/api/use-asset-whitelist-api', () => ({
  useAssetWhitelistApi: vi.fn(() => ({
    addAssetToWhitelist: mockAddAssetToWhitelist,
    getWhitelistedAssets: mockGetWhitelistedAssets,
    removeAssetFromWhitelist: mockRemoveAssetFromWhitelist,
  })),
}));

const mockFetchIgnoredAssets = vi.fn();

vi.mock('@/modules/assets/use-ignored-asset-operations', () => ({
  useIgnoredAssetOperations: vi.fn(() => ({
    fetchIgnoredAssets: mockFetchIgnoredAssets,
  })),
}));

const mockNotifyError = vi.fn();

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({
    notifyError: mockNotifyError,
  })),
}));

describe('useWhitelistedAssetOperations', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('fetchWhitelistedAssets', () => {
    it('should fetch and set whitelisted assets', async () => {
      const mockAssets = ['ETH', 'DAI'];
      mockGetWhitelistedAssets.mockResolvedValue(mockAssets);

      const { fetchWhitelistedAssets } = useWhitelistedAssetOperations();
      await fetchWhitelistedAssets();

      expect(mockGetWhitelistedAssets).toHaveBeenCalledOnce();
    });

    it('should notify on fetch error', async () => {
      mockGetWhitelistedAssets.mockRejectedValue(new Error('Network error'));

      const { fetchWhitelistedAssets } = useWhitelistedAssetOperations();
      await fetchWhitelistedAssets();

      expect(mockNotifyError).toHaveBeenCalledOnce();
    });
  });

  describe('whitelistAsset', () => {
    it('should whitelist an asset and refresh both lists', async () => {
      mockAddAssetToWhitelist.mockResolvedValue(true);
      mockGetWhitelistedAssets.mockResolvedValue(['DAI']);
      mockFetchIgnoredAssets.mockResolvedValue(undefined);

      const { whitelistAsset } = useWhitelistedAssetOperations();
      const result = await whitelistAsset('DAI');

      expect(result.success).toBe(true);
      expect(mockAddAssetToWhitelist).toHaveBeenCalledWith('DAI');
      expect(mockGetWhitelistedAssets).toHaveBeenCalledOnce();
      expect(mockFetchIgnoredAssets).toHaveBeenCalledOnce();
    });

    it('should notify on error', async () => {
      mockAddAssetToWhitelist.mockRejectedValue(new Error('API error'));

      const { whitelistAsset } = useWhitelistedAssetOperations();
      const result = await whitelistAsset('DAI');

      expect(result.success).toBe(false);
      assert(!result.success);
      expect(result.message).toBe('API error');
      expect(mockNotifyError).toHaveBeenCalledOnce();
    });
  });

  describe('unWhitelistAsset', () => {
    it('should unwhitelist an asset and refresh both lists', async () => {
      mockRemoveAssetFromWhitelist.mockResolvedValue(true);
      mockGetWhitelistedAssets.mockResolvedValue([]);
      mockFetchIgnoredAssets.mockResolvedValue(undefined);

      const { unWhitelistAsset } = useWhitelistedAssetOperations();
      const result = await unWhitelistAsset('DAI');

      expect(result.success).toBe(true);
      expect(mockRemoveAssetFromWhitelist).toHaveBeenCalledWith('DAI');
      expect(mockGetWhitelistedAssets).toHaveBeenCalledOnce();
      expect(mockFetchIgnoredAssets).toHaveBeenCalledOnce();
    });

    it('should notify on error', async () => {
      mockRemoveAssetFromWhitelist.mockRejectedValue(new Error('API error'));

      const { unWhitelistAsset } = useWhitelistedAssetOperations();
      const result = await unWhitelistAsset('DAI');

      expect(result.success).toBe(false);
      assert(!result.success);
      expect(result.message).toBe('API error');
      expect(mockNotifyError).toHaveBeenCalledOnce();
    });
  });
});
