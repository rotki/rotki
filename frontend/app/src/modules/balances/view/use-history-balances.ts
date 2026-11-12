import type { AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import { type AssetBalanceWithPriceAndChains, type BigNumber, Zero } from '@rotki/common';
import { fromBlockchain, fromExchanges, fromManual } from '@/modules/balances/aggregation/core/sources';
import { summarizeBalances } from '@/modules/balances/aggregation/core/summarize';
import { useAggregationContext } from '@/modules/balances/aggregation/use-aggregation-context';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useHistoricalBalanceSource } from '@/modules/balances/use-historical-balance-source';
import { bankLocationBalances } from '@/modules/banks/bank-balances';

interface UseHistoryBalancesReturn {
  /** History-derived chain and exchange balances, plus queried bank balances. */
  getBalances: (groupCollections?: boolean) => AssetBalanceWithPriceAndChains[];
  /** Queried blockchain liabilities; history has none of its own, and manual ones are left out. */
  getLiabilities: () => AssetBalanceWithPriceAndChains[];
  /** Manual balances on their own, so a gap they explain can be attributed to them. */
  getManualBalances: (groupCollections?: boolean) => AssetBalanceWithPriceAndChains[];
  /** Manual balances minus manual liabilities, in the main currency. */
  getManualNetValue: () => BigNumber;
}

function sumValues(rows: readonly AssetBalanceWithPriceAndChains[]): BigNumber {
  return rows.reduce((sum, row) => sum.plus(row.value), Zero);
}

/**
 * Balances as the history view shows them.
 *
 * @remarks
 * History derives chain and exchange balances from events. Bank balances and blockchain liabilities
 * have no events behind them, so they are carried through from the queried side unchanged. Manual
 * balances are left out entirely: a user who tracks a wallet manually and also records its events
 * would otherwise count it twice.
 */
export function useHistoryBalances(): UseHistoryBalancesReturn {
  const context = useAggregationContext();
  const { source } = useHistoricalBalanceSource(context);
  const { bankBalances, manualBalances, manualLiabilities, visibleBalances } = storeToRefs(useBalancesStore());

  const bankAssets = computed<AssetBalanceEntries>(() => fromExchanges(bankLocationBalances(get(bankBalances))));
  const blockchainLiabilities = computed<AssetBalanceEntries>(() => fromBlockchain(get(visibleBalances), { key: 'liabilities' }));
  const manualAssets = computed<AssetBalanceEntries>(() => fromManual(get(manualBalances)));
  const manualLiabilityEntries = computed<AssetBalanceEntries>(() => fromManual(get(manualLiabilities)));

  function getBalances(groupCollections = true): AssetBalanceWithPriceAndChains[] {
    return summarizeBalances([get(source), get(bankAssets)], context, { groupCollections });
  }

  function getLiabilities(): AssetBalanceWithPriceAndChains[] {
    return summarizeBalances([get(blockchainLiabilities)], context);
  }

  function getManualBalances(groupCollections = true): AssetBalanceWithPriceAndChains[] {
    return summarizeBalances([get(manualAssets)], context, { groupCollections });
  }

  function getManualNetValue(): BigNumber {
    return sumValues(getManualBalances()).minus(sumValues(summarizeBalances([get(manualLiabilityEntries)], context)));
  }

  return { getBalances, getLiabilities, getManualBalances, getManualNetValue };
}
