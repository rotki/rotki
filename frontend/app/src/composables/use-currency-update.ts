import { useBalances } from '@/composables/balances/index';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { startPromise } from '@shared/utils';

interface UseCurrencyUpdateReturn { onCurrencyUpdate: () => Promise<void> }

export function useCurrencyUpdate(): UseCurrencyUpdateReturn {
  const { updateSetting } = useFrontendSettingsStore();
  const { refreshPrices } = useBalances();

  async function onCurrencyUpdate(): Promise<void> {
    // TODO: This is temporary fix for double conversion issue. Future solutions should try to eliminate this part.
    startPromise(refreshPrices(true));

    // Clear hide small balances state, if the currency is changed
    startPromise(updateSetting({
      balanceUsdValueThreshold: {},
    }));
  }

  return { onCurrencyUpdate };
}
