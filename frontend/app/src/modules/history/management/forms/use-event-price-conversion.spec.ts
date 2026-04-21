import { bigNumberify } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import '@test/i18n';

const mockGetHistoricPrice = vi.fn();

vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: vi.fn().mockReturnValue({
    getHistoricPrice: mockGetHistoricPrice,
  }),
}));

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    useIsTaskRunning: vi.fn().mockReturnValue(ref<boolean>(false)),
  }),
}));

const { useEventPriceConversion } = await import('@/modules/history/management/forms/use-event-price-conversion');

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

describe('useEventPriceConversion', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockGetHistoricPrice.mockClear().mockResolvedValue(bigNumberify(-1));
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency('USD') });
  });

  it('should fetch historic price on mount when asset and timestamp are set', async () => {
    mockGetHistoricPrice.mockResolvedValueOnce(bigNumberify('2500'));

    const amount = ref<string>('1');
    const asset = ref<string | undefined>('ETH');
    const showPriceFields = ref<boolean>(true);
    const timestamp = ref<number>(1700000000000);

    const { result } = withSetup(() => useEventPriceConversion({
      amount,
      asset,
      showPriceFields,
      timestamp,
    }));

    await flushPromises();

    expect(mockGetHistoricPrice).toHaveBeenCalledWith({
      fromAsset: 'ETH',
      timestamp: 1700000000,
      toAsset: 'USD',
    });
    expect(get(result.fetchedAssetToFiatPrice)).toBe('2500');
    expect(get(result.assetToFiatPrice)).toBe('2500');
  });

  it('should not fetch when asset is undefined', async () => {
    const amount = ref<string>('1');
    const asset = ref<string | undefined>(undefined);
    const showPriceFields = ref<boolean>(true);
    const timestamp = ref<number>(1700000000000);

    withSetup(() => useEventPriceConversion({
      amount,
      asset,
      showPriceFields,
      timestamp,
    }));

    await flushPromises();

    expect(mockGetHistoricPrice).not.toHaveBeenCalled();
  });

  it('should not fetch when timestamp is 0', async () => {
    const amount = ref<string>('1');
    const asset = ref<string | undefined>('ETH');
    const showPriceFields = ref<boolean>(true);
    const timestamp = ref<number>(0);

    withSetup(() => useEventPriceConversion({
      amount,
      asset,
      showPriceFields,
      timestamp,
    }));

    await flushPromises();

    expect(mockGetHistoricPrice).not.toHaveBeenCalled();
  });

  it('should compute fiat value from amount and price', async () => {
    mockGetHistoricPrice.mockResolvedValueOnce(bigNumberify('2500'));

    const amount = ref<string>('3');
    const asset = ref<string | undefined>('ETH');
    const showPriceFields = ref<boolean>(true);
    const timestamp = ref<number>(1700000000000);

    const { result } = withSetup(() => useEventPriceConversion({
      amount,
      asset,
      showPriceFields,
      timestamp,
    }));

    await flushPromises();

    expect(get(result.fiatValue)).toBe('7500');
  });

  it('should refetch when asset changes', async () => {
    mockGetHistoricPrice.mockResolvedValue(bigNumberify('100'));

    const amount = ref<string>('1');
    const asset = ref<string | undefined>('ETH');
    const showPriceFields = ref<boolean>(true);
    const timestamp = ref<number>(1700000000000);

    withSetup(() => useEventPriceConversion({
      amount,
      asset,
      showPriceFields,
      timestamp,
    }));

    await flushPromises();
    const callCount = mockGetHistoricPrice.mock.calls.length;

    set(asset, 'BTC');
    await flushPromises();

    expect(mockGetHistoricPrice.mock.calls.length).toBeGreaterThan(callCount);
    expect(mockGetHistoricPrice).toHaveBeenLastCalledWith(
      expect.objectContaining({ fromAsset: 'BTC' }),
    );
  });

  it('should reset all values', async () => {
    mockGetHistoricPrice.mockResolvedValueOnce(bigNumberify('2500'));

    const amount = ref<string>('2');
    const asset = ref<string | undefined>('ETH');
    const showPriceFields = ref<boolean>(true);
    const timestamp = ref<number>(1700000000000);

    const { result } = withSetup(() => useEventPriceConversion({
      amount,
      asset,
      showPriceFields,
      timestamp,
    }));

    await flushPromises();

    expect(get(result.assetToFiatPrice)).not.toBe('');

    result.reset();

    expect(get(result.fetchedAssetToFiatPrice)).toBe('');
    expect(get(result.assetToFiatPrice)).toBe('');
    expect(get(result.fiatValue)).toBe('');
  });

  it('should update fiat value when amount changes', async () => {
    mockGetHistoricPrice.mockResolvedValueOnce(bigNumberify('1000'));

    const amount = ref<string>('2');
    const asset = ref<string | undefined>('ETH');
    const showPriceFields = ref<boolean>(true);
    const timestamp = ref<number>(1700000000000);

    const { result } = withSetup(() => useEventPriceConversion({
      amount,
      asset,
      showPriceFields,
      timestamp,
    }));

    await flushPromises();
    expect(get(result.fiatValue)).toBe('2000');

    set(amount, '5');
    await flushPromises();

    expect(get(result.fiatValue)).toBe('5000');
  });
});
