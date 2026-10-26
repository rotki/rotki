import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetsStore } from '@/modules/assets/use-assets-store';

describe('useAssetsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('isAssetIgnored', () => {
    it('should tell an ignored asset from one that is not', () => {
      const store = useAssetsStore();
      store.ignoredAssets = ['SPAM', 'SCAM'];

      expect(store.isAssetIgnored('SPAM')).toBe(true);
      expect(store.isAssetIgnored('ETH')).toBe(false);
    });

    it('should follow the list as it changes', () => {
      const store = useAssetsStore();
      store.ignoredAssets = ['SPAM'];
      expect(store.isAssetIgnored('SCAM')).toBe(false);

      store.addIgnoredAsset('SCAM');
      expect(store.isAssetIgnored('SCAM')).toBe(true);

      store.ignoredAssets = [];
      expect(store.isAssetIgnored('SPAM')).toBe(false);
    });

    it('should not add an asset that is already ignored twice', () => {
      const store = useAssetsStore();
      store.ignoredAssets = ['SPAM'];

      store.addIgnoredAsset('SPAM');

      expect(store.ignoredAssets).toStrictEqual(['SPAM']);
    });

    it('should answer without scanning the list each time, since a balance pass asks once per asset', () => {
      const store = useAssetsStore();
      const ignored = ['SPAM', 'SCAM'];
      const includes = vi.spyOn(ignored, 'includes');
      store.ignoredAssets = ignored;

      for (let i = 0; i < 100; i++)
        store.isAssetIgnored(`ASSET${i}`);

      expect(includes).not.toHaveBeenCalled();
      expect(store.isAssetIgnored('SCAM')).toBe(true);
    });
  });

  describe('isAssetWhitelisted', () => {
    it('should tell a whitelisted asset from one that is not, following the list', () => {
      const store = useAssetsStore();
      store.whitelistedAssets = ['GOOD'];

      expect(store.isAssetWhitelisted('GOOD')).toBe(true);
      expect(store.isAssetWhitelisted('SPAM')).toBe(false);

      store.whitelistedAssets = ['SPAM'];
      expect(store.isAssetWhitelisted('GOOD')).toBe(false);
      expect(store.isAssetWhitelisted('SPAM')).toBe(true);
    });

    it('should answer without scanning the list each time', () => {
      const store = useAssetsStore();
      const whitelisted = ['GOOD'];
      const includes = vi.spyOn(whitelisted, 'includes');
      store.whitelistedAssets = whitelisted;

      store.isAssetWhitelisted('GOOD');
      store.isAssetWhitelisted('OTHER');

      expect(includes).not.toHaveBeenCalled();
    });
  });
});
