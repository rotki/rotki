<script lang="ts" setup>
import BlockchainBalanceRefreshBehaviourMenu
  from '@/components/dashboard/blockchain-balance/BlockchainBalanceRefreshBehaviourMenu.vue';
import { useRefresh } from '@/composables/balances/refresh';
import SummaryCard from '@/modules/dashboard/summary/SummaryCard.vue';
import { Routes } from '@/router/routes';
import { useBlockchainStore } from '@/store/blockchain';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import BlockchainBalanceCardList from './BlockchainBalanceCardList.vue';
import BlockchainSummaryCardCreateButton from './BlockchainSummaryCardCreateButton.vue';

const { blockchainTotals } = storeToRefs(useBlockchainStore());
const { isTaskRunning } = useTaskStore();
const { refreshBalance } = useRefresh();
const { t } = useI18n({ useScope: 'global' });

const isTokenDetecting = isTaskRunning(TaskType.FETCH_DETECTED_TOKENS);
const isQueryingBlockchain = isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES);
const isLoopringLoading = isTaskRunning(TaskType.L2_LOOPRING);
const isBlockchainLoading = logicOr(isQueryingBlockchain, isLoopringLoading);
const isLoading = logicOr(isBlockchainLoading, isTokenDetecting);
</script>

<template>
  <div class="w-full">
    <SummaryCard
      :name="t('dashboard.blockchain_balances.title')"
      :is-loading="isLoading"
      can-refresh
      :navigates-to="Routes.BALANCES"
      @refresh="refreshBalance($event)"
    >
      <template #refreshMenu>
        <BlockchainBalanceRefreshBehaviourMenu />
      </template>
      <BlockchainSummaryCardCreateButton v-if="blockchainTotals.length === 0" />
      <div
        v-else
        data-cy="blockchain-balances"
      >
        <BlockchainBalanceCardList
          v-for="total in blockchainTotals"
          :key="total.chain"
          :total="total"
        />
      </div>
    </SummaryCard>
  </div>
</template>
