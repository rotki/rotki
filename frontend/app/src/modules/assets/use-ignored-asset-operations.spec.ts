import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';

const mockGetIgnoredAssets = vi.fn();
const mockAddIgnoredAssets = vi.fn();
const mockRemoveIgnoredAssets = vi.fn();

vi.mock('@/modules/assets/api/use-asset-ignore-api', () => ({
  useAssetIgnoreApi: vi.fn(() => ({
    addIgnoredAssets: mockAddIgnoredAssets,
    getIgnoredAssets: mockGetIgnoredAssets,
    removeIgnoredAssets: mockRemoveIgnoredAssets,
  })),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({
    getAssetField: vi.fn((id: string, _field: string): string => id),
  })),
}));

vi.mock('@/modules/balances/manual/use-manual-balance-data', () => ({
  useManualBalanceData: vi.fn(() => ({
    manualBalancesAssets: ref<string[]>([]),
  })),
}));

const mockNotifyError = vi.fn();
const mockShowErrorMessage = vi.fn();

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({
    notifyError: mockNotifyError,
    showErrorMessage: mockShowErrorMessage,
  })),
}));

describe('useIgnoredAssetOperations', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('fetchIgnoredAssets', () => {
    it('should fetch and set ignored assets', async () => {
      const mockAssets = ['ETH', 'DAI'];
      mockGetIgnoredAssets.mockResolvedValue(mockAssets);

      const { fetchIgnoredAssets } = useIgnoredAssetOperations();
      await fetchIgnoredAssets();

      expect(mockGetIgnoredAssets).toHaveBeenCalledOnce();
    });

    it('should notify on fetch error', async () => {
      mockGetIgnoredAssets.mockRejectedValue(new Error('Network error'));

      const { fetchIgnoredAssets } = useIgnoredAssetOperations();
      await fetchIgnoredAssets();

      expect(mockNotifyError).toHaveBeenCalledOnce();
    });
  });

  describe('ignoreAsset', () => {
    it('should ignore assets successfully', async () => {
      mockAddIgnoredAssets.mockResolvedValue({ successful: ['DAI'], noAction: [] });

      const { ignoreAsset } = useIgnoredAssetOperations();
      const result = await ignoreAsset('DAI');

      expect(result.success).toBe(true);
      expect(mockAddIgnoredAssets).toHaveBeenCalledWith(['DAI']);
    });

    it('should handle multiple assets', async () => {
      mockAddIgnoredAssets.mockResolvedValue({ successful: ['DAI', 'USDC'], noAction: [] });

      const { ignoreAsset } = useIgnoredAssetOperations();
      const result = await ignoreAsset(['DAI', 'USDC']);

      expect(result.success).toBe(true);
      expect(mockAddIgnoredAssets).toHaveBeenCalledWith(['DAI', 'USDC']);
    });

    it('should notify on error', async () => {
      mockAddIgnoredAssets.mockRejectedValue(new Error('API error'));

      const { ignoreAsset } = useIgnoredAssetOperations();
      const result = await ignoreAsset('DAI');

      expect(result.success).toBe(false);
      assert(!result.success);
      expect(result.message).toBe('API error');
      expect(mockNotifyError).toHaveBeenCalledOnce();
    });
  });

  describe('unignoreAsset', () => {
    it('should unignore assets successfully', async () => {
      mockRemoveIgnoredAssets.mockResolvedValue({ successful: ['ETH'], noAction: [] });

      const { unignoreAsset } = useIgnoredAssetOperations();
      const result = await unignoreAsset('ETH');

      expect(result.success).toBe(true);
      expect(mockRemoveIgnoredAssets).toHaveBeenCalledWith(['ETH']);
    });

    it('should notify on error', async () => {
      mockRemoveIgnoredAssets.mockRejectedValue(new Error('API error'));

      const { unignoreAsset } = useIgnoredAssetOperations();
      const result = await unignoreAsset('ETH');

      expect(result.success).toBe(false);
      assert(!result.success);
      expect(result.message).toBe('API error');
      expect(mockNotifyError).toHaveBeenCalledOnce();
    });
  });
});
