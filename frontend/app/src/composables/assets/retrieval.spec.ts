import type { ERC20Token } from '@/types/blockchain/accounts';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useAssetCacheStore } from '@/store/assets/asset-cache';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { CUSTOM_ASSET } from '@/types/asset';

vi.mock('@/composables/api/assets/info', () => ({
  useAssetInfoApi: vi.fn().mockReturnValue({
    erc20details: vi.fn().mockResolvedValue(1),
  }),
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/store/notifications/index', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    notify: vi.fn().mockReturnValue({}),
  }),
}));

describe('useAssetRetrieval', () => {
  let assetInfoRetrieval: ReturnType<typeof useAssetInfoRetrieval>;
  let assetCacheStore: ReturnType<typeof useAssetCacheStore>;
  let api: ReturnType<typeof useAssetInfoApi>;

  beforeEach(() => {
    setActivePinia(createPinia());
    assetCacheStore = useAssetCacheStore();
    vi.spyOn(assetCacheStore, 'isPending');
    vi.spyOn(assetCacheStore, 'resolve');
    assetInfoRetrieval = useAssetInfoRetrieval();
    api = useAssetInfoApi();
  });

  describe('fetchTokenDetails', () => {
    const payload = {
      address: '0x12BB890508c125661E03b09EC06E404bc9289040',
      evmChain: 'ethereum',
    };

    it('should succeed', async () => {
      const tokenDetail: ERC20Token = {
        decimals: 18,
        name: 'Radio Caca',
        symbol: 'RACA',
      };

      vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
        result: tokenDetail,
        meta: { title: '' },
      });

      const result = await assetInfoRetrieval.fetchTokenDetails(payload);

      expect(api.erc20details).toHaveBeenCalledWith(payload);

      expect(result).toEqual(tokenDetail);

      expect(useNotificationsStore().notify).not.toHaveBeenCalled();
    });

    it('should handle failure', async () => {
      vi.mocked(useTaskStore().awaitTask).mockRejectedValue(new Error('failed'));

      const result = await assetInfoRetrieval.fetchTokenDetails(payload);

      expect(api.erc20details).toHaveBeenCalledWith(payload);

      expect(result).toEqual({});

      expect(useNotificationsStore().notify).toHaveBeenCalled();
    });
  });

  describe('getAssetInfo and getAssetField', () => {
    it('should handle falsy identifier', () => {
      const identifier = undefined;
      expect(assetInfoRetrieval.getAssetInfo(identifier)).toBeNull();
      expect(assetInfoRetrieval.getAssetField(identifier, 'name')).toBe('');
      expect(assetInfoRetrieval.getAssetField(identifier, 'symbol')).toBe('');
    });

    it('should handle custom asset', () => {
      const identifier = 'ASSET_ID';
      const assetName = 'ASSET_NAME';

      vi.mocked(assetCacheStore.resolve).mockReturnValue(({
        name: assetName,
        isCustomAsset: true,
      }));

      const result = assetInfoRetrieval.getAssetInfo(identifier);

      expect(assetCacheStore.resolve).toHaveBeenCalledWith(identifier);

      expect(result).toMatchObject({
        name: assetName,
        symbol: assetName,
        isCustomAsset: true,
      });

      expect(assetInfoRetrieval.getAssetField(identifier, 'name')).toEqual(assetName);
      expect(assetInfoRetrieval.getAssetField(identifier, 'symbol')).toEqual(assetName);
    });

    it('should handle custom asset type', () => {
      const identifier = 'ASSET_ID';
      const assetName = 'ASSET_NAME';

      vi.mocked(assetCacheStore.resolve).mockReturnValue(({
        name: assetName,
        assetType: CUSTOM_ASSET,
      }));

      const result = assetInfoRetrieval.getAssetInfo(identifier);

      expect(assetCacheStore.resolve).toHaveBeenCalledWith(identifier);

      expect(result).toMatchObject({
        name: assetName,
        symbol: assetName,
        isCustomAsset: true,
      });

      expect(assetInfoRetrieval.getAssetField(identifier, 'name')).toEqual(assetName);
      expect(assetInfoRetrieval.getAssetField(identifier, 'symbol')).toEqual(assetName);
    });

    it('should handle asset with collection parent when isCollectionParent is true', () => {
      const identifier = 'USDC_IN_OPTIMISM';
      const collectionId = '1';
      const assetName = 'USDC in Optimism';
      const assetSymbol = 'USDC';
      const collectionName = 'USDC Generic Name';

      const { fetchedAssetCollections } = storeToRefs(assetCacheStore);

      set(fetchedAssetCollections, {
        [collectionId]: {
          name: collectionName,
          symbol: assetSymbol,
          mainAsset: identifier,
        },
      });

      vi.mocked(assetCacheStore.resolve).mockReturnValue(({
        name: assetName,
        symbol: assetSymbol,
        collectionId,
      }));

      const result = assetInfoRetrieval.getAssetInfo(identifier);

      expect(result).toMatchObject({
        name: collectionName,
        symbol: assetSymbol,
      });

      expect(assetInfoRetrieval.getAssetField(identifier, 'name')).toEqual(collectionName);
      expect(assetInfoRetrieval.getAssetField(identifier, 'symbol')).toEqual(assetSymbol);
    });

    it('should handle asset with collection parent when isCollectionParent is false', () => {
      const identifier = 'USDC_IN_OPTIMISM';
      const collectionId = '1';
      const assetName = 'USDC in Optimism';
      const assetSymbol = 'USDC';
      const collectionName = 'USDC Generic Name';

      const { fetchedAssetCollections } = storeToRefs(assetCacheStore);

      set(fetchedAssetCollections, {
        [collectionId]: {
          name: collectionName,
          symbol: assetSymbol,
          mainAsset: identifier,
        },
      });

      vi.mocked(assetCacheStore.resolve).mockReturnValue(({
        name: assetName,
        symbol: assetSymbol,
        collectionId,
      }));

      const result = assetInfoRetrieval.getAssetInfo(identifier, {
        associate: true,
        collectionParent: false,
      });

      expect(result).toMatchObject({
        name: assetName,
        symbol: assetSymbol,
      });
    });

    it('should use fallback for asset name and symbol', () => {
      const address = '0x12BB890508c125661E03b09EC06E404bc9289040';
      const identifier = `eip155:1/erc20:${address}`;
      vi.mocked(assetCacheStore.resolve).mockReturnValue(null);

      const result = assetInfoRetrieval.getAssetInfo(identifier);
      const fallbackName = `EVM Token: ${address}`;

      expect(result).toMatchObject({
        name: fallbackName,
        symbol: fallbackName,
      });

      expect(assetInfoRetrieval.getAssetField(identifier, 'name')).toEqual(fallbackName);
      expect(assetInfoRetrieval.getAssetField(identifier, 'symbol')).toEqual(fallbackName);
    });
  });
});
