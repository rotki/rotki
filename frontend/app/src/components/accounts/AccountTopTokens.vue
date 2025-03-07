<script lang="ts" setup>
import type { BlockchainAccountBalance } from '@/types/blockchain/accounts';
import type { AssetBalance } from '@rotki/common';
import IconTokenDisplay from '@/components/accounts/IconTokenDisplay.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useBlockchainStore } from '@/store/blockchain';
import { sortDesc } from '@/utils/bignumbers';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { balanceSum } from '@/utils/calculation';

const props = defineProps<{
  chains: string[];
  row: BlockchainAccountBalance;
  loading: boolean;
}>();

const { getAccountDetails } = useBlockchainStore();
const { assetInfo } = useAssetInfoRetrieval();

const assets = computed<AssetBalance[]>(() => {
  const row = props.row;
  const address = getAccountAddress(row);

  if (row.data.type === 'xpub' && row.nativeAsset) {
    return [
      {
        amount: row.amount || Zero,
        asset: row.nativeAsset,
        usdValue: row.usdValue,
      },
    ];
  }

  const assets: Record<string, AssetBalance> = {};
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

  return Object.values(assets).sort((a, b) => sortDesc(a.usdValue, b.usdValue));
});

const router = useRouter();

async function navigateToAsset(asset: AssetBalance) {
  await router.push({
    name: '/assets/[identifier]',
    params: {
      identifier: asset.asset,
    },
  });
}
</script>

<template>
  <IconTokenDisplay
    v-if="assets.length > 1"
    :assets="assets"
    :loading="loading"
  />
  <div
    v-else-if="assets.length === 1"
    class="flex items-center gap-3 justify-end"
  >
    <AmountDisplay :value="assets[0].amount" />
    <AssetIcon
      flat
      :identifier="assets[0].asset"
      :resolution-options="{ collectionParent: false }"
      size="30px"
      padding="1px"
      class="[&_.icon-bg]:!rounded-full [&_.icon-bg]:!overflow-hidden"
      @click="navigateToAsset(assets[0])"
    />
  </div>
</template>
