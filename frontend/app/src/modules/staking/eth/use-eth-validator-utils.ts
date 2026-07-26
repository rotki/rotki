import type { ContextColorsType } from '@rotki/ui-library';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import { type BigNumber, Zero } from '@rotki/common';
import { nonEmptyOr } from '@/modules/core/common/data/data';

interface UseEthValidatorUtilsReturn {
  getColor: (status: string) => ContextColorsType | undefined;
  getOwnershipPercentage: (row: EthereumValidator) => string;
  useTotal: (rows: MaybeRefOrGetter<Collection<EthereumValidator>>) => ComputedRef<BigNumber>;
  useTotalAmount: (rows: MaybeRefOrGetter<Collection<EthereumValidator>>) => ComputedRef<BigNumber>;
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
    return nonEmptyOr(row.ownershipPercentage, '100');
  }

  const useTotal = (rows: MaybeRefOrGetter<Collection<EthereumValidator>>): ComputedRef<BigNumber> => computed(() => toValue(rows).totalValue ?? Zero);
  const useTotalAmount = (rows: MaybeRefOrGetter<Collection<EthereumValidator>>): ComputedRef<BigNumber> => computed(() => toValue(rows).totalAmount ?? Zero);

  return {
    getColor,
    getOwnershipPercentage,
    useTotal,
    useTotalAmount,
  };
}
