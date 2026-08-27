import { bigNumberify, NoPrice } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useHistoricFiatConversion } from '@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion';

const getHistoricPrice = vi.fn();
const getIsPending = vi.fn();

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: vi.fn(() => ({
    createKey: (fromAsset: string, timestamp: number): string => `${fromAsset}#${timestamp}`,
    getHistoricPrice,
    getIsPending,
  })),
}));

describe('modules/dashboard/snapshots/composables/use-historic-fiat-conversion', () => {
  const timestampInSeconds = 1_600_000_000;

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    getHistoricPrice.mockReturnValue(NoPrice);
    getIsPending.mockReturnValue(false);
  });

  function setCurrency(symbol: string): void {
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency(symbol) });
  }

  it('should short-circuit to a rate of one when the display currency is USD', () => {
    setCurrency('USD');
    const { isUsd, loading, rate, rateReady } = useHistoricFiatConversion(timestampInSeconds);

    expect(get(isUsd)).toBe(true);
    expect(get(rate).toNumber()).toBe(1);
    expect(get(loading)).toBe(false);
    expect(get(rateReady)).toBe(true);
    expect(getHistoricPrice).not.toHaveBeenCalled();
  });

  it('should resolve the historic USD rate for a non-USD currency', () => {
    setCurrency('EUR');
    getHistoricPrice.mockReturnValue(bigNumberify(0.85));
    const { isUsd, rate, rateReady } = useHistoricFiatConversion(timestampInSeconds);

    expect(get(isUsd)).toBe(false);
    expect(get(rate).toNumber()).toBe(0.85);
    expect(get(rateReady)).toBe(true);
    expect(getHistoricPrice).toHaveBeenCalledWith('USD', timestampInSeconds);
  });

  it('should report loading and a not-ready rate while the lookup is pending', () => {
    setCurrency('EUR');
    getHistoricPrice.mockReturnValue(NoPrice);
    getIsPending.mockReturnValue(true);
    const { loading, rateReady } = useHistoricFiatConversion(timestampInSeconds);

    expect(get(loading)).toBe(true);
    expect(get(rateReady)).toBe(false);
  });

  it('should start the lookup without anything reading the rate', async () => {
    setCurrency('EUR');
    getHistoricPrice.mockReturnValue(bigNumberify(0.85));
    const ts = ref<number>(timestampInSeconds);
    useHistoricFiatConversion(() => get(ts));

    expect(getHistoricPrice).toHaveBeenCalledWith('USD', timestampInSeconds);

    set(ts, timestampInSeconds + 86_400);
    await nextTick();

    expect(getHistoricPrice).toHaveBeenCalledWith('USD', timestampInSeconds + 86_400);
  });

  it('should accept a getter for the timestamp', () => {
    setCurrency('EUR');
    getHistoricPrice.mockReturnValue(bigNumberify(0.9));
    const ts = ref<number>(timestampInSeconds);
    const { rate } = useHistoricFiatConversion(() => get(ts));

    expect(get(rate).toNumber()).toBe(0.9);
    expect(getHistoricPrice).toHaveBeenCalledWith('USD', timestampInSeconds);
  });
});
