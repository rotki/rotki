import type { OraclePriceEntry } from '@/modules/assets/prices/price-types';
import { bigNumberify } from '@rotki/common';
import { componentVm } from '@test/utils/component-vm';
import { mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@test/i18n';

const mockEditHistoricalPrice = vi.fn();
const mockResetHistoricalPricesData = vi.fn();

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: vi.fn().mockReturnValue({
    editHistoricalPrice: (...args: unknown[]) => mockEditHistoricalPrice(...args),
  }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: vi.fn().mockReturnValue({
    resetHistoricalPricesData: (...args: unknown[]) => mockResetHistoricalPricesData(...args),
  }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    getAssetField: vi.fn().mockImplementation((asset: string) => asset),
  }),
}));

const BigDialog = (await import('@/modules/shell/components/dialogs/BigDialog.vue')).default;
const OraclePriceEditDialog = (await import('@/modules/assets/prices/components/oracle/OraclePriceEditDialog.vue')).default;

function createEntry(overrides: Partial<OraclePriceEntry> = {}): OraclePriceEntry {
  return {
    fromAsset: 'ETH',
    price: bigNumberify('2500'),
    sourceType: 'coingecko',
    timestamp: 1700000000,
    toAsset: 'USD',
    ...overrides,
  };
}

describe('oraclePriceEditDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockEditHistoricalPrice.mockClear().mockResolvedValue(true);
    mockResetHistoricalPricesData.mockClear();
  });

  it('should invalidate the historic price cache after a successful edit', async () => {
    const entry = createEntry();
    const wrapper = mount(OraclePriceEditDialog, {
      shallow: true,
      props: { modelValue: entry },
    });
    await flushPromises();

    const vm = componentVm<{ editedPrice: string; save: () => Promise<void> }>(wrapper);
    vm.editedPrice = '3000';
    await vm.save();
    await flushPromises();

    expect(mockEditHistoricalPrice).toHaveBeenCalledWith({
      fromAsset: 'ETH',
      price: '3000',
      sourceType: 'coingecko',
      timestamp: 1700000000,
      toAsset: 'USD',
    });
    expect(mockResetHistoricalPricesData).toHaveBeenCalledWith([
      { fromAsset: 'ETH', timestamp: 1700000000 },
    ]);
    expect(wrapper.emitted('refresh')).toHaveLength(1);
  });

  it('should name a failed edit in the dialog, keeping it open and the cache untouched', async () => {
    const error = new Error('boom');
    mockEditHistoricalPrice.mockRejectedValueOnce(error);
    const entry = createEntry();
    const wrapper = mount(OraclePriceEditDialog, {
      shallow: true,
      props: { modelValue: entry },
    });
    await flushPromises();

    const vm = componentVm<{ editedPrice: string; save: () => Promise<void> }>(wrapper);
    vm.editedPrice = '3000';
    await vm.save();
    await flushPromises();

    expect(mockResetHistoricalPricesData).not.toHaveBeenCalled();
    expect(wrapper.findComponent(BigDialog).props('failure')).toBe(error);
    expect(wrapper.findComponent(BigDialog).props('failureTitle')).toBe('oracle_prices.edit.error.title');
    expect(wrapper.emitted('refresh')).toBeUndefined();
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });
});
