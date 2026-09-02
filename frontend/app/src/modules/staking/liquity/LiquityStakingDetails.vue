<script setup lang="ts">
import { Blockchain, HistoryEventEntryType } from '@rotki/common';
import BlockchainAccountSelector from '@/modules/accounts/BlockchainAccountSelector.vue';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import LiquityPools from '@/modules/staking/liquity/LiquityPools.vue';
import LiquityProxyInformation from '@/modules/staking/liquity/LiquityProxyInformation.vue';
import LiquityStake from '@/modules/staking/liquity/LiquityStake.vue';
import LiquityStatistics from '@/modules/staking/liquity/LiquityStatistics.vue';
import { useLiquityStakingDetails } from '@/modules/staking/liquity/use-liquity-staking-details';

const emit = defineEmits<{
  refresh: [refresh: boolean];
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
  liquityHistoricPriceStatus,
  loading,
  modelSelectedAccounts,
  proxyInformation,
  stakingQueryStatus,
} = useLiquityStakingDetails();

function refresh(): void {
  emit('refresh', true);
}
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), t('staking.liquity')]"
    child
  >
    <template #buttons>
      <div class="flex items-center gap-3">
        <div v-if="$slots.modules">
          <slot name="modules" />
        </div>
        <RuiTooltip :open-delay="400">
          <template #activator>
            <RuiButton
              variant="outlined"
              color="primary"
              size="lg"
              :loading="loading"
              data-testid="liquity-refresh"
              @click="refresh()"
            >
              <template #prepend>
                <RuiIcon name="lu-refresh-ccw" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </template>
          {{ t('liquity_staking_details.refresh_tooltip') }}
        </RuiTooltip>
      </div>
    </template>
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <BlockchainAccountSelector
        v-model="modelSelectedAccounts"
        :source="{ chains, usableAddresses: availableAddresses }"
        :field="{ dense: true, label: t('liquity_staking_details.select_account') }"
      />

      <div
        v-if="proxyInformation || loading"
        class="flex flex-wrap items-center gap-2"
      >
        <LiquityProxyInformation
          v-if="proxyInformation"
          :proxy-information="proxyInformation"
        />

        <div
          v-if="loading && (stakingQueryStatus || liquityHistoricPriceStatus)"
          class="flex items-center gap-3 text-rui-text-secondary text-sm"
          data-testid="liquity-query-status"
        >
          <RuiProgress
            thickness="2"
            size="18"
            color="primary"
            variant="indeterminate"
            circular
          />
          <div>
            <div v-if="stakingQueryStatus">
              {{
                t('liquity_staking_details.query_staking_data', {
                  processed: stakingQueryStatus.current,
                  total: stakingQueryStatus.total,
                })
              }}
            </div>

            <div v-if="liquityHistoricPriceStatus">
              {{
                t('liquity_staking_details.query_historical_price', {
                  processed: liquityHistoricPriceStatus.processed,
                  total: liquityHistoricPriceStatus.total,
                })
              }}
            </div>
          </div>
        </div>
      </div>
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
      :section-title="t('liquity_staking_events.title')"
      :restrictions="{
        entryTypes: [HistoryEventEntryType.EVM_EVENT],
        externalAccounts: accountFilter,
        onlyChains: chains,
        protocols: ['liquity'],
      }"
    />
  </TablePageLayout>
</template>
