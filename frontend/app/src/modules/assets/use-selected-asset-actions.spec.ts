import type { ActionStatus } from '@/modules/core/common/action';
import { mockUseNotifications } from '@test/utils/mocks/notifications';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSelectedAssetIgnoring, useSelectedAssetSpam } from '@/modules/assets/use-selected-asset-actions';

const { spies } = vi.hoisted(() => ({
  spies: {
    ignoreAsset: vi.fn<(assets: string[]) => Promise<ActionStatus>>(),
    isAssetIgnored: vi.fn<(identifier: string) => boolean>(),
    markAssetsAsSpam: vi.fn<(tokens: string[]) => Promise<ActionStatus>>(),
    notifyWarning: vi.fn<(title: string, message: string) => void>(),
    unignoreAsset: vi.fn<(assets: string[]) => Promise<ActionStatus>>(),
  },
}));

vi.mock('@/modules/assets/use-assets-store', () => ({
  useAssetsStore: (): object => ({ isAssetIgnored: spies.isAssetIgnored }),
}));

vi.mock('@/modules/assets/use-ignored-asset-operations', () => ({
  useIgnoredAssetOperations: (): object => ({ ignoreAsset: spies.ignoreAsset, unignoreAsset: spies.unignoreAsset }),
}));

vi.mock('@/modules/assets/use-spam-asset', () => ({
  useSpamAsset: (): object => ({ markAssetsAsSpam: spies.markAssetsAsSpam }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () =>
  mockUseNotifications({ notifyWarning: spies.notifyWarning }));

describe('useSelectedAssetIgnoring', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spies.isAssetIgnored.mockReturnValue(false);
    spies.ignoreAsset.mockResolvedValue({ success: true });
  });

  it('should toast a warning and skip the backend when nothing is left to ignore', async () => {
    spies.isAssetIgnored.mockReturnValue(true);

    const result = await useSelectedAssetIgnoring().ignoreSelected(['ETH'], true);

    expect(result).toBe(false);
    expect(spies.notifyWarning).toHaveBeenCalledExactlyOnceWith('ignore.no_items.title::', 'ignore.no_items.description::');
    expect(spies.ignoreAsset).not.toHaveBeenCalled();
  });

  it('should ignore the selection without a warning', async () => {
    const result = await useSelectedAssetIgnoring().ignoreSelected(['ETH', 'ETH'], true);

    expect(result).toBe(true);
    expect(spies.ignoreAsset).toHaveBeenCalledWith(['ETH']);
    expect(spies.notifyWarning).not.toHaveBeenCalled();
  });
});

describe('useSelectedAssetSpam', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spies.markAssetsAsSpam.mockResolvedValue({ success: true });
  });

  it('should toast a warning and skip the backend for an empty selection', async () => {
    const result = await useSelectedAssetSpam().markSelectedAsSpam([]);

    expect(result).toBe(false);
    expect(spies.notifyWarning).toHaveBeenCalledExactlyOnceWith('ignore.spam.no_items.title', 'ignore.spam.no_items.description');
    expect(spies.markAssetsAsSpam).not.toHaveBeenCalled();
  });

  it('should mark the selection as spam without a warning', async () => {
    const result = await useSelectedAssetSpam().markSelectedAsSpam(['SPAM']);

    expect(result).toBe(true);
    expect(spies.markAssetsAsSpam).toHaveBeenCalledWith(['SPAM']);
    expect(spies.notifyWarning).not.toHaveBeenCalled();
  });
});
