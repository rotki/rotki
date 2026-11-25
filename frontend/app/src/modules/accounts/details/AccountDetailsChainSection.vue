<script setup lang="ts">
import AccountDetailsAssets from '@/modules/accounts/details/AccountDetailsAssets.vue';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useBlockchainBalanceStaleness } from '@/modules/balances/use-blockchain-balance-staleness';
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
const { lastRefreshed, lastRefreshTimestamp } = useBlockchainBalanceStaleness(() => chain);

const chains = computed<string[]>(() => [chain]);
</script>

<template>
  <section :data-testid="`account-details-chain-${chain}`">
    <AccountDetailsAssets
      v-model:selected="selected"
      :group-id="groupId"
      :chains="chains"
      :selection-mode="selectionMode"
      :limit="CHAIN_ASSET_LIMIT"
    >
      <template #header="{ value }">
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
      </template>
    </AccountDetailsAssets>
  </section>
</template>
