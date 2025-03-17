<script setup lang="ts">
import DashboardAssetTable from '@/components/dashboard/DashboardAssetTable.vue';
import DynamicMessageDisplay from '@/components/dashboard/DynamicMessageDisplay.vue';
import NftBalanceTable from '@/components/dashboard/NftBalanceTable.vue';
import OverallBalances from '@/components/dashboard/OverallBalances.vue';
import PriceRefresh from '@/components/helper/PriceRefresh.vue';
import { useAggregatedBalances } from '@/composables/balances/aggregated';
import { useDynamicMessages } from '@/composables/dynamic-messages';
import { useModules } from '@/composables/session/modules';
import { useTaskStore } from '@/store/tasks';
import { Module } from '@/types/modules';
import { DashboardTableType } from '@/types/settings/frontend-settings';
import { TaskType } from '@/types/task-type';
import PoolTable from './liquidity-pools/PoolTable.vue';
import Summary from './summary/Summary.vue';

const Type = DashboardTableType;

const { t } = useI18n({ useScope: 'global' });
const { useIsTaskRunning } = useTaskStore();
const { isModuleEnabled } = useModules();
const { balances, liabilities } = useAggregatedBalances();
const { activeDashboardMessages } = useDynamicMessages();

const aggregatedBalances = balances();
const aggregatedLiabilities = liabilities();

const nftEnabled = isModuleEnabled(Module.NFTS);

const isQueryingBlockchain = useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
const isLoopringLoading = useIsTaskRunning(TaskType.L2_LOOPRING);
const isExchangeLoading = useIsTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES);
const isAllBalancesLoading = useIsTaskRunning(TaskType.QUERY_BALANCES);

const isBlockchainLoading = logicOr(isQueryingBlockchain, isLoopringLoading);
const isAnyLoading = logicOr(isBlockchainLoading, isExchangeLoading, isAllBalancesLoading);
const dismissedMessage = useSessionStorage('rotki.messages.dash.dismissed', false);
</script>

<template>
  <div
    class="pb-6"
    data-cy="dashboard"
  >
    <DynamicMessageDisplay
      v-if="activeDashboardMessages.length > 0 && !dismissedMessage"
      class="!-mt-6 mb-4"
      :messages="activeDashboardMessages"
      @dismiss="dismissedMessage = true"
    />
    <div class="container">
      <div class="flex flex-wrap gap-6">
        <div class="w-full">
          <OverallBalances />
        </div>
        <Summary />
      </div>
      <div class="flex justify-end my-4">
        <PriceRefresh />
      </div>
      <DashboardAssetTable
        :title="t('common.assets')"
        :table-type="Type.ASSETS"
        :loading="isAnyLoading"
        :balances="aggregatedBalances"
      />
      <PoolTable class="mt-8" />
      <DashboardAssetTable
        v-if="aggregatedLiabilities.length > 0"
        class="mt-8"
        :table-type="Type.LIABILITIES"
        :title="t('dashboard.liabilities.title')"
        :loading="isAnyLoading"
        :balances="aggregatedLiabilities"
      />
      <NftBalanceTable
        v-if="nftEnabled"
        id="nft-balance-table-section"
        data-cy="nft-balance-table"
        class="mt-8"
      />
    </div>
  </div>
</template>
