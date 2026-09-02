import type { AssetPrices } from '@/modules/assets/prices/price-types';
import { type BigNumber, bigNumberify, One } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { BalanceSource, type BalanceValueThreshold } from '@/modules/settings/types/frontend-settings';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface UseCurrencyUpdateReturn { onCurrencyUpdate: () => Promise<void> }

type Currency = ReturnType<typeof useSetting<'currencySymbol'>>['value'];

export function useCurrencyUpdate(): UseCurrencyUpdateReturn {
  const { updateFrontendSetting } = useSettingsOperations();
  const { adjustPrices, refreshPrices } = usePriceRefresh();
  const { fetchExchangeRates } = usePriceTaskManager();
  const currencySymbol = useSetting('currencySymbol');
  const balanceValueThreshold = useSetting('balanceValueThreshold');
  const { exchangeRates, previousCurrency, prices } = storeToRefs(useBalancePricesStore());

  if (!get(previousCurrency)) {
    set(previousCurrency, get(currencySymbol));
  }

  /**
   * Re-denominates the hide-small-balances thresholds into the currency being switched to.
   *
   * @remarks
   * The thresholds are stored in the user's main currency, so they have to move with it or a
   * threshold set in one currency starts hiding a different slice of the balances in the next.
   * Sources with no threshold stay absent, and when no source has one the setting is left
   * untouched: writing an empty object would re-trigger the balance watchers for nothing.
   * @param ratio - the new currency's rate over the old one, the same factor applied to prices
   */
  function convertValueThresholds(ratio: BigNumber): void {
    const thresholds = get(balanceValueThreshold);
    const converted: BalanceValueThreshold = {};
    let hasThreshold = false;

    for (const source of Object.values(BalanceSource)) {
      const value = thresholds[source];
      if (value === undefined || value === '')
        continue;
      converted[source] = bigNumberify(value).multipliedBy(ratio).toString();
      hasThreshold = true;
    }

    if (hasThreshold)
      startPromise(updateFrontendSetting({ balanceValueThreshold: converted }));
  }

  /**
   * The two rates the conversion needs. Only the new currency's rate may be missing, since the old one
   * was in use a moment ago, so that is the only one worth fetching.
   */
  async function conversionRates(oldCurrency: Currency, newCurrency: Currency): Promise<{
    oldRate?: BigNumber;
    newRate?: BigNumber;
  }> {
    let rates = get(exchangeRates);
    const oldRate = oldCurrency === CURRENCY_USD ? One : rates[oldCurrency];

    if (newCurrency !== CURRENCY_USD && !rates[newCurrency]) {
      await fetchExchangeRates(newCurrency);
      rates = get(exchangeRates);
    }

    return { newRate: newCurrency === CURRENCY_USD ? One : rates[newCurrency], oldRate };
  }

  /** Approximates every held price in the new currency so the UI has something until real prices load. */
  function scalePrices(ratio: BigNumber): void {
    const scaledPrices: AssetPrices = {};

    for (const [asset, priceData] of Object.entries(get(prices))) {
      scaledPrices[asset] = {
        ...priceData,
        value: priceData.value.gt(0) ? priceData.value.multipliedBy(ratio) : priceData.value,
      };
    }

    set(prices, scaledPrices);
    adjustPrices(scaledPrices);
    convertValueThresholds(ratio);
  }

  async function onCurrencyUpdate(): Promise<void> {
    const oldCurrency = get(previousCurrency)!;
    const newCurrency = get(currencySymbol);
    set(previousCurrency, newCurrency);

    if (oldCurrency !== newCurrency) {
      const { newRate, oldRate } = await conversionRates(oldCurrency, newCurrency);

      if (oldRate && newRate && !oldRate.isZero())
        scalePrices(newRate.div(oldRate));
    }

    startPromise(refreshPrices(true));
  }

  return { onCurrencyUpdate };
}
