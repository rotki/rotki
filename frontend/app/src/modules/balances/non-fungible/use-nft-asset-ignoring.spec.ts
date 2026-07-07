import type { NonFungibleBalance } from '@/modules/balances/types/nfbalances';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useNftAssetIgnoring } from './use-nft-asset-ignoring';

const { spies } = vi.hoisted(() => ({
  spies: {
    showErrorMessage: vi.fn(),
    ignoreAssetWithConfirmation: vi.fn(),
    ignoreAsset: vi.fn(),
    unignoreAsset: vi.fn(),
    isAssetIgnored: vi.fn(),
  },
}));

vi.mock('@/modules/core/notifications/use-notifications', async () => {
  const actual = await vi.importActual<typeof import('@/modules/core/notifications/use-notifications')>('@/modules/core/notifications/use-notifications');
  return { ...actual, useNotifications: (): object => ({ showErrorMessage: spies.showErrorMessage }) };
});
vi.mock('@/modules/assets/use-ignored-asset-confirmation', () => ({
  useIgnoredAssetConfirmation: (): object => ({ ignoreAssetWithConfirmation: spies.ignoreAssetWithConfirmation }),
}));
vi.mock('@/modules/assets/use-ignored-asset-operations', () => ({
  useIgnoredAssetOperations: (): object => ({ ignoreAsset: spies.ignoreAsset, unignoreAsset: spies.unignoreAsset }),
}));
vi.mock('@/modules/assets/use-assets-store', () => ({
  useAssetsStore: (): object => ({ isAssetIgnored: spies.isAssetIgnored }),
}));

function balance(id: string): NonFungibleBalance {
  return createMock<NonFungibleBalance>({ id, name: id });
}

describe('useNftAssetIgnoring', () => {
  const fetchData = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    spies.isAssetIgnored.mockReturnValue(false);
    spies.ignoreAsset.mockResolvedValue({ success: true });
    spies.unignoreAsset.mockResolvedValue({ success: true });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should refresh only when ignored assets are being shown', () => {
    useNftAssetIgnoring(fetchData, 'none').refreshCallback();
    expect(fetchData).not.toHaveBeenCalled();

    useNftAssetIgnoring(fetchData, 'show_only').refreshCallback();
    expect(fetchData).toHaveBeenCalledOnce();
  });

  it('should unignore an already-ignored asset on toggle', async () => {
    spies.isAssetIgnored.mockReturnValue(true);
    await useNftAssetIgnoring(fetchData, 'show_only').toggleIgnoreAsset(balance('nft-1'));
    expect(spies.unignoreAsset).toHaveBeenCalledWith('nft-1');
    expect(spies.ignoreAssetWithConfirmation).not.toHaveBeenCalled();
  });

  it('should confirm before ignoring a new asset on toggle', async () => {
    await useNftAssetIgnoring(fetchData, 'none').toggleIgnoreAsset(balance('nft-2'));
    expect(spies.ignoreAssetWithConfirmation).toHaveBeenCalledWith('nft-2', 'nft-2', expect.any(Function));
  });

  it('should mass-ignore the not-yet-ignored selection and clear it', async () => {
    const { massIgnore, selected } = useNftAssetIgnoring(fetchData, 'show_only');
    set(selected, ['a', 'b', 'a']);
    await massIgnore(true);
    expect(spies.ignoreAsset).toHaveBeenCalledWith(['a', 'b']);
    expect(get(selected)).toEqual([]);
    expect(fetchData).toHaveBeenCalledOnce();
  });

  it('should warn when there is nothing to mass-ignore', async () => {
    spies.isAssetIgnored.mockReturnValue(true); // all already ignored
    const { massIgnore, selected } = useNftAssetIgnoring(fetchData, 'none');
    set(selected, ['a']);
    await massIgnore(true);
    expect(spies.showErrorMessage).toHaveBeenCalledOnce();
    expect(spies.ignoreAsset).not.toHaveBeenCalled();
  });
});
