<script setup lang="ts">
import type { HyperliquidStakingSummary } from '@/modules/staking/staking-types';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import StakingPageLayout from '@/modules/staking/components/StakingPageLayout.vue';
import { HYPE_IDENTIFIER, HYPERLIQUID_STAKING_RESTRICTIONS } from '@/modules/staking/hyperliquid/constants';
import HyperliquidStakingTable from '@/modules/staking/hyperliquid/HyperliquidStakingTable.vue';
import { useHyperliquidStaking } from '@/modules/staking/hyperliquid/use-hyperliquid-staking';

defineOptions({
  name: 'HyperliquidPage',
});

interface StateTotal {
  key: keyof HyperliquidStakingSummary;
  label: string;
  testid: string;
}

const { t } = useI18n({ useScope: 'global' });

const { error, loading, refresh, rows, total } = useHyperliquidStaking();

const stateTotals = computed<StateTotal[]>(() => [{
  key: 'delegated',
  label: t('staking_page.hyperliquid.table.delegated'),
  testid: 'hyperliquid-delegated-total',
}, {
  key: 'undelegated',
  label: t('staking_page.hyperliquid.table.undelegated'),
  testid: 'hyperliquid-undelegated-total',
}, {
  key: 'pendingWithdrawal',
  label: t('staking_page.hyperliquid.table.pending_withdrawal'),
  testid: 'hyperliquid-pending-withdrawal-total',
}]);

const errorMessage = computed<string>(() => {
  const message = get(error);
  return message ? t('staking_page.hyperliquid.fetch_failed', { message }) : '';
});
</script>

<template>
  <StakingPageLayout
    :title="t('staking.hyperliquid')"
    :asset="HYPE_IDENTIFIER"
    :error="errorMessage"
    :events-title="t('staking_page.hyperliquid.events')"
    :loading="loading"
    :refresh="refresh"
    :restrictions="HYPERLIQUID_STAKING_RESTRICTIONS"
  >
    <div class="grid md:grid-cols-3 gap-4">
      <RuiCard
        v-for="state in stateTotals"
        :key="state.key"
      >
        <template #header>
          {{ state.label }}
        </template>
        <BalanceDisplay
          class="text-h5"
          :data-testid="state.testid"
          :asset="HYPE_IDENTIFIER"
          :value="{ amount: total[state.key] }"
          :loading="loading"
          calculate-value
        />
      </RuiCard>
    </div>

    <HyperliquidStakingTable
      :rows="rows"
      :loading="loading"
    />
  </StakingPageLayout>
</template>
