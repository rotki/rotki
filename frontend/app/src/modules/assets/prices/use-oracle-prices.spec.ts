import { bigNumberify } from '@rotki/common';
import { mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const mockFetchOraclePrices = vi.fn();
const mockDeleteHistoricalPrice = vi.fn();

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    deleteHistoricalPrice: mockDeleteHistoricalPrice,
    fetchOraclePrices: mockFetchOraclePrices,
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn().mockReturnValue({
    notifyError: vi.fn(),
  }),
}));

const { useOraclePrices } = await import('@/modules/assets/prices/use-oracle-prices');

function withSetup<T>(composable: () => T): { result: T; wrapper: ReturnType<typeof mount> } {
  let result!: T;
  const wrapper = mount({
    setup() {
      result = composable();
      return {};
    },
    template: '<div />',
  });
  return { result, wrapper };
}

function emptyCollection(): {
  data: never[];
  found: number;
  limit: number;
  total: number;
} {
  return { data: [], found: 0, limit: -1, total: 0 };
}

describe('useOraclePrices', () => {
  beforeEach(() => {
    mockFetchOraclePrices.mockClear().mockResolvedValue(emptyCollection());
    mockDeleteHistoricalPrice.mockClear().mockResolvedValue(true);
  });

  it('should call fetchOraclePrices with provided payload', async () => {
    const { result } = withSetup(() => useOraclePrices());

    const collection = await result.fetchData({ fromAsset: 'ETH', limit: 100, offset: 0 });

    expect(mockFetchOraclePrices).toHaveBeenCalledWith({
      fromAsset: 'ETH',
      limit: 100,
      offset: 0,
    });
    expect(collection.data).toEqual([]);
  });

  it('should return mapped entries from the API response', async () => {
    const entries = [
      {
        fromAsset: 'ETH',
        price: bigNumberify('2500'),
        sourceType: 'coingecko',
        timestamp: 1700000000,
        toAsset: 'USD',
      },
    ];
    mockFetchOraclePrices.mockResolvedValueOnce({
      data: entries,
      found: 1,
      limit: -1,
      total: 1,
    });

    const { result } = withSetup(() => useOraclePrices());

    const collection = await result.fetchData({ limit: 100, offset: 0 });

    expect(collection.data).toHaveLength(1);
    expect(collection.data[0].fromAsset).toBe('ETH');
    expect(collection.data[0].sourceType).toBe('coingecko');
    expect(collection.found).toBe(1);
  });

  it('should return empty collection when fetch fails', async () => {
    mockFetchOraclePrices.mockRejectedValueOnce(new Error('Network error'));

    const { result } = withSetup(() => useOraclePrices());

    const collection = await result.fetchData({ limit: 100, offset: 0 });

    expect(collection.data).toEqual([]);
    expect(collection.found).toBe(0);
  });

  it('should delete a price and return true on success', async () => {
    const { result } = withSetup(() => useOraclePrices());

    await flushPromises();

    const success = await result.deletePrice({
      fromAsset: 'ETH',
      price: bigNumberify('2500'),
      sourceType: 'coingecko',
      timestamp: 1700000000,
      toAsset: 'USD',
    });

    expect(mockDeleteHistoricalPrice).toHaveBeenCalledOnce();
    expect(mockDeleteHistoricalPrice).toHaveBeenCalledWith({
      fromAsset: 'ETH',
      sourceType: 'coingecko',
      timestamp: 1700000000,
      toAsset: 'USD',
    });
    expect(success).toBe(true);
  });

  it('should return false when delete fails', async () => {
    mockDeleteHistoricalPrice.mockRejectedValueOnce(new Error('Delete failed'));

    const { result } = withSetup(() => useOraclePrices());

    const success = await result.deletePrice({
      fromAsset: 'ETH',
      price: bigNumberify('2500'),
      sourceType: 'coingecko',
      timestamp: 1700000000,
      toAsset: 'USD',
    });

    expect(success).toBe(false);
  });
});
