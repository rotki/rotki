import { bigNumberify } from '@rotki/common';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useFetchPrices } from '@/modules/assets/prices/use-fetch-prices';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { PriceOracle } from '@/modules/settings/types/price-oracle';

const runTaskMock = vi.fn();
const notifyError = vi.fn();

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

  it('should not notify when a batch is cancelled rather than failing', async () => {
    runTaskMock.mockResolvedValueOnce(err(Cancelled({ message: 'cancelled' })));

    await fetcher.fetchPrices({ ignoreCache: false, selectedAssets: ['DAI'] });

    expect(notifyError).not.toHaveBeenCalled();
  });
});
