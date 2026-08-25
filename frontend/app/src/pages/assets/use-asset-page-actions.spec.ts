import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, type ComputedRef, type Ref, shallowRef } from 'vue';
import { useAssetPageActions } from './use-asset-page-actions';

const IDENTIFIER = 'eip155:1/erc20:0xabc';

const {
  ignoreAssetWithConfirmation,
  ignoredState,
  markAssetsAsSpam,
  removeAssetFromSpamList,
  unWhitelistAsset,
  unignoreAsset,
  whitelistAsset,
} = vi.hoisted(() => ({
  ignoreAssetWithConfirmation: vi.fn(async (): Promise<void> => {}),
  ignoredState: { ignored: false, whitelisted: false },
  markAssetsAsSpam: vi.fn(async (): Promise<void> => {}),
  removeAssetFromSpamList: vi.fn(async (): Promise<void> => {}),
  unWhitelistAsset: vi.fn(async (): Promise<void> => {}),
  unignoreAsset: vi.fn(async (): Promise<void> => {}),
  whitelistAsset: vi.fn(async (): Promise<void> => {}),
}));

vi.mock('@/modules/assets/use-ignored-asset-confirmation', () => ({
  useIgnoredAssetConfirmation: (): { ignoreAssetWithConfirmation: typeof ignoreAssetWithConfirmation } => ({
    ignoreAssetWithConfirmation,
  }),
}));

vi.mock('@/modules/assets/use-ignored-asset-operations', () => ({
  useIgnoredAssetOperations: (): { unignoreAsset: typeof unignoreAsset } => ({ unignoreAsset }),
}));

vi.mock('@/modules/assets/use-assets-store', async () => {
  const { computed: computedFn } = await import('vue');
  return {
    useAssetsStore: (): {
      useIsAssetIgnored: () => ComputedRef<boolean>;
      useIsAssetWhitelisted: () => ComputedRef<boolean>;
    } => ({
      useIsAssetIgnored: (): ComputedRef<boolean> => computedFn(() => ignoredState.ignored),
      useIsAssetWhitelisted: (): ComputedRef<boolean> => computedFn(() => ignoredState.whitelisted),
    }),
  };
});

vi.mock('@/modules/assets/use-whitelisted-asset-operations', () => ({
  useWhitelistedAssetOperations: (): {
    unWhitelistAsset: typeof unWhitelistAsset;
    whitelistAsset: typeof whitelistAsset;
  } => ({ unWhitelistAsset, whitelistAsset }),
}));

vi.mock('@/modules/assets/use-spam-asset', () => ({
  useSpamAsset: (): { markAssetsAsSpam: typeof markAssetsAsSpam; removeAssetFromSpamList: typeof removeAssetFromSpamList } => ({
    markAssetsAsSpam,
    removeAssetFromSpamList,
  }),
}));

describe('pages/assets/useAssetPageActions', () => {
  const refetchAssetInfo = vi.fn();
  let asset: Ref<{ isSpam?: boolean; name?: string | null; symbol?: string | null } | null>;

  function setup(): ReturnType<typeof useAssetPageActions> {
    return useAssetPageActions({
      asset: computed(() => get(asset)),
      identifier: shallowRef(IDENTIFIER),
      refetchAssetInfo,
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    ignoredState.ignored = false;
    ignoredState.whitelisted = false;
    asset = shallowRef({ isSpam: false, symbol: 'ABC' });
  });

  describe('spam', () => {
    it('should mark an asset as spam and refresh its info', async () => {
      await setup().toggleSpam();

      expect(markAssetsAsSpam).toHaveBeenCalledWith([IDENTIFIER]);
      expect(removeAssetFromSpamList).not.toHaveBeenCalled();
      expect(refetchAssetInfo).toHaveBeenCalledWith(IDENTIFIER);
    });

    it('should take an asset back off the spam list', async () => {
      set(asset, { isSpam: true });

      await setup().toggleSpam();

      expect(removeAssetFromSpamList).toHaveBeenCalledWith(IDENTIFIER);
      expect(markAssetsAsSpam).not.toHaveBeenCalled();
    });

    it('should read an asset with no spam flag as not spam', async () => {
      set(asset, { symbol: 'ABC' });

      const { isSpam, toggleSpam } = setup();
      expect(get(isSpam)).toBe(false);

      await toggleSpam();

      expect(markAssetsAsSpam).toHaveBeenCalled();
    });

    it('should lower the loading flag even when the call fails', async () => {
      markAssetsAsSpam.mockRejectedValueOnce(new Error('nope'));

      const { loadingSpam, toggleSpam } = setup();

      await expect(toggleSpam()).rejects.toThrow('nope');
      expect(get(loadingSpam)).toBe(false);
    });
  });

  describe('ignore', () => {
    it('should ask for confirmation when ignoring, preferring the symbol over the name', async () => {
      // Both are set, so this fails if the fallback order is reversed. With only one of them
      // present either order produces the same string and the test proves nothing.
      set(asset, { name: 'Some Token', symbol: 'ABC' });

      await setup().toggleIgnoreAsset();

      expect(ignoreAssetWithConfirmation).toHaveBeenCalledWith(IDENTIFIER, 'ABC');
      expect(unignoreAsset).not.toHaveBeenCalled();
    });

    it('should fall back to the name when the asset has no symbol', async () => {
      set(asset, { name: 'Some Token', symbol: null });

      await setup().toggleIgnoreAsset();

      expect(ignoreAssetWithConfirmation).toHaveBeenCalledWith(IDENTIFIER, 'Some Token');
    });

    it('should unignore without a confirmation when the asset is already ignored', async () => {
      ignoredState.ignored = true;

      await setup().toggleIgnoreAsset();

      expect(unignoreAsset).toHaveBeenCalledWith(IDENTIFIER);
      expect(ignoreAssetWithConfirmation).not.toHaveBeenCalled();
    });

    it('should not refresh the asset info, which the ignore flow owns', async () => {
      await setup().toggleIgnoreAsset();

      expect(refetchAssetInfo).not.toHaveBeenCalled();
    });
  });

  describe('whitelist', () => {
    it('should whitelist an asset that is not on the list', async () => {
      await setup().toggleWhitelistAsset();

      expect(whitelistAsset).toHaveBeenCalledWith(IDENTIFIER);
      expect(unWhitelistAsset).not.toHaveBeenCalled();
      expect(refetchAssetInfo).toHaveBeenCalledWith(IDENTIFIER);
    });

    it('should remove an asset that is already whitelisted', async () => {
      ignoredState.whitelisted = true;

      await setup().toggleWhitelistAsset();

      expect(unWhitelistAsset).toHaveBeenCalledWith(IDENTIFIER);
      expect(whitelistAsset).not.toHaveBeenCalled();
    });
  });

  it('should report the ignored state it was given', () => {
    ignoredState.ignored = true;

    expect(get(setup().isIgnored)).toBe(true);
  });
});
