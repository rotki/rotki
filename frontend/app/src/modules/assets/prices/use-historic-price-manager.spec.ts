import type { HistoricalPrice, HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import { bigNumberify } from '@rotki/common';
import { mockTranslate } from '@test/i18n';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { useHistoricPrices } from './use-historic-price-manager';

const addHistoricalPrice = vi.fn<() => Promise<boolean>>(async () => true);
const editHistoricalPrice = vi.fn<() => Promise<boolean>>(async () => true);
const deleteHistoricalPrice = vi.fn<() => Promise<boolean>>(async () => true);
const fetchHistoricalPrices = vi.fn<() => Promise<HistoricalPrice[]>>(async () => []);
const resetHistoricalPricesData = vi.fn();
const notifyError = vi.fn();
const showErrorMessage = vi.fn();

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

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): Record<string, unknown> => ({ notifyError, showErrorMessage }),
}));

const wrappers: VueWrapper[] = [];

function price(overrides: Partial<HistoricalPrice> = {}): HistoricalPrice {
  return {
    fromAsset: 'ETH',
    price: bigNumberify(1500),
    timestamp: 1700000000,
    toAsset: 'USD',
    ...overrides,
  };
}

function formPayload(overrides: Partial<HistoricalPriceFormPayload> = {}): HistoricalPriceFormPayload {
  return {
    fromAsset: 'ETH',
    price: '1500',
    sourceType: PriceOracle.MANUAL,
    timestamp: 1700000000,
    toAsset: 'USD',
    ...overrides,
  };
}

function mountManager(
  filter?: { fromAsset?: string; toAsset?: string },
): ReturnType<typeof useHistoricPrices> {
  let captured: ReturnType<typeof useHistoricPrices> | undefined;
  let setupError: Error | undefined;
  const filterRef = ref<{ fromAsset?: string; toAsset?: string }>(filter ?? {});

  const Host = defineComponent({
    setup(): () => ReturnType<typeof h> {
      try {
        captured = useHistoricPrices(mockTranslate, filter ? filterRef : undefined);
      }
      catch (error) {
        setupError = error instanceof Error ? error : new Error(String(error));
      }
      return (): ReturnType<typeof h> => h('div');
    },
  });

  wrappers.push(mount(Host));
  if (setupError)
    throw setupError;
  return captured!;
}

