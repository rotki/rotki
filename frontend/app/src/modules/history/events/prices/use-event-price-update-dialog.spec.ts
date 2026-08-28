import type { OraclePriceEntry } from '@/modules/assets/prices/price-types';
import type { EventPriceUpdatePayload } from '@/modules/history/events/prices/use-event-price-update-trigger';
import { bigNumberify } from '@rotki/common';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, ref, type Ref } from 'vue';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { useEventPriceUpdateDialog } from './use-event-price-update-dialog';

const { currencySymbol, fetchExistingEntry, notifyError, notifyInfo, updatePrice } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    currencySymbol: ref<string>('USD'),
    fetchExistingEntry: vi.fn(),
    notifyError: vi.fn(),
    notifyInfo: vi.fn(),
    updatePrice: vi.fn(),
  };
});

vi.mock('@/modules/history/events/prices/use-event-price-update', () => ({
  useEventPriceUpdate: (): Record<string, unknown> => ({ fetchExistingEntry, updatePrice }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): Record<string, unknown> => ({ notifyError, notifyInfo }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): typeof currencySymbol => currencySymbol,
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  getDefaultLogLevel: vi.fn(() => 'debug'),
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
  setLevel: vi.fn(),
}));

let scope: ReturnType<typeof effectScope>;

function oracleEntry(overrides: Partial<OraclePriceEntry> = {}): OraclePriceEntry {
  return {
    fromAsset: 'ETH',
    price: bigNumberify(1500),
    sourceType: 'cryptocompare',
    timestamp: 1700000000,
    toAsset: 'USD',
    ...overrides,
  };
}

function payload(): EventPriceUpdatePayload {
  return { asset: 'ETH', timestamp: 1700000000 };
}

async function dialog(
  model: Ref<EventPriceUpdatePayload | undefined>,
): Promise<ReturnType<typeof useEventPriceUpdateDialog>> {
  scope = effectScope();
  const api = scope.run(() => useEventPriceUpdateDialog(model))!;
  await flushPromises();
  return api;
}

