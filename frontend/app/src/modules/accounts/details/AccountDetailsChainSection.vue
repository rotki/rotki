<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AccountDetailsAssets from '@/modules/accounts/details/AccountDetailsAssets.vue';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBlockchainBalanceStaleness } from '@/modules/balances/use-blockchain-balance-staleness';
import { bigNumberSum } from '@/modules/core/common/data/calculation';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';

const selected = defineModel<string[] | undefined>('selected', { required: true });

const { chain, groupId, selectionMode = false } = defineProps<{
  chain: string;
  groupId: string;
  selectionMode?: boolean;
}>();

/** Assets listed per chain before the rest are asked for, so a big chain does not bury the next. */
const CHAIN_ASSET_LIMIT = 10;

const { t } = useI18n({ useScope: 'global' });

const { getChainName } = useSupportedChains();
const { useBlockchainBalances } = useAggregatedBalances();
const { lastRefreshed, lastRefreshTimestamp } = useBlockchainBalanceStaleness(() => chain);

const chains = computed<string[]>(() => [chain]);
const assets = useBlockchainBalances(chains, () => groupId);

const value = computed<BigNumber>(() => bigNumberSum(get(assets).map(asset => asset.value)));
</script>

<template>
  <section
    class="flex flex-col gap-2"
    :data-testid="`account-details-chain-${chain}`"
  >
    <header class="flex items-center gap-2">
      <ChainIcon
        :chain="chain"
        size="20px"
      />
      <span class="font-medium">{{ getChainName(chain) }}</span>
      <span
        class="text-caption text-rui-text-secondary"
        data-testid="account-details-chain-age"
      >
        {{ lastRefreshTimestamp ? lastRefreshed : t('account_balances.staleness.never') }}
      </span>
      <FiatDisplay
        :value="value"
        class="ml-auto font-medium"
      />
    </header>
    <AccountDetailsAssets
      v-model:selected="selected"
      :group-id="groupId"
      :chains="chains"
      :selection-mode="selectionMode"
      :limit="CHAIN_ASSET_LIMIT"
    />
  </section>
</template>
