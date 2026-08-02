import type { NativeActivitySpec, TaskOutcome } from '@/modules/task-center/use-native-task';
import { bigNumberify } from '@rotki/common';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { assetSetDigest, useFetchPrices } from '@/modules/assets/prices/use-fetch-prices';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { PriceOracle } from '@/modules/settings/types/price-oracle';

const runTaskMock = vi.fn();
const notifyError = vi.fn();
const submitTaskSpy = vi.fn();

vi.mock('@/modules/core/tasks/use-task-handler', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useTaskHandler: vi.fn(() => ({
      runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => {
        await taskFn();
        return runTaskMock(taskFn, ...rest);
      },
    })),
  };
});

vi.mock('@/modules/core/notifications/use-notifications', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useNotifications: vi.fn(() => ({ notifyError })),
}));

// The activity is what the task center renders, so the empty-run guard has to be asserted on
// submitTask itself: a run that queries nothing must not register one.
vi.mock('@/modules/task-center/use-native-task', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/task-center/use-native-task')>();

  type NativeTask = ReturnType<typeof actual.useNativeTask>;
  return {
    ...actual,
    useNativeTask: vi.fn((): NativeTask => {
      const real = actual.useNativeTask();
      return {
        ...real,
        // Generic in its own right: `Parameters`/`ReturnType` collapse `submitTask`'s type
        // parameter to its default, which no longer matches the generic signature.
        submitTask: async <T = void>(spec: NativeActivitySpec<T>): Promise<TaskOutcome<T>> => {
          submitTaskSpy(spec);
          return real.submitTask(spec);
        },
      };
    }),
  };
});

function priceResponse(assets: Record<string, [number, number]>): Record<string, unknown> {
  return {
    assets,
    oracles: { [PriceOracle.COINGECKO]: 0, [PriceOracle.MANUALCURRENT]: 1 },
    targetAsset: 'USD',
  };
}

function manyAssets(prefix: string, count: number): string[] {
  return Array.from({ length: count }, (_, index) => `${prefix}${index}`);
}

