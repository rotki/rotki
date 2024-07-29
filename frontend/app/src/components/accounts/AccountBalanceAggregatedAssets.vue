<script lang="ts" setup>
import type { AssetBalance, AssetBalanceWithPrice } from '@rotki/common';

const props = defineProps<{
  groupId: string;
  chains: string[];
}>();

const { groupId, chains } = toRefs(props);
const { getAccountDetails } = useBlockchainStore();

const { isAssetIgnored } = useIgnoredAssetsStore();
const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
const { assetPrice } = useBalancePricesStore();
const { toSortedAssetBalanceWithPrice } = useBalanceSorting();

const assets = computed<AssetBalanceWithPrice[]>(() => {
  const address = get(groupId);

  const assets: Record<string, AssetBalance> = {};

  get(chains).forEach((chain) => {
    const details = getAccountDetails(chain, address);
    details.assets.forEach((item) => {
      const key = item.asset;
      if (assets[key]) {
        assets[key] = {
          ...assets[key],
          ...balanceSum(assets[key], item),
        };
      }
      else {
        assets[key] = item;
      }
    });
  });

  const ownedAssets = mergeAssociatedAssets(assets, getAssociatedAssetIdentifier);
  return toSortedAssetBalanceWithPrice(get(ownedAssets), asset => get(isAssetIgnored(asset)), assetPrice);
});
</script>

<template>
  <AssetBalances
    class="bg-white dark:bg-[#1E1E1E]"
    :balances="assets"
  />
</template>
