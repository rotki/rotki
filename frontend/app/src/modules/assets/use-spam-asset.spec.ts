import { mockUseNotifications } from '@test/utils/mocks/notifications';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';

const { manualBalancesAssets, mockMarkAssetsAsSpam, mockNotifyWarning } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    manualBalancesAssets: ref<string[]>([]),
    mockMarkAssetsAsSpam: vi.fn<(tokens: string[]) => Promise<boolean>>(),
    mockNotifyWarning: vi.fn(),
  };
});

vi.mock('@/modules/assets/api/use-asset-spam-api', () => ({
  useAssetSpamApi: vi.fn(() => ({
    markAssetsAsSpam: mockMarkAssetsAsSpam,
    removeAssetFromSpamList: vi.fn(),
  })),
}));

vi.mock('@/modules/assets/use-whitelisted-asset-operations', () => ({
  useWhitelistedAssetOperations: vi.fn(() => ({ fetchWhitelistedAssets: vi.fn() })),
}));

vi.mock('@/modules/assets/use-ignored-asset-operations', () => ({
  useIgnoredAssetOperations: vi.fn(() => ({ fetchIgnoredAssets: vi.fn() })),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn(() => ({
    getAssetField: vi.fn((id: string, _field: string): string => id),
  })),
}));

vi.mock('@/modules/balances/manual/use-manual-balance-data', () => ({
  useManualBalanceData: vi.fn(() => ({ manualBalancesAssets })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () =>
  mockUseNotifications({ notifyWarning: mockNotifyWarning }));

describe('useSpamAsset', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    manualBalancesAssets.value = [];
    mockMarkAssetsAsSpam.mockResolvedValue(true);
  });

  describe('markAssetsAsSpam', () => {
    it('should mark every asset when none is in a manual balance', async () => {
      const { markAssetsAsSpam } = useSpamAsset();

      const result = await markAssetsAsSpam(['SPAM1', 'SPAM2']);

      expect(result.success).toBe(true);
      expect(mockMarkAssetsAsSpam).toHaveBeenCalledWith(['SPAM1', 'SPAM2']);
      expect(mockNotifyWarning).not.toHaveBeenCalled();
    });

    it('should skip the assets held in manual balances and mark only the rest', async () => {
      manualBalancesAssets.value = ['MANUAL'];
      const { markAssetsAsSpam } = useSpamAsset();

      await markAssetsAsSpam(['SPAM1', 'MANUAL']);

      expect(mockNotifyWarning).toHaveBeenCalledExactlyOnceWith(
        'ignore.spam.warning.manual_balances_title',
        'ignore.spam.warning.manual_balances_message::MANUAL',
      );
      expect(mockMarkAssetsAsSpam).toHaveBeenCalledWith(['SPAM1']);
    });

    it('should mark nothing when every asset is in a manual balance', async () => {
      manualBalancesAssets.value = ['MANUAL'];
      const { markAssetsAsSpam } = useSpamAsset();

      await markAssetsAsSpam(['MANUAL']);

      expect(mockNotifyWarning).toHaveBeenCalledOnce();
      expect(mockMarkAssetsAsSpam).not.toHaveBeenCalled();
    });
  });
});
