<script lang="ts" setup>
import { Routes } from '@/router/routes';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import ManualBalanceCardList from './ManualBalanceCardList.vue';
import SummaryCard from './SummaryCard.vue';
import SummaryCardCreateButton from './SummaryCardCreateButton.vue';

const manualBalancesStore = useManualBalancesStore();
const { fetchManualBalances } = manualBalancesStore;
const { manualBalanceByLocation } = storeToRefs(manualBalancesStore);
const { isTaskRunning } = useTaskStore();

const isManualBalancesLoading = isTaskRunning(TaskType.MANUAL_BALANCES);
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="w-full">
    <SummaryCard
      :name="t('dashboard.manual_balances.title')"
      :tooltip="t('dashboard.manual_balances.card_tooltip')"
      :is-loading="isManualBalancesLoading"
      can-refresh
      :navigates-to="Routes.BALANCES_MANUAL"
      @refresh="fetchManualBalances(true)"
    >
      <SummaryCardCreateButton
        v-if="manualBalanceByLocation.length === 0"
        :to="{
          path: '/balances/manual/assets',
          query: {
            add: 'true',
          },
        }"
      >
        {{ t('dashboard.manual_balances.add') }}
      </SummaryCardCreateButton>
      <div
        v-else
        data-cy="manual-balances"
      >
        <ManualBalanceCardList
          v-for="manualBalance in manualBalanceByLocation"
          :key="manualBalance.location"
          :name="manualBalance.location"
          :amount="manualBalance.usdValue"
        />
      </div>
    </SummaryCard>
  </div>
</template>
