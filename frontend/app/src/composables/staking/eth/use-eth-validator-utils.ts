import type { ContextColorsType } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { EthereumValidator } from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import { type BigNumber, Zero } from '@rotki/common';

interface UseEthValidatorUtilsReturn {
  getColor: (status: string) => ContextColorsType | undefined;
  getOwnershipPercentage: (row: EthereumValidator) => string;
  useTotal: (rows: Ref<Collection<EthereumValidator>>) => ComputedRef<BigNumber>;
  useTotalAmount: (rows: Ref<Collection<EthereumValidator>>) => ComputedRef<BigNumber>;
}

export function useEthValidatorUtils(): UseEthValidatorUtilsReturn {
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

  const useTotal = (rows: Ref<Collection<EthereumValidator>>): ComputedRef<BigNumber> => computed(() => get(rows).totalValue || Zero);
  const useTotalAmount = (rows: Ref<Collection<EthereumValidator>>): ComputedRef<BigNumber> => computed(() => get(rows).totalAmount || Zero);

  return {
    getColor,
    getOwnershipPercentage,
    useTotal,
    useTotalAmount,
  };
}