describe('modules/history/events/prices/useEventPriceUpdateDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchExistingEntry.mockResolvedValue(undefined);
    updatePrice.mockResolvedValue(undefined);
    set(currencySymbol, 'USD');
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('opening on an event', () => {
    it('should read whatever price is already recorded', async () => {
      fetchExistingEntry.mockResolvedValue(oracleEntry());

      const { existingEntry, modelPrice } = await dialog(ref(payload()));

      expect(fetchExistingEntry).toHaveBeenCalledExactlyOnceWith('ETH', 'USD', 1700000000);
      expect(get(existingEntry)?.sourceType).toBe('cryptocompare');
      expect(get(modelPrice)).toBe('1500');
    });

    it('should default to overwriting the oracle when the recorded price came from one', async () => {
      fetchExistingEntry.mockResolvedValue(oracleEntry());

      const { modelMode, showModeChoice } = await dialog(ref(payload()));

      expect(get(modelMode)).toBe('oracle');
      expect(get(showModeChoice)).toBe(true);
    });

    it('should default to manual, offering no choice, when the recorded price was already manual', async () => {
      fetchExistingEntry.mockResolvedValue(oracleEntry({ sourceType: PriceOracle.MANUAL }));

      const { modelMode, showModeChoice } = await dialog(ref(payload()));

      expect(get(modelMode)).toBe('manual');
      expect(get(showModeChoice)).toBe(false);
    });

    it('should start empty and manual when nothing is recorded yet', async () => {
      const { modelMode, modelPrice, showModeChoice } = await dialog(ref(payload()));

      expect(get(modelPrice)).toBe('');
      expect(get(modelMode)).toBe('manual');
      expect(get(showModeChoice)).toBe(false);
    });

    it('should notify and stay usable when the read fails', async () => {
      fetchExistingEntry.mockRejectedValue(new Error('offline'));

      const { existingEntry, loading } = await dialog(ref(payload()));

      expect(notifyError).toHaveBeenCalledOnce();
      expect(get(existingEntry)).toBeUndefined();
      expect(get(loading)).toBe(false);
    });

    it('should read nothing while no event is being priced', async () => {
      const { open } = await dialog(ref(undefined));

      expect(fetchExistingEntry).not.toHaveBeenCalled();
      expect(get(open)).toBe(false);
    });
  });

  describe('the price field', () => {
    it.each([
      ['0', false],
      ['-1', false],
      ['abc', false],
      ['0.5', true],
      ['1500', true],
    ])('should treat %s as valid=%s', async (value, valid) => {
      const { modelPrice, priceValid } = await dialog(ref(payload()));

      set(modelPrice, value);

      expect(get(priceValid)).toBe(valid);
    });

    it('should stay quiet until something has been typed', async () => {
      const { priceErrors } = await dialog(ref(payload()));

      expect(get(priceErrors)).toEqual([]);
    });

    it('should complain once an unusable price is typed', async () => {
      const { modelPrice, priceErrors } = await dialog(ref(payload()));

      set(modelPrice, '0');

      expect(get(priceErrors)).toEqual(['event_asset_price_update.price_error']);
    });
  });

  describe('saving', () => {
    it('should write the typed price against the event and close', async () => {
      const model = ref<EventPriceUpdatePayload | undefined>(payload());
      const { modelPrice, save } = await dialog(model);
      set(modelPrice, '1600');

      await save();

      expect(updatePrice).toHaveBeenCalledExactlyOnceWith({
        existingEntry: undefined,
        fromAsset: 'ETH',
        mode: 'manual',
        price: '1600',
        timestampMs: 1700000000,
        toAsset: 'USD',
      });
      expect(notifyInfo).toHaveBeenCalledOnce();
      expect(get(model)).toBeUndefined();
    });

    it('should write nothing when no event is being priced', async () => {
      const { save } = await dialog(ref(undefined));

      await save();

      expect(updatePrice).not.toHaveBeenCalled();
    });

    it('should write nothing when the price does not parse', async () => {
      const { modelPrice, save } = await dialog(ref(payload()));
      set(modelPrice, 'abc');

      await save();

      expect(updatePrice).not.toHaveBeenCalled();
    });

    it('should write nothing when the manual price is unchanged, avoiding a duplicate entry', async () => {
      fetchExistingEntry.mockResolvedValue(oracleEntry({ sourceType: PriceOracle.MANUAL }));
      const model = ref<EventPriceUpdatePayload | undefined>(payload());
      const { save } = await dialog(model);

      await save();

      expect(updatePrice).not.toHaveBeenCalled();
      expect(get(model)).toBeUndefined();
    });

    it('should write nothing when keeping the oracle price as it is', async () => {
      fetchExistingEntry.mockResolvedValue(oracleEntry());
      const { save } = await dialog(ref(payload()));

      await save();

      expect(updatePrice).not.toHaveBeenCalled();
    });

    it('should still write when the oracle price is being converted to a manual one', async () => {
      fetchExistingEntry.mockResolvedValue(oracleEntry());
      const { modelMode, save } = await dialog(ref(payload()));

      set(modelMode, 'manual');
      await save();

      expect(updatePrice).toHaveBeenCalledOnce();
      expect(updatePrice.mock.calls[0][0]).toMatchObject({ mode: 'manual', price: '1500' });
    });

    it('should write when the price itself changed', async () => {
      fetchExistingEntry.mockResolvedValue(oracleEntry({ sourceType: PriceOracle.MANUAL }));
      const { modelPrice, save } = await dialog(ref(payload()));

      set(modelPrice, '1600');
      await save();

      expect(updatePrice).toHaveBeenCalledOnce();
    });

    it('should notify and stay open when the write fails', async () => {
      updatePrice.mockRejectedValue(new Error('rejected'));
      const model = ref<EventPriceUpdatePayload | undefined>(payload());
      const { modelPrice, save, saving } = await dialog(model);
      set(modelPrice, '1600');

      await save();

      expect(notifyError).toHaveBeenCalledOnce();
      expect(get(model)).toBeDefined();
      expect(get(saving)).toBe(false);
    });
  });

  describe('closing', () => {
    it('should drop the event without writing anything', async () => {
      const model = ref<EventPriceUpdatePayload | undefined>(payload());
      const { close, open } = await dialog(model);

      close();

      expect(get(model)).toBeUndefined();
      expect(get(open)).toBe(false);
      expect(updatePrice).not.toHaveBeenCalled();
    });
  });
});
