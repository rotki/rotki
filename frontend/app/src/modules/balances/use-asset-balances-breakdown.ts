import type { ComputedRef } from 'vue';
import type { AssetBreakdown } from '@/modules/accounts/blockchain-accounts';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import { assetBreakdown, type BreakdownFilters, type BreakdownPorts } from '@/modules/balances/aggregation/core/asset-breakdown';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface UseAssetBalancesBreakdownReturn {
  useAssetBreakdown: (asset: string, liabilities?: boolean, filters?: BreakdownFilters) => ComputedRef<AssetBreakdown[]>;
  getAssetBreakdown: (asset: string, liabilities?: boolean, filters?: BreakdownFilters) => AssetBreakdown[];
}

export function useAssetBalancesBreakdown(): UseAssetBalancesBreakdownReturn {
  const { balances, exchangeBalances, manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { getEvmChainName } = useSupportedChains();

  const ports: BreakdownPorts = {
    chainLabel: chain => getEvmChainName(chain) ?? chain,
    resolveIdentifier: useResolveAssetIdentifier(),
  };

  function getAssetBreakdown(asset: string, liabilities: boolean = false, filters: BreakdownFilters = {}): AssetBreakdown[] {
    const inputs = {
      accounts: get(accounts),
      balances: get(balances),
      exchanges: get(exchangeBalances),
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