describe('modules/assets/prices/useHistoricPrices', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchHistoricalPrices.mockResolvedValue([]);
    addHistoricalPrice.mockResolvedValue(true);
    editHistoricalPrice.mockResolvedValue(true);
    deleteHistoricalPrice.mockResolvedValue(true);
  });

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
  });

  describe('the initial load', () => {
    it('should fetch as soon as it mounts, without waiting for a caller', async () => {
      const rows = [price()];
      fetchHistoricalPrices.mockResolvedValue(rows);

      const { items } = mountManager();
      await flushPromises();

      expect(fetchHistoricalPrices).toHaveBeenCalledOnce();
      expect(get(items)).toEqual(rows);
    });

    it('should narrow the fetch to the filter it was given', async () => {
      mountManager({ fromAsset: 'ETH', toAsset: 'USD' });
      await flushPromises();

      expect(fetchHistoricalPrices).toHaveBeenCalledWith({ fromAsset: 'ETH', toAsset: 'USD' });
    });

    it('should ask for everything when no filter is given', async () => {
      mountManager();
      await flushPromises();

      expect(fetchHistoricalPrices).toHaveBeenCalledWith(undefined);
    });
  });

  describe('the loading flag', () => {
    it('should be raised for the duration of the fetch and lowered after it', async () => {
      let release: (rows: HistoricalPrice[]) => void = () => {};
      fetchHistoricalPrices.mockReturnValue(new Promise((resolve) => {
        release = resolve;
      }));

      const { loading } = mountManager();

      expect(get(loading)).toBe(true);
      release([]);
      await flushPromises();
      expect(get(loading)).toBe(false);
    });

    it('should be lowered again even when the fetch rejects', async () => {
      fetchHistoricalPrices.mockRejectedValue(new Error('offline'));

      const { loading } = mountManager();
      await flushPromises();

      expect(get(loading)).toBe(false);
    });
  });

  describe('a failed fetch', () => {
    it('should notify and leave the previous rows in place', async () => {
      const rows = [price()];
      fetchHistoricalPrices.mockResolvedValue(rows);
      const { items, refresh } = mountManager();
      await flushPromises();

      fetchHistoricalPrices.mockRejectedValue(new Error('offline'));
      await refresh();

      expect(notifyError).toHaveBeenCalledOnce();
      expect(get(items)).toEqual(rows);
    });
  });

  describe('refreshing', () => {
    it('should not touch the price cache for a plain refresh', async () => {
      const { refresh } = mountManager();
      await flushPromises();

      await refresh();

      expect(resetHistoricalPricesData).not.toHaveBeenCalled();
    });

    it('should invalidate the cache for the rows it just fetched when they changed', async () => {
      const rows = [price()];
      fetchHistoricalPrices.mockResolvedValue(rows);
      const { refresh } = mountManager();
      await flushPromises();

      await refresh({ modified: true });

      expect(resetHistoricalPricesData).toHaveBeenCalledWith(rows);
    });

    it('should also invalidate an entry that is no longer among the fetched rows', async () => {
      const removed = price({ fromAsset: 'BTC', timestamp: 1600000000 });
      const remaining = price();
      fetchHistoricalPrices.mockResolvedValue([remaining]);
      const { refresh } = mountManager();
      await flushPromises();

      await refresh({ additionalEntry: removed, modified: true });

      expect(resetHistoricalPricesData).toHaveBeenCalledWith([remaining, removed]);
    });

    it('should ignore an additional entry when nothing was modified', async () => {
      const { refresh } = mountManager();
      await flushPromises();

      await refresh({ additionalEntry: price() });

      expect(resetHistoricalPricesData).not.toHaveBeenCalled();
    });

    it('should refetch when the filter changes', async () => {
      const filter = ref({ fromAsset: 'ETH', toAsset: 'USD' });
      let captured: ReturnType<typeof useHistoricPrices> | undefined;
      const Host = defineComponent({
        setup(): () => ReturnType<typeof h> {
          captured = useHistoricPrices(mockTranslate, filter);
          return (): ReturnType<typeof h> => h('div');
        },
      });
      wrappers.push(mount(Host));
      await flushPromises();
      expect(captured).toBeDefined();

      set(filter, { fromAsset: 'BTC', toAsset: 'USD' });
      await flushPromises();

      expect(fetchHistoricalPrices).toHaveBeenLastCalledWith({ fromAsset: 'BTC', toAsset: 'USD' });
      expect(fetchHistoricalPrices).toHaveBeenCalledTimes(2);
    });
  });

  describe('saving', () => {
    it('should add when it is not an update', async () => {
      const { save } = mountManager();
      await flushPromises();

      const saved = await save(formPayload(), false);

      expect(addHistoricalPrice).toHaveBeenCalledWith(formPayload());
      expect(editHistoricalPrice).not.toHaveBeenCalled();
      expect(saved).toBe(true);
    });

    it('should edit when it is an update', async () => {
      const { save } = mountManager();
      await flushPromises();

      const saved = await save(formPayload(), true);

      expect(editHistoricalPrice).toHaveBeenCalledWith(formPayload());
      expect(addHistoricalPrice).not.toHaveBeenCalled();
      expect(saved).toBe(true);
    });

    it('should pass a refusal from the backend straight back to the caller', async () => {
      addHistoricalPrice.mockResolvedValue(false);
      const { save } = mountManager();
      await flushPromises();

      expect(await save(formPayload(), false)).toBe(false);
      expect(showErrorMessage).not.toHaveBeenCalled();
    });

    it('should report a failed add as a message rather than a notification', async () => {
      addHistoricalPrice.mockRejectedValue(new Error('rejected'));
      const { save } = mountManager();
      await flushPromises();

      const saved = await save(formPayload(), false);

      expect(saved).toBe(false);
      expect(showErrorMessage).toHaveBeenCalledWith(
        'price_management.add.error.title',
        'price_management.add.error.description::rejected',
      );
      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should name the edit, not the add, when an update fails', async () => {
      editHistoricalPrice.mockRejectedValue(new Error('rejected'));
      const { save } = mountManager();
      await flushPromises();

      await save(formPayload(), true);

      expect(showErrorMessage).toHaveBeenCalledWith(
        'price_management.edit.error.title',
        'price_management.edit.error.description::rejected',
      );
    });
  });

  describe('deleting', () => {
    it('should send the pair and timestamp as a manual price, without the price itself', async () => {
      const { deletePrice } = mountManager();
      await flushPromises();

      await deletePrice(price());

      expect(deleteHistoricalPrice).toHaveBeenCalledWith({
        fromAsset: 'ETH',
        sourceType: PriceOracle.MANUAL,
        timestamp: 1700000000,
        toAsset: 'USD',
      });
    });

    it('should invalidate the deleted entry, which the refetch can no longer report', async () => {
      const deleted = price();
      const { deletePrice } = mountManager();
      await flushPromises();
      fetchHistoricalPrices.mockResolvedValue([]);

      await deletePrice(deleted);

      expect(resetHistoricalPricesData).toHaveBeenCalledWith([deleted]);
    });

    it('should notify and not refetch when the delete fails', async () => {
      deleteHistoricalPrice.mockRejectedValue(new Error('locked'));
      const { deletePrice } = mountManager();
      await flushPromises();
      fetchHistoricalPrices.mockClear();

      await deletePrice(price());

      expect(notifyError).toHaveBeenCalledOnce();
      expect(fetchHistoricalPrices).not.toHaveBeenCalled();
      expect(resetHistoricalPricesData).not.toHaveBeenCalled();
    });
  });
});
