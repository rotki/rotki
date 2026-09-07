import type { HistoricalPrice } from '@/modules/assets/prices/price-types';
import type { EditableMissingPrice, MissingPrice } from '@/modules/reports/report-types';
import { bigNumberify } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type Ref, ref } from 'vue';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { useEditableMissingPrices } from './use-editable-missing-prices';

const {
  addHistoricalPrice,
  deleteHistoricalPrice,
  editHistoricalPrice,
  fetchHistoricalPrices,
  getHistoricPrice,
  resetHistoricalPricesData,
} = vi.hoisted(() => ({
  addHistoricalPrice: vi.fn(async () => Promise.resolve(true)),
  deleteHistoricalPrice: vi.fn(async () => Promise.resolve(true)),
  editHistoricalPrice: vi.fn(async () => Promise.resolve(true)),
  fetchHistoricalPrices: vi.fn(),
  getHistoricPrice: vi.fn(),
  resetHistoricalPricesData: vi.fn(),
}));

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: (): Record<string, unknown> => ({
    addHistoricalPrice,
    deleteHistoricalPrice,
    editHistoricalPrice,
    fetchHistoricalPrices,
  }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): Record<string, unknown> => ({ resetHistoricalPricesData }),
}));

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: (): Record<string, unknown> => ({ getHistoricPrice }),
}));

const ETH_AT_NOON: MissingPrice = { fromAsset: 'ETH', time: 1_700_000_000, toAsset: 'USD' };

function keyOf(item: MissingPrice): string {
  return item.fromAsset + item.toAsset + item.time;
}

function savedPrice(price: string, overrides: Partial<HistoricalPrice> = {}): HistoricalPrice {
  return {
    fromAsset: 'ETH',
    price: bigNumberify(price),
    timestamp: 1_700_000_000,
    toAsset: 'USD',
    ...overrides,
  };
}

let items: Ref<MissingPrice[]>;
let onPriceUpdated: ReturnType<typeof vi.fn<(item: EditableMissingPrice) => void>>;
let scope: ReturnType<typeof effectScope>;

function table(): ReturnType<typeof useEditableMissingPrices> {
  scope = effectScope();
  return scope.run(() => useEditableMissingPrices({ items, keyOf, onPriceUpdated }))!;
}

/** The row as the table renders it, after the saved prices have been read. */
async function firstRow(): Promise<{ api: ReturnType<typeof useEditableMissingPrices>; row: EditableMissingPrice }> {
  const api = table();
  await api.getHistoricalPrices();
  return { api, row: get(api.formattedItems)[0] };
}

