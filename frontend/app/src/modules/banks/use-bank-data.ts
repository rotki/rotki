import type { ComputedRef } from 'vue';
import { type AssetBalanceWithPriceAndChains, type BigNumber, Zero } from '@rotki/common';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { fromExchanges } from '@/modules/balances/aggregation/core/sources';
import { summarizeBalances } from '@/modules/balances/aggregation/core/summarize';
import { useAggregationContext } from '@/modules/balances/aggregation/use-aggregation-context';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { exchangeAssetSum } from '@/modules/core/common/data/calculation';

export interface BankBalanceData {
  readonly connector: string;
  readonly name: string;
  readonly balances: AssetBalanceWithPriceAndChains[];
  readonly total: BigNumber;
}

interface UseBankDataReturn {
  /** Connected banks with their own holdings, richest first. */
  banks: ComputedRef<BankBalanceData[]>;
  /** What all banks hold together, ignored assets left out. */
  total: ComputedRef<BigNumber>;
}

/** Builds the bank page from connection-level balances rather than the aggregate location. */
export function useBankData(): UseBankDataReturn {
  const { connectionBalances } = storeToRefs(useBankConnectionsStore());
  const { isAssetIgnored } = useAssetsStore();
  const context = useAggregationContext();

  const banks = computed<BankBalanceData[]>(() => get(connectionBalances)
    .map(({ balances, connector, name }) => ({
      balances: summarizeBalances([fromExchanges({ [name]: balances })], context),
      connector,
      name,
      total: exchangeAssetSum(balances, isAssetIgnored),
    }))
    .sort((a, b) => sortDesc(a.total, b.total)));

  const total = computed<BigNumber>(() => get(banks).reduce((sum, bank) => sum.plus(bank.total), Zero));

  return {
    banks,
    total,
  };
}
