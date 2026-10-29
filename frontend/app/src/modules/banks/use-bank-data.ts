import type { ComputedRef } from 'vue';
import type { ExchangeData, ExchangeInfo } from '@/modules/balances/types/exchanges';
import { type AssetBalanceWithPriceAndChains, type BigNumber, Zero } from '@rotki/common';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { fromExchanges } from '@/modules/balances/aggregation/core/sources';
import { summarizeBalances } from '@/modules/balances/aggregation/core/summarize';
import { useAggregationContext } from '@/modules/balances/aggregation/use-aggregation-context';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { exchangeAssetSum } from '@/modules/core/common/data/calculation';

interface UseBankDataReturn {
  /** The connected banks with balances, richest first. */
  banks: ComputedRef<ExchangeInfo[]>;
  /** Every bank's holdings in one list, an asset held at several banks broken down by bank. */
  balances: ComputedRef<AssetBalanceWithPriceAndChains[]>;
  /** What all banks hold together, ignored assets left out. */
  total: ComputedRef<BigNumber>;
  isBankLocation: (location: string) => boolean;
}

/**
 * Bank balances live in the same per-location map as exchange balances, so the net worth, the
 * location breakdown and every asset view already count them. This is the bank-only view of that
 * map, for the surfaces that show banks apart from exchanges.
 */
export function useBankData(): UseBankDataReturn {
  const { exchangeBalances } = storeToRefs(useBalancesStore());
  const { bankLocations } = storeToRefs(useBankConnectionsStore());
  const { isAssetIgnored } = useAssetsStore();
  const context = useAggregationContext();

  const isBankLocation = (location: string): boolean => get(bankLocations).includes(location);

  const bankBalances = computed<ExchangeData>(() => Object.fromEntries(
    Object.entries(get(exchangeBalances)).filter(([location]) => isBankLocation(location)),
  ));

  const banks = computed<ExchangeInfo[]>(() => Object.entries(get(bankBalances))
    .map(([location, balances]) => ({
      balances,
      location,
      total: exchangeAssetSum(balances, isAssetIgnored),
    }))
    .sort((a, b) => sortDesc(a.total, b.total)));

  const balances = computed<AssetBalanceWithPriceAndChains[]>(() => summarizeBalances([fromExchanges(get(bankBalances))], context));

  const total = computed<BigNumber>(() => get(banks).reduce((sum, bank) => sum.plus(bank.total), Zero));

  return {
    balances,
    banks,
    isBankLocation,
    total,
  };
}
