<script setup lang="ts">
import { Blockchain, HistoryEventEntryType } from '@rotki/common';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import StakingLocationTitle from '@/modules/staking/components/StakingLocationTitle.vue';
import StakingRefreshActions from '@/modules/staking/components/StakingRefreshActions.vue';
import LiquityPools from '@/modules/staking/liquity/LiquityPools.vue';
import LiquityProxyInformation from '@/modules/staking/liquity/LiquityProxyInformation.vue';
import LiquityStake from '@/modules/staking/liquity/LiquityStake.vue';
import LiquityStatistics from '@/modules/staking/liquity/LiquityStatistics.vue';
import { useLiquityStakingDetails } from '@/modules/staking/liquity/use-liquity-staking-details';

defineProps<{
  syncingHistory: boolean;
  /** The chain the history sync queries, named in its menu entry. */
  chainName: string;
}>();

const emit = defineEmits<{
  'refresh': [];
  'sync-history': [];
}>();

defineSlots<{
  modules: () => any;
}>();

const chains = [Blockchain.ETH];

const { t } = useI18n({ useScope: 'global' });

const {
  accountFilter,
  aggregatedStake,
  aggregatedStakingPool,
  aggregatedStatistic,
  availableAddresses,
  loading,
  modelSelectedAccounts,
  proxyInformation,
} = useLiquityStakingDetails();
</script>

<template>
  <TablePageLayout child>
    <template #title>
      <StakingLocationTitle location="liquity" />
    </template>
    <template #buttons>
      <StakingRefreshActions
        :refreshing="loading"
        :syncing-history="syncingHistory"
        :chain-name="chainName"
        :tooltip="t('liquity_staking_details.refresh_tooltip')"
        test-id-prefix="liquity"
        @refresh="emit('refresh')"
        @sync-history="emit('sync-history')"
      >
        <slot name="modules" />
      </StakingRefreshActions>
    </template>
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <BlockchainAccountSelector
        v-model="modelSelectedAccounts"
        class="w-full sm:w-80"
        label-placement="hidden"
        :placeholder="t('liquity_staking_details.all_accounts')"
        :source="{ chains, usableAddresses: availableAddresses }"
        :field="{ dense: true, label: t('liquity_staking_details.select_account') }"
      />

      <LiquityProxyInformation
        v-if="proxyInformation"
        :proxy-information="proxyInformation"
      />
    </div>

    <div class="grid md:grid-cols-2 gap-4">
      <LiquityPools
        class="flex-1"
        :pool="aggregatedStakingPool"
      />
      <LiquityStake
        class="flex-1"
        :stake="aggregatedStake"
      />
    </div>

    <LiquityStatistics
      :statistic="aggregatedStatistic"
      :pool="aggregatedStakingPool"
    />

    <HistoryEventsView
      :section-title="t('common.events')"
      :restrictions="{
        entryTypes: [HistoryEventEntryType.EVM_EVENT],
        externalAccounts: accountFilter,
        onlyChains: chains,
        protocols: ['liquity'],
      }"
    />
  </TablePageLayout>
</template>
