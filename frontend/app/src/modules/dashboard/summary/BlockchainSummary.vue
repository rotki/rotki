<script lang="ts" setup>
import { useBlockchainTotalSummary } from '@/modules/balances/blockchain/use-blockchain-total-summary';
import BlockchainBalanceRefreshBehaviourMenu
  from '@/modules/balances/BlockchainBalanceRefreshBehaviourMenu.vue';
import BlockchainBalanceStalenessIndicator from '@/modules/balances/BlockchainBalanceStalenessIndicator.vue';
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import { useBalanceStatus } from '@/modules/balances/use-balance-status';
import SummaryCard from '@/modules/dashboard/summary/SummaryCard.vue';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import BlockchainBalanceCardList from './BlockchainBalanceCardList.vue';
import BlockchainSummaryCardCreateButton from './BlockchainSummaryCardCreateButton.vue';

const { blockchainTotals } = useBlockchainTotalSummary();
const { useIsActive } = useTaskCenter();
const { refreshBalance } = useBalanceRefresh();
const { isRefreshing } = useBalanceStatus();
const { t } = useI18n({ useScope: 'global' });

const isTokenDetecting = useIsActive(ActivityKind.TOKEN_DETECTION);
const isLoading = logicOr(isRefreshing, isTokenDetecting);
</script>

<template>
  <div class="w-full">
    <SummaryCard
      :name="t('dashboard.blockchain_balances.title')"
      :is-loading="isLoading"
      can-refresh
      :navigates-to="{ name: '/balances/' }"
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
      <div class="px-6 pt-2 text-end">
        <BlockchainBalanceStalenessIndicator />
      </div>
    </SummaryCard>
  </div>
</template>
