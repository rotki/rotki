<script lang="ts" setup>
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { type AssetBalance, Zero } from '@rotki/common';
import { pick } from 'es-toolkit';
import IconTokenDisplay from '@/components/accounts/IconTokenDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { getAccountAddress, isXpubAccount } from '@/modules/accounts/account-utils';
import { ValueDisplay } from '@/modules/amount-display/components';
import { sortDesc } from '@/modules/common/data/bignumbers';

const { chains, row, loading } = defineProps<{
  chains: string[];
  row: BlockchainAccountBalance;
  loading: boolean;
}>();

const { useBlockchainBalances } = useAggregatedBalances();
const router = useRouter();

const address = computed<string>(() => getAccountAddress(row));
const balances = useBlockchainBalances(() => chains, address);

const topTokens = computed<AssetBalance[]>(() => get(balances)
  .map(balance => pick(balance, ['asset', 'amount', 'value']))
  .sort((a, b) => sortDesc(a.value, b.value)));

const assets = computed<AssetBalance[]>(() => {
  if (isXpubAccount(row) && row.nativeAsset) {
    return [{
      amount: row.amount || Zero,
      asset: row.nativeAsset,
      value: row.value,
    }];
  }
  return get(topTokens);
});

async function navigateToAsset(asset: AssetBalance): Promise<void> {
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
    <ValueDisplay :value="assets[0].amount" />
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
