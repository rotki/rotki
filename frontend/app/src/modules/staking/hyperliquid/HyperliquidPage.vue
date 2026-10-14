<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import StakingPageLayout from '@/modules/staking/components/StakingPageLayout.vue';
import StakingTotals, { type StakingTotal } from '@/modules/staking/components/StakingTotals.vue';
import { HYPE_IDENTIFIER, HYPERLIQUID_STAKING_RESTRICTIONS } from '@/modules/staking/hyperliquid/constants';
import HyperliquidStakingTable from '@/modules/staking/hyperliquid/HyperliquidStakingTable.vue';
import { useHyperliquidStaking } from '@/modules/staking/hyperliquid/use-hyperliquid-staking';

defineOptions({
  name: 'HyperliquidPage',
});

const { t } = useI18n({ useScope: 'global' });

const { failedAddresses, loaded, loading, refresh, rows, total } = useHyperliquidStaking();

const stateTotals = computed<StakingTotal[]>(() => {
  const { delegated, pendingWithdrawal, undelegated } = get(total);
  return [{
    amount: delegated,
    key: 'delegated',
    label: t('staking_page.hyperliquid.table.delegated'),
    testid: 'hyperliquid-delegated-total',
  }, {
    amount: undelegated,
    key: 'undelegated',
    label: t('staking_page.hyperliquid.table.undelegated'),
    testid: 'hyperliquid-undelegated-total',
  }, {
    amount: pendingWithdrawal,
    key: 'pendingWithdrawal',
    label: t('staking_page.hyperliquid.table.pending_withdrawal'),
    testid: 'hyperliquid-pending-withdrawal-total',
  }];
});
</script>

<template>
  <StakingPageLayout
    location="hyperliquid"
    :chain="Blockchain.HYPERLIQUID"
    :asset="HYPE_IDENTIFIER"
    :failed-addresses="failedAddresses"
    :loading="loading"
    :refresh="refresh"
    :restrictions="HYPERLIQUID_STAKING_RESTRICTIONS"
  >
    <StakingTotals
      :asset="HYPE_IDENTIFIER"
      :totals="stateTotals"
      :loading="loading"
    />

    <HyperliquidStakingTable
      :rows="rows"
      :loaded="loaded"
      :loading="loading"
    />
  </StakingPageLayout>
</template>
