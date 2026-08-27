import type { ERC20Token } from '@/modules/accounts/blockchain-accounts';
import { HYPERLIQUID_TOKEN_ADDRESS } from '@test/utils/asset-test-data';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { neverSettles } from '@test/utils/never-settles';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { CUSTOM_ASSET, HYPERLIQUID_TOKEN } from '@/modules/assets/types';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

const { cancelActivityMock } = vi.hoisted(() => ({
  cancelActivityMock: vi.fn(),
}));

const runTaskResult = vi.fn();

/** Runs the submitted spec inline so assertions see the real `run` body. */
const submitTask = vi.fn(runSpecWith(runTaskResult));

vi.mock('@/modules/assets/api/use-asset-info-api', () => ({
  useAssetInfoApi: vi.fn().mockReturnValue({
    erc20details: vi.fn().mockResolvedValue({ taskId: 1 }),
  }),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelActivity: cancelActivityMock,
    cancelByType: vi.fn(() => vi.fn()),
    runTaskResult,
    statusOf: vi.fn(),
    submitTask,
  })),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn().mockReturnValue({
    notify: vi.fn(),
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications-store/index', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    removeMatching: vi.fn(),
  }),
}));

describe('useAssetRetrieval', () => {
  let assetInfoRetrieval: ReturnType<typeof useAssetInfoRetrieval>;
  let assetInfoCache: ReturnType<typeof useAssetInfoCache>;
  let api: ReturnType<typeof useAssetInfoApi>;

  beforeEach(() => {
    vi.clearAllMocks();
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

      runTaskResult.mockImplementation(async (task: () => Promise<unknown>) => {
        await task();
        return ok(tokenDetail);
      });

      const result = await assetInfoRetrieval.fetchTokenDetails(payload);

      expect(api.erc20details).toHaveBeenCalledWith(payload);

      expect(result).toEqual(tokenDetail);

      expect(useNotificationDispatcher().notify).not.toHaveBeenCalled();
    });

    it('should read the details off the activity outcome, so a deduped caller whose run never executes is not answered with an empty token', async () => {
      const tokenDetail: ERC20Token = {
        decimals: 6,
        name: 'USD Coin',
        symbol: 'USDC',
      };

      submitTask.mockResolvedValueOnce(ok(tokenDetail));

      const result = await assetInfoRetrieval.fetchTokenDetails(payload);

      expect(api.erc20details).not.toHaveBeenCalled();
      expect(result).toEqual(tokenDetail);
    });

    it('should handle failure', async () => {
      runTaskResult.mockImplementation(async (task: () => Promise<unknown>) => {
        await task();
        return err(TaskFailed({ message: 'failed' }));
      });

      const result = await assetInfoRetrieval.fetchTokenDetails(payload);

      expect(api.erc20details).toHaveBeenCalledWith(payload);

      expect(result).toEqual({});

      expect(useNotificationDispatcher().notify).toHaveBeenCalled();
    });

    it('should time out and cancel the task when the lookup never resolves, rather than leave the form fields disabled forever', async () => {
      vi.useFakeTimers();
      cancelActivityMock.mockClear();
      submitTask.mockReturnValueOnce(neverSettles());

      try {
        const resultPromise = assetInfoRetrieval.fetchTokenDetails(payload);

        await vi.advanceTimersByTimeAsync(15_000);

        await expect(resultPromise).resolves.toEqual({});
        expect(cancelActivityMock).toHaveBeenCalledWith(
          ActivityKind.ASSETS,
          ActivityPart.ERC20,
          payload.evmChain,
          payload.address,
        );
        expect(useNotificationDispatcher().notify).toHaveBeenCalled();
      }
      finally {
        vi.useRealTimers();
      }
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

  describe('getAssetContractInfo', () => {
    it('should extract a normalized Hyperliquid Core token address without an EVM location', () => {
      const mixedCaseAddress = HYPERLIQUID_TOKEN_ADDRESS.toUpperCase().replace('0X', '0x');
      vi.mocked(assetInfoCache.resolve).mockReturnValue({
        assetType: HYPERLIQUID_TOKEN,
        name: 'MAX',
        symbol: 'MAX',
      });

      expect(assetInfoRetrieval.getAssetContractInfo(`hyperc:${mixedCaseAddress}`)).toEqual({
        address: HYPERLIQUID_TOKEN_ADDRESS,
      });
    });
  });
});
