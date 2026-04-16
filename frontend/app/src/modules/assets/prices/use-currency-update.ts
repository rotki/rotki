import type { AssetPrices } from '@/modules/assets/prices/price-types';
import { One } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface UseCurrencyUpdateReturn { onCurrencyUpdate: () => Promise<void> }

export function useCurrencyUpdate(): UseCurrencyUpdateReturn {
  const { updateFrontendSetting } = useSettingsOperations();
  const { adjustPrices, refreshPrices } = usePriceRefresh();
  const { fetchExchangeRates } = usePriceTaskManager();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { exchangeRates, previousCurrency, prices } = storeToRefs(useBalancePricesStore());

  if (!get(previousCurrency)) {
    set(previousCurrency, get(currencySymbol));
  }

  async function onCurrencyUpdate(): Promise<void> {
    const oldCurrency = get(previousCurrency)!;
    const newCurrency = get(currencySymbol);
    set(previousCurrency, newCurrency);

    // Approximate prices using exchange rate ratio while real prices load
    if (oldCurrency !== newCurrency) {
      let rates = get(exchangeRates);
      const oldRate = oldCurrency === CURRENCY_USD ? One : rates[oldCurrency];

      // Ensure the new currency's exchange rate is available
      if (newCurrency !== CURRENCY_USD && !rates[newCurrency]) {
        await fetchExchangeRates(newCurrency);
        rates = get(exchangeRates);
      }

      const newRate = newCurrency === CURRENCY_USD ? One : rates[newCurrency];

      if (oldRate && newRate && !oldRate.isZero()) {
        const ratio = newRate.div(oldRate);
        const currentPrices = get(prices);
        const scaledPrices: AssetPrices = {};

        for (const [asset, priceData] of Object.entries(currentPrices)) {
          scaledPrices[asset] = {
            ...priceData,
            value: priceData.value.multipliedBy(ratio),
          };
        }

        set(prices, scaledPrices);
        adjustPrices(scaledPrices);
      }
    }

    startPromise(refreshPrices(true));

    // Clear hide small balances state, if the currency is changed
    startPromise(updateFrontendSetting({
      balanceValueThreshold: {},
    }));
  }

  return { onCurrencyUpdate };
}
