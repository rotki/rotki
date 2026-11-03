import type { ComputedRef } from 'vue';
import type { BankAccountBalance, BankConnection, BankConnectionBalances } from '@/modules/banks/types';
import { type AssetBalanceWithPriceAndChains, type BigNumber, Zero } from '@rotki/common';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { fromExchanges } from '@/modules/balances/aggregation/core/sources';
import { summarizeBalances } from '@/modules/balances/aggregation/core/summarize';
import { useAggregationContext } from '@/modules/balances/aggregation/use-aggregation-context';
import { aggregateConnectionBalances } from '@/modules/banks/bank-balances';
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
  /** What all banks hold together, ignored assets left out. */
  total: ComputedRef<BigNumber>;
}

/** Builds the bank page from connection-level balances rather than the aggregate location. */
export function useBankData(): UseBankDataReturn {
  const { connectionBalances, connections } = storeToRefs(useBankConnectionsStore());
  const { isAssetIgnored } = useAssetsStore();
  const context = useAggregationContext();

  /**
   * One row per asset of the given connections.
   *
   * @remarks
   * Every connection counts as the one `banks` source: keyed by connection name, a row held at
   * several banks would expand into a per-protocol breakdown that renders bank names as protocols.
   * The tiles already show what each bank holds.
   */
  const summarize = (entries: readonly BankConnectionBalances[]): AssetBalanceWithPriceAndChains[] =>
    summarizeBalances([fromExchanges({ banks: aggregateConnectionBalances(entries) })], context);

  const banks = computed<BankBalanceData[]>(() => get(connections)
    .map((connection) => {
      const entry = get(connectionBalances).find(({ connector, name }) => connector === connection.connector && name === connection.name);
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

  const allBalances = computed<AssetBalanceWithPriceAndChains[]>(() => summarize(get(connectionBalances)));

  const total = computed<BigNumber>(() => get(connectionBalances)
    .reduce((sum, { balances }) => sum.plus(exchangeAssetSum(balances, isAssetIgnored)), Zero));

  return {
    allBalances,
    banks,
    total,
  };
}
