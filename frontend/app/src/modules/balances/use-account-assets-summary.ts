import type { Balances } from '@/types/blockchain/accounts';
import type { AssetBalance, AssetBalanceWithPrice } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useBalanceSorting } from '@/composables/balances/sorting';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useBalancePricesStore } from '@/store/balances/prices';
import { sortDesc } from '@/utils/bignumbers';
import { balanceSum } from '@/utils/calculation';
import { isEmpty } from 'es-toolkit/compat';

interface UseAccountAssetsSummaryReturn {
  useAccountAssets: (chains: Ref<string[]>, address: Ref<string>) => ComputedRef<AssetBalanceWithPrice[]>;
  useAccountTopTokens: (chains: Ref<string[]>, address: Ref<string>) => ComputedRef<AssetBalance[]>;
}

interface SummaryFilters {
  address: string;
  chains: string[];
}

export function useAccountAssetsSummary(): UseAccountAssetsSummaryReturn {
  const { balances } = storeToRefs(useBalancesStore());
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { assetPrice } = useBalancePricesStore();
  const { toSortedAssetBalanceWithPrice } = useBalanceSorting();
  const { assetAssociationMap, assetInfo } = useAssetInfoRetrieval();

  function summarizeAssetsForAddress(
    balances: Balances,
    filters: SummaryFilters,
    associationMap: Record<string, string>,
    getGroup?: (identifier: string) => string,
  ): Record<string, AssetBalance> {
    const { address, chains } = filters;
    const assets: Record<string, AssetBalance> = {};

    for (const chain of chains) {
      const chainBalances = balances[chain];
      if (!chainBalances || isEmpty(chainBalances))
        continue;

      const addressBalances = chainBalances[address];
      if (!addressBalances)
        continue;

      const addressAssets = addressBalances.assets;
      if (!addressAssets || isEmpty(addressAssets))
        continue;

      for (const [assetIdentifier, balance] of Object.entries(addressAssets)) {
        const identifier = associationMap?.[assetIdentifier] ?? assetIdentifier;
        if (isAssetIgnored(identifier))
          continue;

        const key = getGroup?.(identifier) ?? identifier;

        if (assets[key]) {
          const { asset, ...oldBalance } = assets[key];
          assets[key] = {
            asset,
            ...balanceSum(oldBalance, balance),
          };
        }
        else {
          assets[key] = {
            asset: identifier,
            ...balance,
          };
        }
      }
    }
    return assets;
  }

  const getAccountAssets = (
    balances: Balances,
    chains: string[],
    address: string,
    assetAssociationMap: Record<string, string>,
  ): AssetBalanceWithPrice[] => {
    const assets = summarizeAssetsForAddress(
      balances,
      { address, chains },
      assetAssociationMap,
    );
    return toSortedAssetBalanceWithPrice(get(assets), asset => isAssetIgnored(asset), assetPrice);
  };

  const getAccountTopTokens = (
    balances: Balances,
    filters: SummaryFilters,
    assetAssociationMap: Record<string, string>,
  ): AssetBalance[] => {
    const { address, chains } = filters;

    const topAssets = summarizeAssetsForAddress(
      balances,
      { address, chains },
      assetAssociationMap,
      (asset) => {
        const info = get(assetInfo(asset));
        return info?.collectionId ? `collection-${info.collectionId}` : asset;
      },
    );

    return Object.values(topAssets)
      .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
  };

  const useAccountAssets = (
    chains: Ref<string[]>,
    address: Ref<string>,
  ): ComputedRef<AssetBalanceWithPrice[]> => computed(() => getAccountAssets(
    get(balances),
    get(chains),
    get(address),
    get(assetAssociationMap),
  ));

  const useAccountTopTokens = (
    chains: Ref<string[]>,
    address: Ref<string>,
  ): ComputedRef<AssetBalance[]> => computed(() => getAccountTopTokens(
    get(balances),
    {
      address: get(address),
      chains: get(chains),
    },
    get(assetAssociationMap),
  ));

  return {
    useAccountAssets,
    useAccountTopTokens,
  };
}
