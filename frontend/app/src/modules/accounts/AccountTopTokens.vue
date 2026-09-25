<script lang="ts" setup>
import type { AssetBalance } from '@rotki/common';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { topTokens, xpubNativeHolding } from '@/modules/accounts/core/account-assets';
import IconTokenDisplay from '@/modules/accounts/IconTokenDisplay.vue';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';

const { chains, row, loading } = defineProps<{
  chains: string[];
  row: BlockchainAccountBalance;
  loading: boolean;
}>();

const { useBlockchainBalances } = useAggregatedBalances();
const router = useRouter();

const address = computed<string>(() => getAccountAddress(row));
const balances = useBlockchainBalances(() => chains, address);

const assets = computed<AssetBalance[]>(() => {
  const native = xpubNativeHolding(row);
  return native ? [native] : topTokens(get(balances));
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
