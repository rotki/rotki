import type { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { type AssetBalanceWithPriceAndChains, BigNumber } from '@rotki/common';
import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useStatisticsStore } from './use-statistics-store';

let generalSettingsStore: ReturnType<typeof useSettingsRepo> | null = null;

/** USD-to-currency rates the mock serves, shared with the assertions so neither can drift. */
const JPY_RATE = 150;
const EUR_RATE = 0.9;

function getExchangeRate(currency: string): BigNumber {
  if (currency === 'JPY')
    return new BigNumber(JPY_RATE);
  if (currency === 'EUR')
    return new BigNumber(EUR_RATE);
  return new BigNumber('1');
}

function createBalanceWithPrice(
  amount: string,
  asset: string,
  price: string,
): AssetBalanceWithPriceAndChains {
  const amountBN = new BigNumber(amount);
  const priceBN = new BigNumber(price);
  const usdValue = amountBN.multipliedBy(priceBN);
  const currency = generalSettingsStore ? generalSettingsStore.general.mainCurrency.tickerSymbol : 'USD';
  const rate = getExchangeRate(currency);
  const value = asset === currency ? amountBN : usdValue.multipliedBy(rate);

  return {
    amount: amountBN,
    asset,
    price: priceBN,
    value,
  };
}

vi.mock('@/modules/balances/use-aggregated-balances', () => ({
  useAggregatedBalances: vi.fn(() => ({
    getBalances: (): AssetBalanceWithPriceAndChains[] => [
      createBalanceWithPrice('10000', 'JPY', '0.01'),
      createBalanceWithPrice('2', 'ETH', '2000'),
      createBalanceWithPrice('0.5', 'BTC', '40000'),
    ],
    getLiabilities: (): AssetBalanceWithPriceAndChains[] => [
      createBalanceWithPrice('1000', 'USD', '1'),
    ],
  })),
}));

vi.mock('@/modules/assets/amount-display/use-number-scrambler', () => ({
  useNumberScrambler: vi.fn(({ value }) => value),
}));

vi.mock('@/modules/assets/prices/use-price-utils', () => ({
  usePriceUtils: (): Pick<ReturnType<typeof usePriceUtils>, 'getExchangeRate'> => ({
    getExchangeRate: (currency: string): BigNumber => getExchangeRate(currency),
  }),
}));

describe('useStatisticsStore', () => {
  let generalSettings: ReturnType<typeof useSettingsRepo>;
  let currencies: ReturnType<typeof useCurrencies>;

  /**
   * Switches the main currency, which the store reads only when it is created.
   *
   * @remarks
   * `defaultGeneralSettings` is reapplied alongside `mainCurrency` because it derives other
   * currency-dependent defaults, which would otherwise keep the previous currency's values.
   */
  function setMainCurrency(symbol: string): void {
    generalSettings.updateGeneral({
      ...defaultGeneralSettings(currencies.findCurrency(symbol)),
      mainCurrency: currencies.findCurrency(symbol),
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());

    generalSettings = useSettingsRepo();
    currencies = useCurrencies();
    generalSettingsStore = generalSettings;

    setMainCurrency('USD');
  });

  describe('calculateTotalValue with main currency handling', () => {
    it('should use amount directly for main currency assets and convert USD values for others', () => {
      setMainCurrency('JPY');

      const store = useStatisticsStore();
      const totalValue = get(store.totalNetWorth);

      const mainCurrencyAssetAtFaceValue = 10000;
      const assets = mainCurrencyAssetAtFaceValue + (4000 * JPY_RATE) + (20000 * JPY_RATE);
      const liabilities = 1000 * JPY_RATE;
      expect(totalValue.toNumber()).toBe(assets - liabilities);
    });

    it('should correctly calculate when USD is the main currency', () => {
      const store = useStatisticsStore();
      const totalValue = get(store.totalNetWorth);

      expect(totalValue.toNumber()).toBe((100 + 4000 + 20000) - 1000);
    });

    it('should correctly handle EUR as main currency', () => {
      setMainCurrency('EUR');

      const store = useStatisticsStore();
      const totalValue = get(store.totalNetWorth);

      const noAssetIsInTheMainCurrency = 100 + 4000 + 20000;
      const assets = noAssetIsInTheMainCurrency * EUR_RATE;
      const liabilities = 1000 * EUR_RATE;
      expect(totalValue.toNumber()).toBe(assets - liabilities);
    });

    it('should correctly handle when main currency appears in liabilities', async () => {
      const module = await import('@/modules/balances/use-aggregated-balances');
      // @ts-expect-error partial mock - only getBalances and getLiabilities are used by the store
      vi.mocked(module.useAggregatedBalances).mockImplementationOnce(() => ({
        getBalances: (): AssetBalanceWithPriceAndChains[] => [
          createBalanceWithPrice('2', 'ETH', '2000'),
        ],
        getLiabilities: (): AssetBalanceWithPriceAndChains[] => [
          createBalanceWithPrice('5000', 'JPY', '0.01'),
          createBalanceWithPrice('1000', 'USD', '1'),
        ],
      }));

      setMainCurrency('JPY');

      const store = useStatisticsStore();
      const totalValue = get(store.totalNetWorth);

      const assets = 4000 * JPY_RATE;
      const mainCurrencyLiabilityAtFaceValue = 5000;
      const liabilities = mainCurrencyLiabilityAtFaceValue + (1000 * JPY_RATE);
      expect(totalValue.toNumber()).toBe(assets - liabilities);
    });
  });

  describe('totalNetWorth', () => {
    it('should not double-apply exchange rate', () => {
      setMainCurrency('JPY');

      const store = useStatisticsStore();
      const totalValue = get(store.totalNetWorth);

      // Verify totalNetWorth equals calculateTotalValue without additional multiplication
      expect(totalValue.toNumber()).toBe(3460000);
    });
  });

  describe('getNetValue snapshotCount', () => {
    it('should return snapshotCount of 0 when there is no backend data', () => {
      const store = useStatisticsStore();
      const result = store.getNetValue(0);

      expect(result.snapshotCount).toBe(0);
      // Should still have 2 data points (synthetic zero + current balance)
      expect(result.data).toHaveLength(2);
    });

    it('should return snapshotCount matching the number of real backend data points', () => {
      const store = useStatisticsStore();
      const now = Math.floor(Date.now() / 1000);

      store.netValue = {
        data: [new BigNumber('1000'), new BigNumber('2000'), new BigNumber('3000')],
        times: [now - 300, now - 200, now - 100],
      };

      const result = store.getNetValue(0);

      // 3 real snapshots from the backend
      expect(result.snapshotCount).toBe(3);
      // Total should be 3 snapshots + 1 appended current balance
      expect(result.data).toHaveLength(4);
    });

    it('should exclude snapshots before startingDate from snapshotCount', () => {
      const store = useStatisticsStore();
      const now = Math.floor(Date.now() / 1000);

      store.netValue = {
        data: [new BigNumber('1000'), new BigNumber('2000'), new BigNumber('3000')],
        times: [now - 300, now - 200, now - 100],
      };

      const afterTheFirstTwoSnapshots = now - 150;
      const result = store.getNetValue(afterTheFirstTwoSnapshots);

      expect(result.snapshotCount).toBe(1);
      // 1 real snapshot + 1 appended current balance
      expect(result.data).toHaveLength(2);
    });
  });
});
