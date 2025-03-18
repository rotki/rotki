<script lang="ts" setup>
import type { BlockchainAccountBalance } from '@/types/blockchain/accounts';
import IconTokenDisplay from '@/components/accounts/IconTokenDisplay.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useAccountAssetsSummary } from '@/modules/balances/use-account-assets-summary';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { type AssetBalance, Zero } from '@rotki/common';

const props = defineProps<{
  chains: string[];
  row: BlockchainAccountBalance;
  loading: boolean;
}>();

const { chains } = toRefs(props);
const { useAccountTopTokens } = useAccountAssetsSummary();
const router = useRouter();

const address = computed<string>(() => getAccountAddress(props.row));
const topTokens = useAccountTopTokens(chains, address);

const assets = computed<AssetBalance[]>(() => {
  const row = props.row;
  if (row.data.type === 'xpub' && row.nativeAsset) {
    return [{
      amount: row.amount || Zero,
      asset: row.nativeAsset,
      usdValue: row.usdValue,
    }];
  }
  return get(topTokens);
});

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
