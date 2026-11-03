import type { ComputedRef } from 'vue';
import type { BankAccountBalance, BankConnection, BankConnectionBalances } from '@/modules/banks/types';
import { type AssetBalanceWithPriceAndChains, type BigNumber, Zero } from '@rotki/common';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { fromExchanges } from '@/modules/balances/aggregation/core/sources';
import { summarizeBalances } from '@/modules/balances/aggregation/core/summarize';
import { useAggregationContext } from '@/modules/balances/aggregation/use-aggregation-context';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { bankLocationBalances, isSameConnection } from '@/modules/banks/bank-balances';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { exchangeAssetSum } from '@/modules/core/common/data/calculation';

export interface BankBalanceData extends BankConnection {
  readonly balances: AssetBalanceWithPriceAndChains[];
  /** The bank's accounts, richest first, leaving out those holding an ignored asset. */
  readonly accounts: BankAccountBalance[];
  readonly total: BigNumber;
}

interface UseBankDataReturn {
  /**
   * Every bank connection with its own holdings, richest first.
   *
   * @remarks
   * Driven by the connections rather than the balances, so a connection that has not reported a
   * balance yet, such as one waiting on a TAN, is still listed, holding nothing.
   */
  banks: ComputedRef<BankBalanceData[]>;
  /** What all banks hold together, one row per asset. */
  allBalances: ComputedRef<AssetBalanceWithPriceAndChains[]>;
  /** What all banks hold together, ignored assets left out; the sum of the banks' totals. */
  total: ComputedRef<BigNumber>;
}

/** The bank pages' view of the bank balances, per connection and all together. */
export function useBankData(): UseBankDataReturn {
  const { connections } = storeToRefs(useBankConnectionsStore());
  const { bankBalances } = storeToRefs(useBalancesStore());
  const { isAssetIgnored } = useAssetsStore();
  const context = useAggregationContext();

  const summarize = (entries: readonly BankConnectionBalances[]): AssetBalanceWithPriceAndChains[] =>
    summarizeBalances([fromExchanges(bankLocationBalances(entries))], context);

  const banks = computed<BankBalanceData[]>(() => get(connections)
    .map((connection) => {
      const entry = get(bankBalances).find(balances => isSameConnection(balances, connection));
      return {
        ...connection,
        accounts: (entry?.accounts ?? [])
          .filter(account => !isAssetIgnored(account.asset))
          .sort((a, b) => sortDesc(a.value, b.value)),
        balances: entry ? summarize([entry]) : [],
        total: entry ? exchangeAssetSum(entry.balances, isAssetIgnored) : Zero,
      };
    })
    .sort((a, b) => sortDesc(a.total, b.total)));

  const allBalances = computed<AssetBalanceWithPriceAndChains[]>(() => summarize(get(bankBalances)));

  const total = computed<BigNumber>(() => get(banks).reduce((sum, bank) => sum.plus(bank.total), Zero));

  return {
    allBalances,
    banks,
    total,
  };
}
