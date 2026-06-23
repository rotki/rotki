import type { AssetInfo } from '@rotki/common';
import { describe, expect, it, vi } from 'vitest';
import { ref, type Ref } from 'vue';
import { useSnapshotAssetFilters } from '@/modules/dashboard/snapshots/composables/use-snapshot-asset-filters';

const cache = ref<Record<string, AssetInfo | null>>({});
const isAssetIgnored = vi.fn();

// Reads the cache RECORD directly — must not trigger a mappings fetch.
vi.mock('@/modules/assets/use-asset-info-cache', () => ({
  useAssetInfoCache: (): { cache: Ref<Record<string, AssetInfo | null>> } => ({ cache }),
}));

vi.mock('@/modules/assets/use-assets-store', () => ({
  useAssetsStore: (): { isAssetIgnored: typeof isAssetIgnored } => ({ isAssetIgnored }),
}));

// ETH2 resolves to ETH (the cache is keyed by the resolved identifier).
vi.mock('@/modules/assets/use-resolve-asset-identifier', () => ({
  useResolveAssetIdentifier: (): ((id: string) => string) => (id: string): string => (id === 'ETH2' ? 'ETH' : id),
}));

describe('modules/dashboard/snapshots/composables/use-snapshot-asset-filters', () => {
  it('should treat a cached asset flagged isSpam as spam', () => {
    set(cache, { SPAM: { isSpam: true, name: 'Spammy', symbol: 'SPAM' } });
    expect(useSnapshotAssetFilters().isSpamAsset('SPAM')).toBe(true);
  });

  it('should treat a cached asset whose protocol is spam as spam', () => {
    set(cache, { SPAM: { name: 'Spammy', protocol: 'spam', symbol: 'SPAM' } });
    expect(useSnapshotAssetFilters().isSpamAsset('SPAM')).toBe(true);
  });

  it('should not treat a normal cached asset as spam', () => {
    set(cache, { ETH: { name: 'Ethereum', protocol: 'eth', symbol: 'ETH' } });
    expect(useSnapshotAssetFilters().isSpamAsset('ETH')).toBe(false);
  });

  it('should treat an asset not in the cache as non-spam (no fetch)', () => {
    set(cache, {});
    expect(useSnapshotAssetFilters().isSpamAsset('UNRESOLVED')).toBe(false);
  });

  it('should resolve the identifier before reading the cache', () => {
    set(cache, { ETH: { name: 'Ethereum', protocol: 'spam', symbol: 'ETH' } });
    // ETH2 resolves to ETH, so it inherits ETH's cached spam flag.
    expect(useSnapshotAssetFilters().isSpamAsset('ETH2')).toBe(true);
  });

  it('should delegate the ignored check to the assets store', () => {
    isAssetIgnored.mockReturnValue(true);
    expect(useSnapshotAssetFilters().isIgnoredAsset('DAI')).toBe(true);
    expect(isAssetIgnored).toHaveBeenCalledWith('DAI');
  });
});
