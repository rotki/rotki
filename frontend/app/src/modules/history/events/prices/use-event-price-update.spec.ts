import type { OraclePriceEntry } from '@/modules/assets/prices/price-types';
import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const mockAddHistoricalPrice = vi.fn().mockResolvedValue(true);
const mockEditHistoricalPrice = vi.fn().mockResolvedValue(true);
const mockFetchOraclePrices = vi.fn();
const mockResetHistoricalPricesData = vi.fn();

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    addHistoricalPrice: mockAddHistoricalPrice,
    editHistoricalPrice: mockEditHistoricalPrice,
    fetchOraclePrices: mockFetchOraclePrices,
  }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: vi.fn().mockReturnValue({
    resetHistoricalPricesData: mockResetHistoricalPricesData,
  }),
}));

const { useEventPriceUpdate } = await import('@/modules/history/events/prices/use-event-price-update');

function makeEntry(sourceType: string): OraclePriceEntry {
  return {
    fromAsset: 'ETH',
    price: bigNumberify('2500'),
    sourceType,
    timestamp: 1700000000,
    toAsset: 'USD',
  };
}

describe('useEventPriceUpdate', () => {
  beforeEach(() => {
    mockAddHistoricalPrice.mockClear().mockResolvedValue(true);
    mockEditHistoricalPrice.mockClear().mockResolvedValue(true);
    mockFetchOraclePrices.mockReset();
    mockResetHistoricalPricesData.mockClear();
  });

  describe('fetchExistingEntry', () => {
    it('should query oracle prices with exact timestamp in seconds', async () => {
      mockFetchOraclePrices.mockResolvedValue({ data: [], found: 0, limit: 1, total: 0 });
      const { fetchExistingEntry } = useEventPriceUpdate();

      await fetchExistingEntry('ETH', 'USD', 1700000000000);

      expect(mockFetchOraclePrices).toHaveBeenCalledWith({
        fromAsset: 'ETH',
        fromTimestamp: 1700000000,
        limit: 1,
        offset: 0,
        toAsset: 'USD',
        toTimestamp: 1700000000,
      });
    });

    it('should return the first entry when one exists', async () => {
      const entry = makeEntry('coingecko');
      mockFetchOraclePrices.mockResolvedValue({ data: [entry], found: 1, limit: 1, total: 1 });
      const { fetchExistingEntry } = useEventPriceUpdate();

      const result = await fetchExistingEntry('ETH', 'USD', 1700000000000);

      expect(result).toEqual(entry);
    });

    it('should return undefined when no entry exists', async () => {
      mockFetchOraclePrices.mockResolvedValue({ data: [], found: 0, limit: 1, total: 0 });
      const { fetchExistingEntry } = useEventPriceUpdate();

      const result = await fetchExistingEntry('ETH', 'USD', 1700000000000);

      expect(result).toBeUndefined();
    });
  });

  describe('updatePrice', () => {
    it('should PATCH with existing source type for oracle mode with non-manual existing entry', async () => {
      const { updatePrice } = useEventPriceUpdate();

      await updatePrice({
        existingEntry: makeEntry('coingecko'),
        fromAsset: 'ETH',
        mode: 'oracle',
        price: '2600',
        timestampMs: 1700000000000,
        toAsset: 'USD',
      });

      expect(mockEditHistoricalPrice).toHaveBeenCalledWith({
        fromAsset: 'ETH',
        price: '2600',
        sourceType: 'coingecko',
        timestamp: 1700000000,
        toAsset: 'USD',
      });
      expect(mockAddHistoricalPrice).not.toHaveBeenCalled();
    });

    it('should PATCH with manual source type for oracle mode with existing manual entry', async () => {
      const { updatePrice } = useEventPriceUpdate();

      await updatePrice({
        existingEntry: makeEntry('manual'),
        fromAsset: 'ETH',
        mode: 'oracle',
        price: '2600',
        timestampMs: 1700000000000,
        toAsset: 'USD',
      });

      expect(mockEditHistoricalPrice).toHaveBeenCalledWith(expect.objectContaining({
        sourceType: 'manual',
      }));
    });

    it('should PATCH for manual mode when existing entry is manual (same tuple)', async () => {
      const { updatePrice } = useEventPriceUpdate();

      await updatePrice({
        existingEntry: makeEntry('manual'),
        fromAsset: 'ETH',
        mode: 'manual',
        price: '2600',
        timestampMs: 1700000000000,
        toAsset: 'USD',
      });

      expect(mockEditHistoricalPrice).toHaveBeenCalledWith(expect.objectContaining({
        sourceType: 'manual',
      }));
      expect(mockAddHistoricalPrice).not.toHaveBeenCalled();
    });

    it('should PUT for manual mode when existing entry is a non-manual oracle', async () => {
      const { updatePrice } = useEventPriceUpdate();

      await updatePrice({
        existingEntry: makeEntry('coingecko'),
        fromAsset: 'ETH',
        mode: 'manual',
        price: '2600',
        timestampMs: 1700000000000,
        toAsset: 'USD',
      });

      expect(mockAddHistoricalPrice).toHaveBeenCalledWith(expect.objectContaining({
        sourceType: 'manual',
      }));
      expect(mockEditHistoricalPrice).not.toHaveBeenCalled();
    });

    it('should PUT with manual source type for manual mode with no existing entry', async () => {
      const { updatePrice } = useEventPriceUpdate();

      await updatePrice({
        fromAsset: 'ETH',
        mode: 'manual',
        price: '2600',
        timestampMs: 1700000000000,
        toAsset: 'USD',
      });

      expect(mockAddHistoricalPrice).toHaveBeenCalledWith({
        fromAsset: 'ETH',
        price: '2600',
        sourceType: 'manual',
        timestamp: 1700000000,
        toAsset: 'USD',
      });
      expect(mockEditHistoricalPrice).not.toHaveBeenCalled();
    });

    it('should defensively PUT as manual for oracle mode with no existing entry', async () => {
      const { updatePrice } = useEventPriceUpdate();

      await updatePrice({
        fromAsset: 'ETH',
        mode: 'oracle',
        price: '2600',
        timestampMs: 1700000000000,
        toAsset: 'USD',
      });

      expect(mockAddHistoricalPrice).toHaveBeenCalledWith(expect.objectContaining({
        sourceType: 'manual',
      }));
      expect(mockEditHistoricalPrice).not.toHaveBeenCalled();
    });

    it('should reset the historic price cache after updating', async () => {
      const { updatePrice } = useEventPriceUpdate();

      await updatePrice({
        fromAsset: 'ETH',
        mode: 'manual',
        price: '2600',
        timestampMs: 1700000000000,
        toAsset: 'USD',
      });

      expect(mockResetHistoricalPricesData).toHaveBeenCalledWith([{
        fromAsset: 'ETH',
        price: '2600',
        sourceType: 'manual',
        timestamp: 1700000000,
        toAsset: 'USD',
      }]);
    });

    it('should propagate errors from the API', async () => {
      mockAddHistoricalPrice.mockRejectedValueOnce(new Error('API error'));
      const { updatePrice } = useEventPriceUpdate();

      await expect(updatePrice({
        fromAsset: 'ETH',
        mode: 'manual',
        price: '2600',
        timestampMs: 1700000000000,
        toAsset: 'USD',
      })).rejects.toThrow('API error');

      expect(mockResetHistoricalPricesData).not.toHaveBeenCalled();
    });
  });
});
