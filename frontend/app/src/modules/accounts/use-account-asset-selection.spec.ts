import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountAssetSelection } from './use-account-asset-selection';
import '@test/i18n';

const h = vi.hoisted(() => ({
  ignoreAsset: vi.fn(),
  markAssetsAsSpam: vi.fn(),
  showErrorMessage: vi.fn(),
  unignoreAsset: vi.fn(),
}));

vi.mock('@/modules/assets/use-ignored-asset-operations', () => ({
  useIgnoredAssetOperations: vi.fn(() => ({ ignoreAsset: h.ignoreAsset, unignoreAsset: h.unignoreAsset })),
}));

vi.mock('@/modules/assets/use-spam-asset', () => ({
  useSpamAsset: vi.fn(() => ({ markAssetsAsSpam: h.markAssetsAsSpam })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ showErrorMessage: h.showErrorMessage })),
}));

describe('useAccountAssetSelection', () => {
  const onRefresh = vi.fn<() => Promise<void>>(async () => {});

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('toggleSelectionMode', () => {
    it('should enable selection mode and expose the selected assets', () => {
      const { selectedAssets, selectionMode, toggleSelectionMode } = useAccountAssetSelection(onRefresh);
      expect(get(selectionMode)).toBe(false);
      expect(get(selectedAssets)).toBeUndefined();

      toggleSelectionMode();
      expect(get(selectionMode)).toBe(true);
      set(selectedAssets, ['ETH']);
      expect(get(selectedAssets)).toEqual(['ETH']);
    });

    it('should clear the selection when disabling selection mode', () => {
      const { selectedAssets, selectionMode, toggleSelectionMode } = useAccountAssetSelection(onRefresh);
      toggleSelectionMode();
      set(selectedAssets, ['ETH']);
      toggleSelectionMode();
      expect(get(selectionMode)).toBe(false);
      expect(get(selectedAssets)).toBeUndefined();
    });
  });

  describe('handleIgnoreSelected', () => {
    it('should show an error and not ignore when nothing is selected', async () => {
      const { handleIgnoreSelected } = useAccountAssetSelection(onRefresh);
      await handleIgnoreSelected(true);
      expect(h.showErrorMessage).toHaveBeenCalledOnce();
      expect(h.ignoreAsset).not.toHaveBeenCalled();
    });

    it('should ignore the selected assets and refresh on success', async () => {
      h.ignoreAsset.mockResolvedValue({ success: true });
      const { handleIgnoreSelected, selectedAssets, selectionMode, toggleSelectionMode } = useAccountAssetSelection(onRefresh);
      toggleSelectionMode();
      set(selectedAssets, ['ETH', 'DAI']);

      await handleIgnoreSelected(true);
      expect(h.ignoreAsset).toHaveBeenCalledWith(['ETH', 'DAI']);
      expect(onRefresh).toHaveBeenCalledOnce();
      expect(get(selectionMode)).toBe(false);
    });

    it('should unignore the selected assets when ignored is false', async () => {
      h.unignoreAsset.mockResolvedValue({ success: true });
      const { handleIgnoreSelected, selectedAssets, toggleSelectionMode } = useAccountAssetSelection(onRefresh);
      toggleSelectionMode();
      set(selectedAssets, ['ETH']);

      await handleIgnoreSelected(false);
      expect(h.unignoreAsset).toHaveBeenCalledWith(['ETH']);
      expect(onRefresh).toHaveBeenCalledOnce();
    });

    it('should keep the selection when the operation fails', async () => {
      h.ignoreAsset.mockResolvedValue({ success: false });
      const { handleIgnoreSelected, selectedAssets, selectionMode, toggleSelectionMode } = useAccountAssetSelection(onRefresh);
      toggleSelectionMode();
      set(selectedAssets, ['ETH']);

      await handleIgnoreSelected(true);
      expect(onRefresh).not.toHaveBeenCalled();
      expect(get(selectionMode)).toBe(true);
      expect(get(selectedAssets)).toEqual(['ETH']);
    });
  });

  describe('handleMarkSelectedAsSpam', () => {
    it('should show an error when nothing is selected', async () => {
      const { handleMarkSelectedAsSpam } = useAccountAssetSelection(onRefresh);
      await handleMarkSelectedAsSpam();
      expect(h.showErrorMessage).toHaveBeenCalledOnce();
      expect(h.markAssetsAsSpam).not.toHaveBeenCalled();
    });

    it('should mark the selected assets as spam and refresh on success', async () => {
      h.markAssetsAsSpam.mockResolvedValue({ success: true });
      const { handleMarkSelectedAsSpam, selectedAssets, selectionMode, toggleSelectionMode } = useAccountAssetSelection(onRefresh);
      toggleSelectionMode();
      set(selectedAssets, ['SCAM']);

      await handleMarkSelectedAsSpam();
      expect(h.markAssetsAsSpam).toHaveBeenCalledWith(['SCAM']);
      expect(onRefresh).toHaveBeenCalledOnce();
      expect(get(selectionMode)).toBe(false);
    });
  });
});
