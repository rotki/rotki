import type { ERC20Token } from '@/modules/accounts/blockchain-accounts';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetInfoApi } from '@/composables/api/assets/info';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { CUSTOM_ASSET } from '@/modules/assets/types';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { useNotificationDispatcher } from '@/modules/notifications/use-notification-dispatcher';

const runTaskMock = vi.fn();

vi.mock('@/composables/api/assets/info', () => ({
  useAssetInfoApi: vi.fn().mockReturnValue({
    erc20details: vi.fn().mockResolvedValue(1),
  }),
}));

vi.mock('@/modules/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => {
      await taskFn();
      return runTaskMock(taskFn, ...rest);
    },
    cancelTask: vi.fn(),
    cancelTaskByTaskType: vi.fn(),
  }),
}));

vi.mock('@/modules/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn().mockReturnValue({
    notify: vi.fn(),
  }),
}));

vi.mock('@/store/notifications/index', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    removeMatching: vi.fn(),
  }),
}));

describe('useAssetRetrieval', () => {
  let assetInfoRetrieval: ReturnType<typeof useAssetInfoRetrieval>;
  let assetInfoCache: ReturnType<typeof useAssetInfoCache>;
  let api: ReturnType<typeof useAssetInfoApi>;

  beforeEach(() => {
    setActivePinia(createPinia());
    assetInfoCache = useAssetInfoCache();
    vi.spyOn(assetInfoCache, 'isPending');
    vi.spyOn(assetInfoCache, 'resolve');
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

      runTaskMock.mockResolvedValue({ success: true, result: tokenDetail });

      const result = await assetInfoRetrieval.fetchTokenDetails(payload);

      expect(api.erc20details).toHaveBeenCalledWith(payload);

      expect(result).toEqual(tokenDetail);

      expect(useNotificationDispatcher().notify).not.toHaveBeenCalled();
    });

    it('should handle failure', async () => {
      runTaskMock.mockResolvedValue({ success: false, message: 'failed', cancelled: false, backendCancelled: false, skipped: false });

      const result = await assetInfoRetrieval.fetchTokenDetails(payload);

      expect(api.erc20details).toHaveBeenCalledWith(payload);

      expect(result).toEqual({});

      expect(useNotificationDispatcher().notify).toHaveBeenCalled();
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

      vi.mocked(assetInfoCache.resolve).mockReturnValue(({
        name: assetName,
        isCustomAsset: true,
      }));

      const result = assetInfoRetrieval.getAssetInfo(identifier);

      expect(assetInfoCache.resolve).toHaveBeenCalledWith(identifier);

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

      vi.mocked(assetInfoCache.resolve).mockReturnValue(({
        name: assetName,
        assetType: CUSTOM_ASSET,
      }));

      const result = assetInfoRetrieval.getAssetInfo(identifier);

      expect(assetInfoCache.resolve).toHaveBeenCalledWith(identifier);

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

      set(assetInfoCache.fetchedAssetCollections, {
        [collectionId]: {
          name: collectionName,
          symbol: assetSymbol,
          mainAsset: identifier,
        },
      });

      vi.mocked(assetInfoCache.resolve).mockReturnValue(({
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

      set(assetInfoCache.fetchedAssetCollections, {
        [collectionId]: {
          name: collectionName,
          symbol: assetSymbol,
          mainAsset: identifier,
        },
      });

      vi.mocked(assetInfoCache.resolve).mockReturnValue(({
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
      vi.mocked(assetInfoCache.resolve).mockReturnValue(null);

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
