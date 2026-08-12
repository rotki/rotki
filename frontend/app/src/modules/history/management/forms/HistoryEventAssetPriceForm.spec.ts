import type { Pinia } from 'pinia';
import type { PriceIntent } from '@/modules/history/management/forms/price-intent';
import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import HistoryEventAssetPriceForm from '@/modules/history/management/forms/HistoryEventAssetPriceForm.vue';

const { mockGetHistoricPrice } = vi.hoisted(() => ({ mockGetHistoricPrice: vi.fn() }));

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: vi.fn().mockReturnValue({
    getHistoricPrice: mockGetHistoricPrice,
  }),
}));

vi.mock('@/modules/assets/api/use-asset-info-api', () => ({
  useAssetInfoApi: vi.fn(),
}));

const timestamp = 1742901211000;

describe('forms/HistoryEventAssetPriceForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof HistoryEventAssetPriceForm>>;
  let pinia: Pinia;

  beforeAll(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    mockGetHistoricPrice.mockClear().mockResolvedValue(bigNumberify('2500'));

    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency('USD') });

    vi.mocked(useAssetInfoApi).mockReturnValue({
      assetMapping: vi.fn<ReturnType<typeof useAssetInfoApi>['assetMapping']>(),
      assetSearch: vi.fn<ReturnType<typeof useAssetInfoApi>['assetSearch']>(),
      erc20details: vi.fn<ReturnType<typeof useAssetInfoApi>['erc20details']>(),
    });
  });

  afterEach(() => {
    wrapper.unmount();
  });

  const createWrapper = (
    props: Partial<ComponentMountingOptions<typeof HistoryEventAssetPriceForm>['props']> = {},
  ): VueWrapper<InstanceType<typeof HistoryEventAssetPriceForm>> => mount(HistoryEventAssetPriceForm, {
    global: {
      plugins: [pinia],
    },
    props: {
      amount: '1',
      asset: 'ETH',
      errorMessages: { amount: [], asset: [] },
      location: 'ethereum',
      timestamp,
      ...props,
    },
  });

  /** The last value the form reported through `v-model:price-intent`. */
  function lastIntent(): PriceIntent | undefined {
    const emitted = wrapper.emitted<[PriceIntent | undefined]>('update:priceIntent') ?? [];
    return emitted.at(-1)?.[0];
  }

  it('should report no intent while the price is the one that was fetched', async () => {
    wrapper = createWrapper();
    await flushPromises();

    expect(lastIntent()).toBeUndefined();
  });

  it('should report the price the user typed as an intent', async () => {
    wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid=primary] input').setValue('3000');
    await flushPromises();

    expect(lastIntent()).toEqual({
      fromAsset: 'ETH',
      price: '3000',
      timestampMs: timestamp,
      toAsset: 'USD',
    });
  });

  it('should withdraw the intent once the price is edited back to the fetched one', async () => {
    wrapper = createWrapper();
    await flushPromises();

    await wrapper.find('[data-testid=primary] input').setValue('3000');
    await flushPromises();
    expect(lastIntent()).toBeDefined();

    await wrapper.find('[data-testid=primary] input').setValue('2500');
    await flushPromises();

    expect(lastIntent()).toBeUndefined();
  });

  it('should report no intent for an asset that is the display currency itself', async () => {
    wrapper = createWrapper({ asset: 'USD' });
    await flushPromises();

    await wrapper.find('[data-testid=primary] input').setValue('3000');
    await flushPromises();

    expect(lastIntent()).toBeUndefined();
  });

  it('should report no intent while the form is disabled', async () => {
    wrapper = createWrapper({ disabled: true });
    await flushPromises();

    await wrapper.find('[data-testid=primary] input').setValue('3000');
    await flushPromises();

    expect(lastIntent()).toBeUndefined();
  });

  it('should report no intent when the form has no price fields at all', async () => {
    wrapper = createWrapper({ noPriceFields: true });
    await flushPromises();

    expect(lastIntent()).toBeUndefined();
  });
});
