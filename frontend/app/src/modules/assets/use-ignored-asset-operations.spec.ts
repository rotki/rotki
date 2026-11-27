import { mockUseNotifications } from '@test/utils/mocks/notifications';
import { get, set } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';

const mockGetIgnoredAssets = vi.fn();
const mockAddIgnoredAssets = vi.fn();
const mockRemoveIgnoredAssets = vi.fn();
const mockRefreshSummary = vi.fn<() => Promise<void>>();

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

const { manualBalancesAssets } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { manualBalancesAssets: ref<string[]>([]) };
});

vi.mock('@/modules/balances/manual/use-manual-balance-data', () => ({
  useManualBalanceData: vi.fn(() => ({ manualBalancesAssets })),
}));

const { mockNotifyError, mockNotifyFailure, mockNotifyWarning } = vi.hoisted(() => ({
  mockNotifyError: vi.fn(),
  mockNotifyFailure: vi.fn(),
  mockNotifyWarning: vi.fn(),
}));

vi.mock('@/modules/core/notifications/use-notifications', () =>
  mockUseNotifications({ notifyError: mockNotifyError, notifyFailure: mockNotifyFailure, notifyWarning: mockNotifyWarning }));

vi.mock('@/modules/history/data-issues/use-data-issues-summary', () => ({
  useDataIssuesSummary: vi.fn(() => ({ refreshSummary: mockRefreshSummary })),
}));

describe('useIgnoredAssetOperations', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(manualBalancesAssets, []);
    mockRefreshSummary.mockResolvedValue(undefined);
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

      expect(mockNotifyFailure).toHaveBeenCalledOnce();
      expect(mockNotifyError).not.toHaveBeenCalled();
    });
  });

  describe('ignoreAsset', () => {
    it('should ignore assets successfully and notify the data issues inbox', async () => {
      const store = useDataIssuesInboxStore();
      mockAddIgnoredAssets.mockResolvedValue({ successful: ['DAI'], noAction: [] });

      const { ignoreAsset } = useIgnoredAssetOperations();
      const result = await ignoreAsset('DAI');

      expect(result.success).toBe(true);
      expect(mockAddIgnoredAssets).toHaveBeenCalledWith(['DAI']);
      expect(get(store.issuesInvalidated)).toBe(1);
      expect(get(store.lastRemovedAssets)).toStrictEqual(['DAI']);
      expect(mockRefreshSummary).toHaveBeenCalledOnce();
    });

    it('should skip refreshing the summary directly when an active reload listener exists', async () => {
      const store = useDataIssuesInboxStore();
      store.incrementReloadListeners();
      mockAddIgnoredAssets.mockResolvedValue({ successful: ['DAI'], noAction: [] });

      const { ignoreAsset } = useIgnoredAssetOperations();
      await ignoreAsset('DAI');

      expect(get(store.issuesInvalidated)).toBe(1);
      expect(get(store.lastRemovedAssets)).toStrictEqual(['DAI']);
      expect(mockRefreshSummary).not.toHaveBeenCalled();
    });

    it('should leave data issues untouched when no assets were newly ignored', async () => {
      const store = useDataIssuesInboxStore();
      mockAddIgnoredAssets.mockResolvedValue({ successful: [], noAction: ['DAI'] });

      const { ignoreAsset } = useIgnoredAssetOperations();
      await ignoreAsset('DAI');

      expect(get(store.issuesInvalidated)).toBe(0);
      expect(mockRefreshSummary).not.toHaveBeenCalled();
    });

    it('should toast a warning for assets held in manual balances and ignore only the rest', async () => {
      set(manualBalancesAssets, ['MANUAL']);
      mockAddIgnoredAssets.mockResolvedValue({ successful: ['DAI'], noAction: [] });

      const { ignoreAsset } = useIgnoredAssetOperations();
      const result = await ignoreAsset(['DAI', 'MANUAL']);

      expect(result.success).toBe(true);
      expect(mockNotifyWarning).toHaveBeenCalledExactlyOnceWith(
        'ignore.warning.manual_balances_title',
        'ignore.warning.manual_balances_message::MANUAL',
      );
      expect(mockAddIgnoredAssets).toHaveBeenCalledWith(['DAI']);
    });

    it('should not warn when no asset is held in a manual balance', async () => {
      mockAddIgnoredAssets.mockResolvedValue({ successful: ['DAI'], noAction: [] });

      const { ignoreAsset } = useIgnoredAssetOperations();
      await ignoreAsset('DAI');

      expect(mockNotifyWarning).not.toHaveBeenCalled();
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
