import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';
import { useBalancePricesStore } from './use-balance-prices-store';

describe('useBalancePricesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should start with empty prices and rates and no previous currency', () => {
    const store = useBalancePricesStore();
    expect(get(store.prices)).toEqual({});
    expect(get(store.exchangeRates)).toEqual({});
    expect(get(store.previousCurrency)).toBeUndefined();
  });

  it('should hold the assigned prices, rates and previous currency', () => {
    const { exchangeRates, prices, previousCurrency } = storeToRefs(useBalancePricesStore());
    set(prices, { ETH: { isManualPrice: false, oracle: 'coingecko', value: bigNumberify(1000) } });
    set(exchangeRates, { EUR: bigNumberify(0.9) });
    set(previousCurrency, 'EUR');

    expect(get(prices).ETH.value).toEqual(bigNumberify(1000));
    expect(get(exchangeRates).EUR).toEqual(bigNumberify(0.9));
    expect(get(previousCurrency)).toBe('EUR');
  });
});
