import { mockUseNotifications } from '@test/utils/mocks/notifications';
import { get } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';

const { manualBalancesAssets, mockMarkAssetsAsSpam, mockNotifyError, mockNotifyWarning, mockRefreshSummary } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    manualBalancesAssets: ref<string[]>([]),
    mockMarkAssetsAsSpam: vi.fn<(tokens: string[]) => Promise<boolean>>(),
    mockNotifyError: vi.fn(),
    mockNotifyWarning: vi.fn(),
    mockRefreshSummary: vi.fn<() => Promise<void>>(),
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
  mockUseNotifications({ notifyError: mockNotifyError, notifyWarning: mockNotifyWarning }));

vi.mock('@/modules/history/data-issues/use-data-issues-summary', () => ({
  useDataIssuesSummary: vi.fn(() => ({ refreshSummary: mockRefreshSummary })),
}));

describe('useSpamAsset', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    manualBalancesAssets.value = [];
    mockMarkAssetsAsSpam.mockResolvedValue(true);
    mockRefreshSummary.mockResolvedValue(undefined);
  });

  describe('markAssetsAsSpam', () => {
    it('should mark every asset when none is in a manual balance and refresh data issues', async () => {
      const store = useDataIssuesInboxStore();
      const { markAssetsAsSpam } = useSpamAsset();

      const result = await markAssetsAsSpam(['SPAM1', 'SPAM2']);

      expect(result.success).toBe(true);
      expect(mockMarkAssetsAsSpam).toHaveBeenCalledWith(['SPAM1', 'SPAM2']);
      expect(mockNotifyWarning).not.toHaveBeenCalled();
      expect(get(store.issuesInvalidated)).toBe(1);
      expect(get(store.lastRemovedAssets)).toStrictEqual(['SPAM1', 'SPAM2']);
      expect(mockRefreshSummary).toHaveBeenCalledOnce();
    });

    it('should skip the assets held in manual balances and mark only the rest', async () => {
      const store = useDataIssuesInboxStore();
      manualBalancesAssets.value = ['MANUAL'];
      const { markAssetsAsSpam } = useSpamAsset();

      await markAssetsAsSpam(['SPAM1', 'MANUAL']);

      expect(mockNotifyWarning).toHaveBeenCalledExactlyOnceWith(
        'ignore.spam.warning.manual_balances_title',
        'ignore.spam.warning.manual_balances_message::MANUAL',
      );
      expect(mockMarkAssetsAsSpam).toHaveBeenCalledWith(['SPAM1']);
      expect(get(store.lastRemovedAssets)).toStrictEqual(['SPAM1']);
      expect(mockRefreshSummary).toHaveBeenCalledOnce();
    });

    it('should mark nothing and leave data issues untouched when every asset is in a manual balance', async () => {
      const store = useDataIssuesInboxStore();
      manualBalancesAssets.value = ['MANUAL'];
      const { markAssetsAsSpam } = useSpamAsset();

      await markAssetsAsSpam(['MANUAL']);

      expect(mockNotifyWarning).toHaveBeenCalledOnce();
      expect(mockMarkAssetsAsSpam).not.toHaveBeenCalled();
      expect(get(store.issuesInvalidated)).toBe(0);
      expect(mockRefreshSummary).not.toHaveBeenCalled();
    });

    it('should notify a failure unless the caller asks for silence and skip data issues refresh', async () => {
      const store = useDataIssuesInboxStore();
      mockMarkAssetsAsSpam.mockRejectedValue(new Error('backend down'));
      const { markAssetsAsSpam } = useSpamAsset();

      expect(await markAssetsAsSpam(['SPAM1'], { silent: true })).toEqual({ message: 'backend down', success: false });
      expect(mockNotifyError).not.toHaveBeenCalled();

      await markAssetsAsSpam(['SPAM1']);
      expect(mockNotifyError).toHaveBeenCalledOnce();
      expect(get(store.issuesInvalidated)).toBe(0);
      expect(mockRefreshSummary).not.toHaveBeenCalled();
    });
  });
});
