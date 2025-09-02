import type { ContextColorsType } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { EthereumValidator } from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import { type BigNumber, One, Zero } from '@rotki/common';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useGeneralSettingsStore } from '@/store/settings/general';

interface UseEthValidatorUtilsReturn {
  getColor: (status: string) => ContextColorsType | undefined;
  getOwnershipPercentage: (row: EthereumValidator) => string;
  useTotal: (rows: Ref<Collection<EthereumValidator>>) => ComputedRef<BigNumber>;
}

export function useEthValidatorUtils(): UseEthValidatorUtilsReturn {
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { useExchangeRate } = usePriceUtils();

  const colorMap: Record<string, ContextColorsType | undefined> = {
    active: 'success',
    consolidated: 'secondary',
    exited: 'error',
    exiting: 'warning',
    pending: 'info',
  };

  function getColor(status: string): ContextColorsType | undefined {
    return colorMap[status] ?? undefined;
  }

  function getOwnershipPercentage(row: EthereumValidator): string {
    return row.ownershipPercentage || '100';
  }

  const useTotal = (rows: Ref<Collection<EthereumValidator>>): ComputedRef<BigNumber> => computed(() => {
    const mainCurrency = get(currencySymbol);
    return (get(rows).totalUsdValue || Zero).multipliedBy(get(useExchangeRate(mainCurrency)) ?? One);
  });

  return {
    getColor,
    getOwnershipPercentage,
    useTotal,
  };
}
