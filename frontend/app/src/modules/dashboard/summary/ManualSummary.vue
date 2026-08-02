<script lang="ts" setup>
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import ManualBalanceCardList from './ManualBalanceCardList.vue';
import SummaryCard from './SummaryCard.vue';
import SummaryCardCreateButton from './SummaryCardCreateButton.vue';

const { fetchManualBalances } = useManualBalances();
const { manualBalanceByLocation } = useManualBalanceData();
const { useIsActive } = useTaskCenter();

const isManualBalancesLoading = useIsActive(ActivityKind.MANUAL_BALANCES);
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="w-full">
    <SummaryCard
      :name="t('dashboard.manual_balances.title')"
      :tooltip="t('dashboard.manual_balances.card_tooltip')"
      :is-loading="isManualBalancesLoading"
      can-refresh
      :navigates-to="{ name: '/balances/manual/[[tab]]' }"
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
          :amount="manualBalance.value"
        />
      </div>
    </SummaryCard>
  </div>
</template>
