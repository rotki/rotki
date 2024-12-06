<script lang="ts" setup>
import { balanceSum } from '@/utils/calculation';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useBlockchainStore } from '@/store/blockchain';
import { useBalanceSorting } from '@/composables/balances/sorting';
import AssetBalances from '@/components/AssetBalances.vue';
import type { AssetBalance, AssetBalanceWithPrice } from '@rotki/common';

const props = defineProps<{
  groupId: string;
  chains: string[];
}>();

const { chains, groupId } = toRefs(props);
const { getAccountDetails } = useBlockchainStore();

const { isAssetIgnored } = useIgnoredAssetsStore();
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

  return toSortedAssetBalanceWithPrice(get(assets), asset => get(isAssetIgnored(asset)), assetPrice);
});
</script>

<template>
  <AssetBalances
    class="bg-white dark:bg-[#1E1E1E]"
    :balances="assets"
    :details="{
      groupId,
      chains,
    }"
  />
</template>
