<script lang="ts" setup>
import { useBalanceRefresh } from '@/modules/balances/use-balance-refresh';
import { useBankData } from '@/modules/banks/use-bank-data';
import SummaryCard from '@/modules/dashboard/summary/SummaryCard.vue';
import SummaryCardCreateButton from '@/modules/dashboard/summary/SummaryCardCreateButton.vue';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import BankBox from './BankBox.vue';

const { t } = useI18n({ useScope: 'global' });

const { useIsActive } = useTaskCenter();
const { refreshBalance } = useBalanceRefresh();
const { banks } = useBankData();

const isBankLoading = useIsActive(ActivityKind.BANK_BALANCES);
</script>

<template>
  <div class="w-full">
    <SummaryCard
      :name="t('dashboard.bank_balances.title')"
      can-refresh
      :is-loading="isBankLoading"
      :navigates-to="{ name: '/balances/banks/' }"
      @refresh="refreshBalance($event)"
    >
      <SummaryCardCreateButton
        v-if="banks.length === 0"
        :to="{
          path: '/api-keys/banks',
          query: {
            add: 'true',
          },
        }"
      >
        {{ t('dashboard.bank_balances.add') }}
      </SummaryCardCreateButton>
      <div
        v-else
        data-testid="bank-balances"
      >
        <BankBox
          v-for="bank in banks"
          :key="bank.location"
          :location="bank.location"
          :amount="bank.total"
        />
      </div>
    </SummaryCard>
  </div>
</template>
