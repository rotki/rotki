<script lang="ts" setup>
import type { AssetBalance } from '@rotki/common';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { topTokens, xpubNativeHolding } from '@/modules/accounts/core/account-assets';
import IconTokenDisplay from '@/modules/accounts/IconTokenDisplay.vue';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import AssetIcon from '@/modules/shell/components/AssetIcon.vue';

const { chains, opensDetails = false, row } = defineProps<{
  chains: string[];
  row: BlockchainAccountBalance;
  /** The "+N" count opens the account's details, where every asset is listed. */
  opensDetails?: boolean;
}>();

const emit = defineEmits<{
  'open-details': [];
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
  >
    <template
      v-if="opensDetails"
      #more="{ hidden, label }"
    >
      <button
        type="button"
        class="rounded px-1 -mx-1 cursor-pointer hover:bg-rui-hover hover:text-rui-text focus-visible:outline-2 focus-visible:outline-rui-primary"
        :title="label"
        :aria-label="label"
        data-testid="top-asset-count"
        data-account-details-opener
        @click.stop="emit('open-details')"
      >
        +{{ hidden }}
      </button>
    </template>
  </IconTokenDisplay>
  <div
    v-else-if="assets.length === 1"
    class="flex items-center justify-end text-body-2"
  >
    <AssetIcon
      :identifier="assets[0].asset"
      :resolution-options="{ collectionParent: false }"
      size="24px"
      padding="0px"
      class="cursor-pointer"
      @click="navigateToAsset(assets[0])"
    />
    <span class="ml-1.5 min-w-8 text-start whitespace-nowrap">
      <ValueDisplay :value="assets[0].amount" />
    </span>
  </div>
</template>
