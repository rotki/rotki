import type { ComputedRef } from 'vue';
import type { AssetBreakdown } from '@/modules/accounts/blockchain-accounts';
import { NoPrice } from '@rotki/common';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import { assetBreakdown, type BreakdownFilters, type BreakdownPorts, historicalAssetBreakdown, type HistoricalBreakdownPorts } from '@/modules/balances/aggregation/core/asset-breakdown';
import { useBalanceDisplayModeStore } from '@/modules/balances/use-balance-display-mode-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { bankLocationBalances } from '@/modules/banks/bank-balances';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface UseAssetBalancesBreakdownReturn {
  useAssetBreakdown: (asset: string, liabilities?: boolean, filters?: BreakdownFilters) => ComputedRef<AssetBreakdown[]>;
  getAssetBreakdown: (asset: string, liabilities?: boolean, filters?: BreakdownFilters) => AssetBreakdown[];
}

export function useAssetBalancesBreakdown(): UseAssetBalancesBreakdownReturn {
  const { bankBalances, exchangeBalances, manualBalances, manualLiabilities, visibleBalances: balances } = storeToRefs(useBalancesStore());
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { isHistoryMode, entries: historicalEntries } = storeToRefs(useBalanceDisplayModeStore());
  const { getEvmChainName, matchChain } = useSupportedChains();
  const { getAssetPrice } = usePriceUtils();
  const resolveIdentifier = useResolveAssetIdentifier();

  const ports: BreakdownPorts = {
    chainLabel: chain => getEvmChainName(chain) ?? chain,
    resolveIdentifier,
  };

  const historicalPorts: HistoricalBreakdownPorts = {
    chainLabel: ports.chainLabel,
    matchChain,
    priceOf: (asset: string) => getAssetPrice(asset, NoPrice),
    resolveIdentifier,
  };

  function getAssetBreakdown(asset: string, liabilities: boolean = false, filters: BreakdownFilters = {}): AssetBreakdown[] {
    if (get(isHistoryMode))
      return historicalAssetBreakdown(asset, get(historicalEntries), historicalPorts);

    const inputs = {
      accounts: get(accounts),
      balances: get(balances),
      exchanges: { ...get(exchangeBalances), ...bankLocationBalances(get(bankBalances)) },
      manual: liabilities ? get(manualLiabilities) : get(manualBalances),
    };
    return assetBreakdown(asset, inputs, liabilities, filters, ports);
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
