import { CURRENCY_USD } from '@/types/currencies';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import type { BalanceSource } from '@/types/settings/frontend-settings';
import type { ComputedRef } from 'vue';

export function useUsdValueThreshold(balanceSource: BalanceSource): ComputedRef<string> {
  const { balanceUsdValueThreshold } = storeToRefs(useFrontendSettingsStore());
  const { exchangeRate } = useBalancePricesStore();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  return computed(() => {
    const valueThreshold = get(balanceUsdValueThreshold)[balanceSource];
    const currency = get(currencySymbol);

    if (!valueThreshold || currency === CURRENCY_USD)
      return valueThreshold;

    const rate = get(exchangeRate(currency)) ?? One;
    return bigNumberify(valueThreshold).multipliedBy(rate).toFixed();
  });
}
