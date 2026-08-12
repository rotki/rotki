import type { SupportedAsset } from '@rotki/common';
import type { Ref } from 'vue';
import type { IgnoredAssetsHandlingType } from '@/modules/assets/types';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useManagedAssetOperations } from './use-managed-asset-operations';

const { spies } = vi.hoisted(() => ({
  spies: {
    showErrorMessage: vi.fn(),
    ignoreAssetWithConfirmation: vi.fn(),
    ignoreAsset: vi.fn(),
    unignoreAsset: vi.fn(),
    isAssetIgnored: vi.fn(),
    isAssetWhitelisted: vi.fn(),
    useIsAssetWhitelisted: vi.fn(),
    unWhitelistAsset: vi.fn(),
    whitelistAsset: vi.fn(),
    markAssetsAsSpam: vi.fn(),
    removeAssetFromSpamList: vi.fn(),
    refetchAssetInfo: vi.fn(),
  },
}));

// Mocked outright rather than spread over `...actual`: importActual evaluates the real
// notifications graph, which costs ~1.2s to import.
vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): object => ({ showErrorMessage: spies.showErrorMessage }),
}));
vi.mock('@/modules/assets/use-ignored-asset-confirmation', () => ({
  useIgnoredAssetConfirmation: (): object => ({ ignoreAssetWithConfirmation: spies.ignoreAssetWithConfirmation }),
}));
vi.mock('@/modules/assets/use-ignored-asset-operations', () => ({
  useIgnoredAssetOperations: (): object => ({ ignoreAsset: spies.ignoreAsset, unignoreAsset: spies.unignoreAsset }),
}));
vi.mock('@/modules/assets/use-assets-store', () => ({
  useAssetsStore: (): object => ({ isAssetIgnored: spies.isAssetIgnored, isAssetWhitelisted: spies.isAssetWhitelisted, useIsAssetWhitelisted: spies.useIsAssetWhitelisted }),
}));
vi.mock('@/modules/assets/use-whitelisted-asset-operations', () => ({
  useWhitelistedAssetOperations: (): object => ({ unWhitelistAsset: spies.unWhitelistAsset, whitelistAsset: spies.whitelistAsset }),
}));
vi.mock('@/modules/assets/use-spam-asset', () => ({
  useSpamAsset: (): object => ({ markAssetsAsSpam: spies.markAssetsAsSpam, removeAssetFromSpamList: spies.removeAssetFromSpamList }),
}));
vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): object => ({ refetchAssetInfo: spies.refetchAssetInfo }),
}));

function asset(overrides: Partial<SupportedAsset>): SupportedAsset {
  return createMock<SupportedAsset>({ identifier: 'ETH', name: 'Ether', symbol: 'ETH', ...overrides });
}

function setup(handling: IgnoredAssetsHandlingType, selectedIds: string[] = []): {
  ops: ReturnType<typeof useManagedAssetOperations>;
  onRefresh: ReturnType<typeof vi.fn>;
  selected: Ref<string[]>;
} {
  const onRefresh = vi.fn();
  const selected = ref<string[]>(selectedIds);
  const ops = useManagedAssetOperations(onRefresh, handling, selected);
  return { onRefresh, ops, selected };
}

describe('useManagedAssetOperations', () => {
  beforeEach(() => {
    spies.isAssetIgnored.mockReturnValue(false);
    spies.isAssetWhitelisted.mockReturnValue(false);
    spies.ignoreAsset.mockResolvedValue({ success: true });
    spies.unignoreAsset.mockResolvedValue({ success: true });
    spies.markAssetsAsSpam.mockResolvedValue({ success: true });
    spies.removeAssetFromSpamList.mockResolvedValue({ success: true });
    spies.whitelistAsset.mockResolvedValue(undefined);
    spies.unWhitelistAsset.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should unignore an ignored asset and refresh when handling is active', async () => {
    spies.isAssetIgnored.mockReturnValue(true);
    const { onRefresh, ops } = setup('show_only');
    await ops.toggleIgnoreAsset(asset({ identifier: 'A' }));
    expect(spies.unignoreAsset).toHaveBeenCalledWith('A');
    expect(onRefresh).toHaveBeenCalledOnce();
    expect(get(ops.loadingIgnore)).toBeUndefined();
  });

  it('should confirm before ignoring a new asset', async () => {
    const { ops } = setup('none');
    await ops.toggleIgnoreAsset(asset({ identifier: 'A', name: 'Asset A', symbol: '' }));
    expect(spies.ignoreAssetWithConfirmation).toHaveBeenCalledWith('A', 'Asset A', expect.any(Function));
  });

  it('should toggle spam on and off', async () => {
    const { onRefresh, ops } = setup('none');
    await ops.toggleSpam(asset({ identifier: 'A', protocol: 'spam' }));
    expect(spies.removeAssetFromSpamList).toHaveBeenCalledWith('A');

    await ops.toggleSpam(asset({ identifier: 'B' }));
    expect(spies.markAssetsAsSpam).toHaveBeenCalledWith(['B']);
    expect(spies.refetchAssetInfo).toHaveBeenCalledWith('B');
    expect(onRefresh).toHaveBeenCalledTimes(2);
  });

  it('should toggle whitelist state', async () => {
    spies.isAssetWhitelisted.mockReturnValueOnce(true);
    const { ops } = setup('none');
    await ops.toggleWhitelistAsset('A');
    expect(spies.unWhitelistAsset).toHaveBeenCalledWith('A');

    await ops.toggleWhitelistAsset('B');
    expect(spies.whitelistAsset).toHaveBeenCalledWith('B');
  });

  it('should mass-ignore the not-yet-ignored selection and clear it', async () => {
    const { ops, selected } = setup('show_only', ['a', 'b', 'a']);
    await ops.massIgnore(true);
    expect(spies.ignoreAsset).toHaveBeenCalledWith(['a', 'b']);
    expect(get(selected)).toEqual([]);
  });

  it('should warn when there is nothing to mass-ignore', async () => {
    const { ops } = setup('none', []);
    await ops.massIgnore(true);
    expect(spies.showErrorMessage).toHaveBeenCalledOnce();
    expect(spies.ignoreAsset).not.toHaveBeenCalled();
  });

  it('should mass-mark spam for the selection', async () => {
    const { ops, selected } = setup('none', ['a', 'b']);
    await ops.massSpam();
    expect(spies.markAssetsAsSpam).toHaveBeenCalledWith(['a', 'b']);
    expect(get(selected)).toEqual([]);
  });

  it('should warn when there is nothing to mass-spam', async () => {
    const { ops } = setup('none', []);
    await ops.massSpam();
    expect(spies.showErrorMessage).toHaveBeenCalledOnce();
    expect(spies.markAssetsAsSpam).not.toHaveBeenCalled();
  });
});
