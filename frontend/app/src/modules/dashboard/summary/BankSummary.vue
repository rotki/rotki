<script lang="ts" setup>
import { useBankData } from '@/modules/banks/use-bank-data';
import SummaryCard from '@/modules/dashboard/summary/SummaryCard.vue';
import SummaryCardCreateButton from '@/modules/dashboard/summary/SummaryCardCreateButton.vue';
import BankBox from './BankBox.vue';

const { t } = useI18n({ useScope: 'global' });

const { banks } = useBankData();
</script>

<template>
  <div class="w-full">
    <SummaryCard
      :name="t('dashboard.bank_balances.title')"
      :navigates-to="{ name: '/balances/banks/' }"
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
