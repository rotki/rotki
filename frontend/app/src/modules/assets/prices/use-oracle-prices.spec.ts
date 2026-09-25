import { bigNumberify } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import flushPromises from 'flush-promises';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RequestFailed } from '@/modules/core/api/request-result';
import '@test/i18n';

const mockFetchOraclePrices = vi.fn();
const mockDeleteHistoricalPrice = vi.fn();
const mockResetHistoricalPricesData = vi.fn();

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    deleteHistoricalPrice: mockDeleteHistoricalPrice,
    fetchOraclePrices: mockFetchOraclePrices,
  }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: vi.fn().mockReturnValue({
    resetHistoricalPricesData: mockResetHistoricalPricesData,
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn().mockReturnValue({
    notifyError: vi.fn(),
  }),
}));

const { useOraclePrices } = await import('@/modules/assets/prices/use-oracle-prices');

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
    mockResetHistoricalPricesData.mockClear();
  });

  it('should call fetchOraclePrices with provided payload', async () => {
    const { result } = withSetup(() => useOraclePrices());

    const collection = await result.fetchData({ fromAsset: 'ETH', limit: 100, offset: 0 });

    expect(mockFetchOraclePrices).toHaveBeenCalledWith({
      fromAsset: 'ETH',
      limit: 100,
      offset: 0,
    });
    expect(collection).toStrictEqual(ok(emptyCollection()));
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

    expect(collection).toStrictEqual(ok({ data: entries, found: 1, limit: -1, total: 1 }));
  });

  it('should carry the failure instead of an empty collection when fetch fails', async () => {
    const failure = new Error('Network error');
    mockFetchOraclePrices.mockRejectedValueOnce(failure);

    const { result } = withSetup(() => useOraclePrices());

    const collection = await result.fetchData({ limit: 100, offset: 0 });

    expect(collection).toStrictEqual(err(RequestFailed({ cause: failure, message: 'Network error', path: undefined, status: undefined })));
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
    expect(mockResetHistoricalPricesData).toHaveBeenCalledWith([
      { fromAsset: 'ETH', timestamp: 1700000000 },
    ]);
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
    expect(mockResetHistoricalPricesData).not.toHaveBeenCalled();
  });
});
