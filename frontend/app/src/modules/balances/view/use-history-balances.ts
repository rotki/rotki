import type { AssetBalanceWithPriceAndChains, BigNumber } from '@rotki/common';
import type { AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import { fromBlockchain, fromExchanges, fromManual } from '@/modules/balances/aggregation/core/sources';
import { summarizeBalances } from '@/modules/balances/aggregation/core/summarize';
import { useAggregationContext } from '@/modules/balances/aggregation/use-aggregation-context';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useHistoricalBalanceSource } from '@/modules/balances/use-historical-balance-source';
import { sumValues } from '@/modules/balances/view/history-comparison';
import { bankLocationBalances } from '@/modules/banks/bank-balances';

interface UseHistoryBalancesReturn {
  /** History-derived chain and exchange balances, plus queried bank balances. */
  getBalances: (groupCollections?: boolean) => AssetBalanceWithPriceAndChains[];
  /** History-derived debt-token liabilities plus queried non-token protocol liabilities. */
  getLiabilities: () => AssetBalanceWithPriceAndChains[];
  /** Manual balances on their own, so a gap they explain can be attributed to them. */
  getManualBalances: (groupCollections?: boolean) => AssetBalanceWithPriceAndChains[];
  /** Manual liabilities on their own, so a liability gap they explain can be attributed to them. */
  getManualLiabilities: () => AssetBalanceWithPriceAndChains[];
  /** Manual balances minus manual liabilities, in the main currency. */
  getManualNetValue: () => BigNumber;
}

/**
 * Balances as the history view shows them.
 *
 * @remarks
 * History derives chain and exchange balances (including ERC-20 debt tokens) from events. Bank
 * balances and non-token protocol liabilities (e.g. Maker vaults, Liquity debt) have no events
 * behind them, so they are carried through from the queried side unchanged. Debt tokens are never
 * filled in from live balances, even when history has no positive bucket for them, so missing or
 * zeroed debt buckets surface as gaps. Manual balances are left out entirely: a user who tracks a
 * wallet manually and also records its events would otherwise count it twice.
 */
export function useHistoryBalances(): UseHistoryBalancesReturn {
  const context = useAggregationContext();
  const { isTrackedLiability, liabilitySource, source } = useHistoricalBalanceSource(context);
  const { bankBalances, manualBalances, manualLiabilities, visibleBalances } = storeToRefs(useBalancesStore());

  const bankAssets = computed<AssetBalanceEntries>(() => fromExchanges(bankLocationBalances(get(bankBalances))));
  const blockchainLiabilities = computed<AssetBalanceEntries>(() => fromBlockchain(get(visibleBalances), { key: 'liabilities' }));
  const fallbackLiabilities = computed<AssetBalanceEntries>(() => {
    const live = get(blockchainLiabilities);
    const entries: AssetBalanceEntries = {};
    for (const [asset, protocols] of Object.entries(live)) {
      if (!isTrackedLiability(asset))
        entries[asset] = protocols;
    }
    return entries;
  });
  const manualAssets = computed<AssetBalanceEntries>(() => fromManual(get(manualBalances)));
  const manualLiabilityEntries = computed<AssetBalanceEntries>(() => fromManual(get(manualLiabilities)));

  function getBalances(groupCollections = true): AssetBalanceWithPriceAndChains[] {
    return summarizeBalances([get(source), get(bankAssets)], context, { groupCollections });
  }

  function getLiabilities(): AssetBalanceWithPriceAndChains[] {
    return summarizeBalances([get(liabilitySource), get(fallbackLiabilities)], context);
  }

  function getManualBalances(groupCollections = true): AssetBalanceWithPriceAndChains[] {
    return summarizeBalances([get(manualAssets)], context, { groupCollections });
  }

  function getManualLiabilities(): AssetBalanceWithPriceAndChains[] {
    return summarizeBalances([get(manualLiabilityEntries)], context);
  }

  function getManualNetValue(): BigNumber {
    return sumValues(getManualBalances()).minus(sumValues(getManualLiabilities()));
  }

  return { getBalances, getLiabilities, getManualBalances, getManualLiabilities, getManualNetValue };
}
