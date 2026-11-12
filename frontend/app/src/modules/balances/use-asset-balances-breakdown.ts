import type { ComputedRef } from 'vue';
import type { AssetBreakdown } from '@/modules/accounts/blockchain-accounts';
import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';
import { NoPrice } from '@rotki/common';
import { groupAddresses } from '@/modules/accounts/core/account-groups';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import {
  assetBreakdown,
  type BreakdownFilters,
  type BreakdownPorts,
  historicalAssetBreakdown,
  type HistoricalBreakdownPorts,
} from '@/modules/balances/aggregation/core/asset-breakdown';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { useIsHistoryView } from '@/modules/balances/view/balance-view';
import { bankLocationBalances } from '@/modules/banks/bank-balances';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface UseAssetBalancesBreakdownReturn {
  useAssetBreakdown: (asset: string, liabilities?: boolean, filters?: BreakdownFilters) => ComputedRef<AssetBreakdown[]>;
  getAssetBreakdown: (asset: string, liabilities?: boolean, filters?: BreakdownFilters) => AssetBreakdown[];
}

/**
 * Where an asset is held, one row per location and account, in the enclosing page's balance view.
 *
 * @remarks
 * Queried unless the page provided the history view. In the history view, chain rows come from the
 * history buckets and bank rows from the queried bank balances; manual balances and manual
 * liabilities are left out, matching the history totals. Liabilities have no history buckets, so
 * their breakdown stays the queried blockchain one.
 */
export function useAssetBalancesBreakdown(): UseAssetBalancesBreakdownReturn {
  const { bankBalances, exchangeBalances, manualBalances, manualLiabilities, visibleBalances: balances } = storeToRefs(useBalancesStore());
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { entries: historicalEntries } = storeToRefs(useHistoricalSnapshotStore());
  const isHistory = useIsHistoryView();
  const { getEvmChainName, matchChain } = useSupportedChains();
  const { getAssetPrice } = usePriceUtils();
  const resolveIdentifier = useResolveAssetIdentifier();

  const ports: BreakdownPorts = {
    chainLabel: chain => getEvmChainName(chain) ?? chain,
    resolveIdentifier,
  };

  const historicalPorts: HistoricalBreakdownPorts = {
    ...ports,
    matchChain,
    priceOf: (asset: string) => getAssetPrice(asset, NoPrice),
  };

  function queriedBreakdown(asset: string, liabilities: boolean, filters: BreakdownFilters): AssetBreakdown[] {
    const inputs = {
      accounts: get(accounts),
      balances: get(balances),
      exchanges: { ...get(exchangeBalances), ...bankLocationBalances(get(bankBalances)) },
      manual: liabilities ? get(manualLiabilities) : get(manualBalances),
    };
    return assetBreakdown(asset, inputs, liabilities, filters, ports);
  }

  /** History buckets narrowed to the chains and account group the filters ask for. */
  function filteredEntries({ chains = [], groupId }: BreakdownFilters): HistoricalBalanceEntry[] {
    const addresses = groupId ? new Set(groupAddresses(get(accounts), groupId)) : undefined;
    return get(historicalEntries).filter(({ location, locationLabel }) => {
      const chain = matchChain(location);
      if (chains.length > 0 && (chain === undefined || !chains.includes(chain)))
        return false;
      return !addresses || (locationLabel != null && addresses.has(locationLabel));
    });
  }

  function historyBreakdown(asset: string, liabilities: boolean, filters: BreakdownFilters): AssetBreakdown[] {
    const blockchainOnly = { accounts: get(accounts), balances: get(balances), exchanges: {}, manual: [] };
    if (liabilities)
      return assetBreakdown(asset, blockchainOnly, true, filters, ports);

    const chainRows = historicalAssetBreakdown(asset, filteredEntries(filters), historicalPorts);
    if (filters.blockchainOnly || filters.groupId || (filters.chains?.length ?? 0) > 0)
      return chainRows;

    const bankInputs = { accounts: {}, balances: {}, exchanges: bankLocationBalances(get(bankBalances)), manual: [] };
    return [...chainRows, ...assetBreakdown(asset, bankInputs, false, {}, ports)];
  }

  function getAssetBreakdown(asset: string, liabilities: boolean = false, filters: BreakdownFilters = {}): AssetBreakdown[] {
    return get(isHistory)
      ? historyBreakdown(asset, liabilities, filters)
      : queriedBreakdown(asset, liabilities, filters);
  }

  const useAssetBreakdown = (
    asset: string,
    liabilities: boolean = false,
    filters: BreakdownFilters = {},
  ): ComputedRef<AssetBreakdown[]> => computed<AssetBreakdown[]>(() => getAssetBreakdown(asset, liabilities, filters));

  return {
    getAssetBreakdown,
    useAssetBreakdown,
  };
}