describe('useFetchPrices', () => {
  let store: ReturnType<typeof useBalancePricesStore>;
  let fetcher: ReturnType<typeof useFetchPrices>;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useBalancePricesStore();
    fetcher = useFetchPrices();
    vi.clearAllMocks();
  });

  it('should update the price store on a successful fetch', async () => {
    runTaskMock.mockResolvedValue(ok(priceResponse({ DAI: [1, 0] })));

    await fetcher.fetchPrices({ ignoreCache: false, selectedAssets: ['DAI'] });

    expect(usePriceApi().queryPrices).toHaveBeenCalledWith(['DAI'], 'USD', false);
    const { prices } = storeToRefs(store);
    expect(get(prices)).toMatchObject({ DAI: { isManualPrice: false, value: bigNumberify(1) } });
  });

  it('should fetch every batch and merge prices when there are more than 100 assets', async () => {
    runTaskMock
      .mockResolvedValueOnce(ok(priceResponse({ A0: [1, 0] })))
      .mockResolvedValueOnce(ok(priceResponse({ B0: [2, 0] })));

    await fetcher.fetchPrices({ ignoreCache: false, selectedAssets: [...manyAssets('A', 100), ...manyAssets('B', 50)] });

    expect(usePriceApi().queryPrices).toHaveBeenCalledTimes(2);
    const { prices } = storeToRefs(store);
    expect(get(prices)).toMatchObject({
      A0: { value: bigNumberify(1) },
      B0: { value: bigNumberify(2) },
    });
  });

  it('should notify and stop on the first failing batch', async () => {
    runTaskMock.mockResolvedValueOnce(err(TaskFailed({ cause: new Error('boom'), message: 'boom' })));

    await fetcher.fetchPrices({ ignoreCache: false, selectedAssets: [...manyAssets('A', 100), ...manyAssets('B', 50)] });

    // The first batch failed, so the second is never queried (short-circuit).
    expect(usePriceApi().queryPrices).toHaveBeenCalledTimes(1);
    expect(notifyError).toHaveBeenCalledOnce();
  });

  it('should not submit an activity when no assets are selected', async () => {
    await fetcher.fetchPrices({ ignoreCache: false, selectedAssets: [] });

    // With no assets there are no batches, so the activity would do nothing but still occupy the
    // task center - and a concurrent real refresh would inherit its "0 assets" subtitle.
    expect(submitTaskSpy).not.toHaveBeenCalled();
    expect(usePriceApi().queryPrices).not.toHaveBeenCalled();
  });

  it('should still submit an activity when assets are selected', async () => {
    runTaskMock.mockResolvedValue(ok(priceResponse({ DAI: [1, 0] })));

    await fetcher.fetchPrices({ ignoreCache: false, selectedAssets: ['DAI'] });

    expect(submitTaskSpy).toHaveBeenCalledOnce();
  });

  it('should label the activity with the real asset count', async () => {
    runTaskMock.mockResolvedValue(ok(priceResponse({ A0: [1, 0] })));

    await fetcher.fetchPrices({ ignoreCache: false, selectedAssets: manyAssets('A', 150) });

    // The count must come from the selection, not from anything the batching consumed: the old
    // splicing `chunkArray` emptied its input, so the task center claimed "Fetching prices for
    // 0 assets" while fetching 150.
    expect(submitTaskSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        subtitle: expect.objectContaining({ params: { count: 150 }, plural: 150 }),
      }),
    );
  });

  it('should not notify when a batch is cancelled rather than failing', async () => {
    runTaskMock.mockResolvedValueOnce(err(Cancelled({ message: 'cancelled' })));

    await fetcher.fetchPrices({ ignoreCache: false, selectedAssets: ['DAI'] });

    expect(notifyError).not.toHaveBeenCalled();
  });

  describe('activity identity', () => {
    /**
     * `submitTask` dedups by id. Under the old singleton `prices:latest`, opening the
     * manual-balance form while the background sweep was in flight handed the form the sweep's
     * promise: its own assets were never queried and the form showed no price.
     */
    it('should not dedup two concurrent fetches for different asset sets', async () => {
      runTaskMock.mockResolvedValue(ok(priceResponse({ DAI: [1, 0] })));

      await Promise.all([
        fetcher.fetchPrices({ ignoreCache: false, selectedAssets: ['DAI'] }),
        fetcher.fetchPrices({ ignoreCache: false, selectedAssets: ['ETH'] }),
      ]);

      expect(usePriceApi().queryPrices).toHaveBeenCalledTimes(2);
    });

    it('should still dedup two concurrent fetches for the same asset set', async () => {
      runTaskMock.mockResolvedValue(ok(priceResponse({ DAI: [1, 0] })));

      await Promise.all([
        fetcher.fetchPrices({ ignoreCache: false, selectedAssets: ['DAI', 'ETH'] }),
        // Same set, different order — the digest sorts, so this is the same identity.
        fetcher.fetchPrices({ ignoreCache: false, selectedAssets: ['ETH', 'DAI'] }),
      ]);

      expect(usePriceApi().queryPrices).toHaveBeenCalledOnce();
    });

    it('should not let a cache read answer a force refresh of the same assets', async () => {
      runTaskMock.mockResolvedValue(ok(priceResponse({ DAI: [1, 0] })));

      await Promise.all([
        fetcher.fetchPrices({ ignoreCache: false, selectedAssets: ['DAI'] }),
        fetcher.fetchPrices({ ignoreCache: true, selectedAssets: ['DAI'] }),
      ]);

      expect(usePriceApi().queryPrices).toHaveBeenCalledTimes(2);
    });
  });
});

describe('assetSetDigest', () => {
  it('should be independent of member order', () => {
    expect(assetSetDigest(['ETH', 'DAI', 'BTC'])).toBe(assetSetDigest(['BTC', 'ETH', 'DAI']));
  });

  it('should differ for different sets', () => {
    expect(assetSetDigest(['DAI'])).not.toBe(assetSetDigest(['ETH']));
    expect(assetSetDigest(['DAI'])).not.toBe(assetSetDigest(['DAI', 'ETH']));
  });

  it('should not collide on a shifted separator', () => {
    // Without folding the separator, ['ab','c'] and ['a','bc'] hash the same byte stream.
    expect(assetSetDigest(['ab', 'c'])).not.toBe(assetSetDigest(['a', 'bc']));
  });
});
