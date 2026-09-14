import type { ComputedRef } from 'vue';
import type { ExchangeInfo } from '@/modules/balances/types/exchanges';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { exchangeAssetSum } from '@/modules/core/common/data/calculation';
import { useLocationStore } from '@/modules/core/common/use-location-store';

interface UseBankDataReturn {
  /** The connected banks with balances, richest first. */
  banks: ComputedRef<ExchangeInfo[]>;
  isBankLocation: (location: string) => boolean;
}

/**
 * Bank balances live in the same per-location map as exchange balances, so the net worth, the
 * location breakdown and every asset view already count them. This is the bank-only view of that
 * map, for the surfaces that show banks apart from exchanges.
 */
export function useBankData(): UseBankDataReturn {
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { banks: bankLocations } = storeToRefs(useLocationStore());
  const { isAssetIgnored } = useAssetsStore();

  const isBankLocation = (location: string): boolean => get(bankLocations).includes(location);

  const banks = computed<ExchangeInfo[]>(() => Object.entries(get(exchangeBalances))
    .filter(([location]) => isBankLocation(location))
    .map(([location, balances]) => ({
      balances,
      location,
      total: exchangeAssetSum(balances, isAssetIgnored),
    }))
    .sort((a, b) => sortDesc(a.total, b.total)));

  return {
    banks,
    isBankLocation,
  };
}
