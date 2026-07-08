import type { AssetPrices } from '@/modules/assets/prices/price-types';
import { bigNumberify } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencyUpdate } from './use-currency-update';

const currencySymbol = ref<string>('USD');
const previousCurrency = ref<string>();
const exchangeRates = ref<Record<string, ReturnType<typeof bigNumberify>>>({});
const prices = ref<AssetPrices>({});

const { spies } = vi.hoisted(() => ({
  spies: {
    updateFrontendSetting: vi.fn(),
    adjustPrices: vi.fn(),
    refreshPrices: vi.fn(),
    fetchExchangeRates: vi.fn(),
  },
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ updateFrontendSetting: spies.updateFrontendSetting }),
}));
vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: (): object => ({ adjustPrices: spies.adjustPrices, refreshPrices: spies.refreshPrices }),
}));
vi.mock('@/modules/assets/prices/use-price-task-manager', () => ({
  usePriceTaskManager: (): object => ({ fetchExchangeRates: spies.fetchExchangeRates }),
}));
vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => currencySymbol),
}));
vi.mock('@/modules/balances/use-balance-prices-store', () => ({
  useBalancePricesStore: vi.fn(() => ({ exchangeRates, previousCurrency, prices })),
}));

function price(value: number): AssetPrices[string] {
  return { isManualPrice: false, oracle: 'coingecko', value: bigNumberify(value) };
}

describe('useCurrencyUpdate', () => {
  beforeEach(() => {
    set(currencySymbol, 'USD');
    set(previousCurrency, undefined);
    set(exchangeRates, { EUR: bigNumberify(0.9) });
    set(prices, { ETH: price(100) });
    spies.refreshPrices.mockResolvedValue(undefined);
    spies.updateFrontendSetting.mockResolvedValue(undefined);
    spies.fetchExchangeRates.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should seed the previous currency from the current symbol', () => {
    useCurrencyUpdate();
    expect(get(previousCurrency)).toBe('USD');
  });

  it('should refresh prices and reset the balance threshold on update', async () => {
    const { onCurrencyUpdate } = useCurrencyUpdate();
    await onCurrencyUpdate();
    expect(spies.refreshPrices).toHaveBeenCalledWith(true);
    expect(spies.updateFrontendSetting).toHaveBeenCalledWith({ balanceValueThreshold: {} });
  });

  it('should scale prices by the exchange-rate ratio when the currency changes', async () => {
    const { onCurrencyUpdate } = useCurrencyUpdate();
    set(currencySymbol, 'EUR');
    await onCurrencyUpdate();
    // USD (rate 1) -> EUR (rate 0.9): 100 * 0.9 = 90
    expect(get(prices).ETH.value).toEqual(bigNumberify(90));
    expect(spies.adjustPrices).toHaveBeenCalledOnce();
    expect(get(previousCurrency)).toBe('EUR');
  });

  it('should fetch a missing exchange rate before scaling', async () => {
    spies.fetchExchangeRates.mockImplementation(async (currency: string) => {
      set(exchangeRates, { ...get(exchangeRates), [currency]: bigNumberify(0.5) });
    });
    const { onCurrencyUpdate } = useCurrencyUpdate();
    set(currencySymbol, 'GBP');
    await onCurrencyUpdate();
    expect(spies.fetchExchangeRates).toHaveBeenCalledWith('GBP');
    expect(get(prices).ETH.value).toEqual(bigNumberify(50)); // 100 * 0.5
  });

  it('should not scale non-positive prices', async () => {
    set(prices, { ETH: price(0) });
    const { onCurrencyUpdate } = useCurrencyUpdate();
    set(currencySymbol, 'EUR');
    await onCurrencyUpdate();
    expect(get(prices).ETH.value).toEqual(bigNumberify(0));
  });
});
