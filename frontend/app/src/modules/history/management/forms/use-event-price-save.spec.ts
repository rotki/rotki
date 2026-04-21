import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const mockAddHistoricalPrice = vi.fn().mockResolvedValue(true);
const mockResetHistoricalPricesData = vi.fn();

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    addHistoricalPrice: mockAddHistoricalPrice,
  }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: vi.fn().mockReturnValue({
    resetHistoricalPricesData: mockResetHistoricalPricesData,
  }),
}));

const { useEventPriceSave } = await import('@/modules/history/management/forms/use-event-price-save');

describe('useEventPriceSave', () => {
  beforeEach(() => {
    mockAddHistoricalPrice.mockClear().mockResolvedValue(true);
    mockResetHistoricalPricesData.mockClear();
  });

  it('should save a price with manual source type', async () => {
    const { savePrice } = useEventPriceSave();

    await savePrice('ETH', 'USD', '2500', 1700000000000);

    expect(mockAddHistoricalPrice).toHaveBeenCalledOnce();
    expect(mockAddHistoricalPrice).toHaveBeenCalledWith({
      fromAsset: 'ETH',
      price: '2500',
      sourceType: 'manual',
      timestamp: 1700000000,
      toAsset: 'USD',
    });
  });

  it('should reset the historic price cache after saving', async () => {
    const { savePrice } = useEventPriceSave();

    await savePrice('BTC', 'EUR', '45000', 1700100000000);

    expect(mockResetHistoricalPricesData).toHaveBeenCalledOnce();
    expect(mockResetHistoricalPricesData).toHaveBeenCalledWith([{
      fromAsset: 'BTC',
      price: '45000',
      sourceType: 'manual',
      timestamp: 1700100000,
      toAsset: 'EUR',
    }]);
  });

  it('should convert millisecond timestamps to seconds', async () => {
    const { savePrice } = useEventPriceSave();

    await savePrice('ETH', 'USD', '100', 1700000000000);

    const payload = mockAddHistoricalPrice.mock.calls[0][0];
    expect(payload.timestamp).toBe(1700000000);
  });

  it('should propagate errors from the API', async () => {
    mockAddHistoricalPrice.mockRejectedValueOnce(new Error('API error'));

    const { savePrice } = useEventPriceSave();

    await expect(savePrice('ETH', 'USD', '100', 1700000000000)).rejects.toThrow('API error');
    expect(mockResetHistoricalPricesData).not.toHaveBeenCalled();
  });
});
