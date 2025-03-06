<script lang="ts" setup>
import SummaryCard from '@/modules/dashboard/summary/SummaryCard.vue';
import BlockchainBalanceRefreshBehaviourMenu
  from '@/components/dashboard/blockchain-balance/BlockchainBalanceRefreshBehaviourMenu.vue';
import { useBlockchainStore } from '@/store/blockchain';
import { TaskType } from '@/types/task-type';
import { useRefresh } from '@/composables/balances/refresh';
import { useTaskStore } from '@/store/tasks';
import { Routes } from '@/router/routes';
import BlockchainBalanceCardList from './BlockchainBalanceCardList.vue';
import SummaryCardCreateButton from './SummaryCardCreateButton.vue';

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
      <SummaryCardCreateButton
        v-if="blockchainTotals.length === 0"
        :to="{
          path: '/accounts/evm',
          query: {
            add: 'true',
          },
        }"
      >
        {{ t('dashboard.blockchain_balances.add') }}
      </SummaryCardCreateButton>
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