describe('modules/assets/prices/useEditableMissingPrices', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    items = ref<MissingPrice[]>([ETH_AT_NOON]);
    onPriceUpdated = vi.fn<(item: EditableMissingPrice) => void>();
    fetchHistoricalPrices.mockResolvedValue([]);
    getHistoricPrice.mockResolvedValue(bigNumberify(0));
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the rows', () => {
    it('should offer an empty price for a price nothing knows', async () => {
      const { row } = await firstRow();

      expect(row).toMatchObject({ price: '', saved: false, useRefreshedHistoricalPrice: false });
    });

    it('should show a price already saved manually', async () => {
      fetchHistoricalPrices.mockResolvedValue([savedPrice('1500')]);

      const { row } = await firstRow();

      expect(row).toMatchObject({ price: '1500', saved: true, useRefreshedHistoricalPrice: false });
    });

    it('should not match a saved price for another asset or another moment', async () => {
      fetchHistoricalPrices.mockResolvedValue([
        savedPrice('1500', { fromAsset: 'BTC' }),
        savedPrice('1600', { toAsset: 'EUR' }),
        savedPrice('1700', { timestamp: 1 }),
      ]);

      const { row } = await firstRow();

      expect(row.price).toBe('');
      expect(row.saved).toBe(false);
    });

    it('should show a rate fetched from an oracle, marked as not the user\'s own', async () => {
      getHistoricPrice.mockResolvedValue(bigNumberify(1234));

      const { api } = await firstRow();
      await api.refreshHistoricalPrice(get(api.formattedItems)[0]);

      expect(get(api.formattedItems)[0]).toMatchObject({ price: '1234', useRefreshedHistoricalPrice: true });
    });

    it('should prefer a manually saved price over a fetched one', async () => {
      getHistoricPrice.mockResolvedValue(bigNumberify(1234));
      fetchHistoricalPrices.mockResolvedValue([savedPrice('1500')]);

      const { api } = await firstRow();
      await api.refreshHistoricalPrice(get(api.formattedItems)[0]);

      expect(get(api.formattedItems)[0]).toMatchObject({ price: '1500', useRefreshedHistoricalPrice: false });
    });
  });

  describe('writing a price', () => {
    it('should add a price the row did not have', async () => {
      const { api, row } = await firstRow();
      await api.updatePrice({ ...row, price: '1500' });

      expect(addHistoricalPrice).toHaveBeenCalledWith(expect.objectContaining({
        fromAsset: 'ETH',
        price: '1500',
        sourceType: PriceOracle.MANUAL,
        timestamp: 1_700_000_000,
        toAsset: 'USD',
      }));
      expect(editHistoricalPrice).not.toHaveBeenCalled();
      expect(deleteHistoricalPrice).not.toHaveBeenCalled();
    });

    it('should edit a price that was already saved', async () => {
      fetchHistoricalPrices.mockResolvedValue([savedPrice('1500')]);

      const { api, row } = await firstRow();
      await api.updatePrice({ ...row, price: '1600' });

      expect(editHistoricalPrice).toHaveBeenCalledWith(expect.objectContaining({ price: '1600' }));
      expect(addHistoricalPrice).not.toHaveBeenCalled();
    });

    it('should delete a saved price the user cleared', async () => {
      fetchHistoricalPrices.mockResolvedValue([savedPrice('1500')]);

      const { api, row } = await firstRow();
      await api.updatePrice({ ...row, price: '' });

      expect(deleteHistoricalPrice).toHaveBeenCalledWith(expect.objectContaining({ fromAsset: 'ETH' }));
      expect(addHistoricalPrice).not.toHaveBeenCalled();
      expect(editHistoricalPrice).not.toHaveBeenCalled();
    });

    it('should write nothing for an empty price that was never saved', async () => {
      const { api, row } = await firstRow();
      await api.updatePrice({ ...row, price: '' });

      expect(addHistoricalPrice).not.toHaveBeenCalled();
      expect(editHistoricalPrice).not.toHaveBeenCalled();
      expect(deleteHistoricalPrice).not.toHaveBeenCalled();
    });

    it('should write nothing for a rate that came from an oracle', async () => {
      const { api, row } = await firstRow();
      await api.updatePrice({ ...row, price: '1234', useRefreshedHistoricalPrice: true });

      expect(addHistoricalPrice).not.toHaveBeenCalled();
      expect(resetHistoricalPricesData).not.toHaveBeenCalled();
      expect(onPriceUpdated).not.toHaveBeenCalled();
    });

    it('should invalidate the cache and re-read the prices after writing', async () => {
      const { api, row } = await firstRow();
      fetchHistoricalPrices.mockClear();
      await api.updatePrice({ ...row, price: '1500' });

      expect(resetHistoricalPricesData).toHaveBeenCalledWith([expect.objectContaining({ fromAsset: 'ETH' })]);
      expect(fetchHistoricalPrices).toHaveBeenCalledOnce();
    });

    it('should tell the caller which row was written', async () => {
      const { api, row } = await firstRow();
      await api.updatePrice({ ...row, price: '1500' });

      expect(onPriceUpdated).toHaveBeenCalledWith(expect.objectContaining({ fromAsset: 'ETH', time: 1_700_000_000 }));
    });

    it('should write a price for a caller that wants no notification', async () => {
      scope = effectScope();
      const api = scope.run(() => useEditableMissingPrices({ items, keyOf }))!;
      await api.getHistoricalPrices();

      await api.updatePrice({ ...get(api.formattedItems)[0], price: '1500' });

      expect(addHistoricalPrice).toHaveBeenCalledOnce();
    });
  });

  describe('when writing fails', () => {
    it('should report the message on the row it belongs to', async () => {
      addHistoricalPrice.mockRejectedValue(new Error('backend is down'));

      const { api, row } = await firstRow();
      await api.updatePrice({ ...row, price: '1500' });

      expect(get(api.errorMessages)[keyOf(ETH_AT_NOON)]).toBe('backend is down');
    });

    it('should unwrap a validation error down to the price field', async () => {
      addHistoricalPrice.mockRejectedValue(
        new ApiValidationError(JSON.stringify({ price: ['must be a number'] })),
      );

      const { api, row } = await firstRow();
      await api.updatePrice({ ...row, price: 'abc' });

      expect(get(api.errorMessages)[keyOf(ETH_AT_NOON)]).toBe('must be a number');
    });

    it('should fall back to the raw message when the validation error names another field', async () => {
      const raw = JSON.stringify({ timestamp: ['out of range'] });
      addHistoricalPrice.mockRejectedValue(new ApiValidationError(raw));

      const { api, row } = await firstRow();
      await api.updatePrice({ ...row, price: '1500' });

      expect(get(api.errorMessages)[keyOf(ETH_AT_NOON)]).toBe(raw);
    });

    it('should still invalidate the cache and re-read the prices', async () => {
      addHistoricalPrice.mockRejectedValue(new Error('backend is down'));

      const { api, row } = await firstRow();
      fetchHistoricalPrices.mockClear();
      await api.updatePrice({ ...row, price: '1500' });

      expect(resetHistoricalPricesData).toHaveBeenCalledOnce();
      expect(fetchHistoricalPrices).toHaveBeenCalledOnce();
    });
  });

  describe('clearing a failure', () => {
    it('should forget the failure on the row being corrected, and only that one', async () => {
      const later: MissingPrice = { ...ETH_AT_NOON, time: 1_700_000_001 };
      set(items, [ETH_AT_NOON, later]);
      addHistoricalPrice.mockRejectedValue(new Error('backend is down'));

      const { api } = await firstRow();
      await api.updatePrice({ ...get(api.formattedItems)[0], price: '1500' });
      await api.updatePrice({ ...get(api.formattedItems)[1], price: '1500' });

      api.clearError(ETH_AT_NOON);

      expect(get(api.errorMessages)[keyOf(ETH_AT_NOON)]).toBeUndefined();
      expect(get(api.errorMessages)[keyOf(later)]).toBe('backend is down');
    });

    it('should leave the failures alone for a row that has none', async () => {
      addHistoricalPrice.mockRejectedValue(new Error('backend is down'));

      const { api, row } = await firstRow();
      await api.updatePrice({ ...row, price: '1500' });

      api.clearError({ ...ETH_AT_NOON, time: 999 });

      expect(get(api.errorMessages)[keyOf(ETH_AT_NOON)]).toBe('backend is down');
    });
  });

  describe('fetching a rate from the oracles', () => {
    it('should mark itself busy only while the lookup runs', async () => {
      const { api, row } = await firstRow();

      const pending = api.refreshHistoricalPrice(row);
      expect(get(api.refreshing)).toBe(true);

      await pending;
      expect(get(api.refreshing)).toBe(false);
    });

    it('should ask for the row\'s own asset pair and moment', async () => {
      const { api, row } = await firstRow();
      await api.refreshHistoricalPrice(row);

      expect(getHistoricPrice).toHaveBeenCalledWith({
        fromAsset: 'ETH',
        timestamp: 1_700_000_000,
        toAsset: 'USD',
      });
    });

    it.each([
      ['the oracles have no rate', undefined],
      ['the rate comes back as zero', bigNumberify(0)],
    ])('should report a lookup that found nothing when %s', async (_case, rate) => {
      getHistoricPrice.mockResolvedValue(rate);

      const { api, row } = await firstRow();
      await api.refreshHistoricalPrice(row);

      expect(get(api.errorMessages)[keyOf(ETH_AT_NOON)])
        .toBe('profit_loss_report.actionable.missing_prices.price_not_found');
      expect(get(api.formattedItems)[0].price).toBe('');
    });
  });

  describe('keying rows', () => {
    it('should keep two rows of the same asset at different moments apart', async () => {
      const later: MissingPrice = { ...ETH_AT_NOON, time: 1_700_000_001 };
      set(items, [ETH_AT_NOON, later]);
      addHistoricalPrice.mockRejectedValue(new Error('backend is down'));

      const { api } = await firstRow();
      await api.updatePrice({ ...get(api.formattedItems)[1], price: '1500' });

      expect(get(api.errorMessages)[keyOf(later)]).toBe('backend is down');
      expect(get(api.errorMessages)[keyOf(ETH_AT_NOON)]).toBeUndefined();
    });
  });
});
