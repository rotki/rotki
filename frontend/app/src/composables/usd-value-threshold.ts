import type { ComputedRef } from 'vue';
import { bigNumberify, One } from '@rotki/common';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';
import { type BalanceSource, BalanceSource as BalanceSourceEnum } from '@/types/settings/frontend-settings';

const SOURCES_WITHOUT_RATE_CONVERSION: BalanceSource[] = [BalanceSourceEnum.MANUAL, BalanceSourceEnum.EXCHANGES];

export function useUsdValueThreshold(balanceSource: BalanceSource): ComputedRef<string | undefined> {
  const { balanceUsdValueThreshold } = storeToRefs(useFrontendSettingsStore());
  const { useExchangeRate } = usePriceUtils();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  return computed<string | undefined>(() => {
    const valueThreshold = get(balanceUsdValueThreshold)[balanceSource];
    const currency = get(currencySymbol);

    if (!valueThreshold || currency === CURRENCY_USD || SOURCES_WITHOUT_RATE_CONVERSION.includes(balanceSource))
      return valueThreshold;

    const rate = get(useExchangeRate(currency)) ?? One;
    return bigNumberify(valueThreshold).multipliedBy(rate).toFixed();
  });
}
