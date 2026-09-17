<script lang="ts" setup>
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import ManualBalanceCardList from './ManualBalanceCardList.vue';
import SummaryCard from './SummaryCard.vue';
import SummaryCardCreateButton from './SummaryCardCreateButton.vue';

const { manualBalanceByLocation } = useManualBalanceData();
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="w-full">
    <SummaryCard
      :name="t('dashboard.manual_balances.title')"
      :navigates-to="{ name: '/balances/manual/[[tab]]' }"
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
        data-testid="manual-balances"
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
