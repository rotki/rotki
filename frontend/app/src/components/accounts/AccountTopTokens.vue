<script lang="ts" setup>
import type { AssetBalance } from '@/types/balances';

const props = defineProps<{
  chains: string[];
  address: string;
  loading: boolean;
}>();

const { getAccountDetails } = useBlockchainStore();
const { assetInfo } = useAssetInfoRetrieval();

const assets = computed<AssetBalance[]>(() => {
  const assets: Record<string, AssetBalance> = {};
  const address = props.address;

  props.chains.forEach((chain) => {
    const details = getAccountDetails(chain, address);
    details.assets.forEach((item) => {
      const assetId = item.asset;
      const info = get(assetInfo(assetId));
      const key = info?.collectionId ? `collection-${info.collectionId}` : assetId;

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

  return Object.values(assets).sort((a, b) => sortDesc(a.value, b.value));
});
</script>

<template>
  <IconTokenDisplay
    :assets="assets"
    :loading="loading"
  />
</template>
