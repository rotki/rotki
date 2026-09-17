<script lang="ts" setup>
import { useBlockchainTotalSummary } from '@/modules/balances/blockchain/use-blockchain-total-summary';
import SummaryCard from '@/modules/dashboard/summary/SummaryCard.vue';
import BlockchainBalanceCardList from './BlockchainBalanceCardList.vue';
import BlockchainSummaryCardCreateButton from './BlockchainSummaryCardCreateButton.vue';

const { blockchainTotals } = useBlockchainTotalSummary();
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="w-full">
    <SummaryCard
      :name="t('dashboard.blockchain_balances.title')"
      :navigates-to="{ name: '/balances/' }"
    >
      <BlockchainSummaryCardCreateButton v-if="blockchainTotals.length === 0" />
      <div
        v-else
        data-testid="blockchain-balances"
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
