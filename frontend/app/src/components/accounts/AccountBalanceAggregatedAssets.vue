<script lang="ts" setup>
import { isEvmNativeToken } from '@/types/asset';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import type { AssetBalance, AssetBalanceWithPrice } from '@rotki/common';

const props = defineProps<{
  groupId: string;
  chains: string[];
}>();

const { groupId, chains } = toRefs(props);
const blockchainStore = useBlockchainStore();
const { getAccountDetails } = blockchainStore;
const { balances } = storeToRefs(blockchainStore);

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

const evmNativeTokenBreakdowns = computed(() => {
  const balanceData = get(balances);
  const nativeTokenBreakdowns: Record<string, AssetBreakdown[]> = {};

  get(assets).forEach((item) => {
    const asset = item.asset;
    if (isEvmNativeToken(asset)) {
      const address = get(groupId);

      const breakdownPerAsset: AssetBreakdown[] = [];

      get(chains).forEach((chain) => {
        const chainBalanceData = balanceData[chain];

        if (!chainBalanceData)
          return;

        const assetBalance = chainBalanceData[address]?.assets?.[asset];

        if (!assetBalance)
          return;

        breakdownPerAsset.push({
          address,
          location: chain,
          ...assetBalance,
        });
      });

      if (breakdownPerAsset.length > 0)
        nativeTokenBreakdowns[asset] = breakdownPerAsset;
    }
  });

  return nativeTokenBreakdowns;
});
</script>

<template>
  <AssetBalances
    class="bg-white dark:bg-[#1E1E1E]"
    :balances="assets"
    :evm-native-token-breakdowns="evmNativeTokenBreakdowns"
  />
</template>
