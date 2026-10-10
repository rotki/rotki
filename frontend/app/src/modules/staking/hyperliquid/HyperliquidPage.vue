<script setup lang="ts">
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { HYPE_IDENTIFIER, HYPERLIQUID_STAKING_RESTRICTIONS } from '@/modules/staking/hyperliquid/constants';
import HyperliquidStakingTable from '@/modules/staking/hyperliquid/HyperliquidStakingTable.vue';
import { useHyperliquidStaking } from '@/modules/staking/hyperliquid/use-hyperliquid-staking';

defineOptions({
  name: 'HyperliquidPage',
});

const { t } = useI18n({ useScope: 'global' });

const { error, loading, refresh, rows, total } = useHyperliquidStaking();
const { fetchPrices } = usePriceTaskManager();

async function load(ignoreCache: boolean = false): Promise<void> {
  await Promise.all([
    refresh(),
    fetchPrices({ ignoreCache, selectedAssets: [HYPE_IDENTIFIER] }),
  ]);
}

onMounted(async () => {
  await load();
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), t('staking.hyperliquid')]"
    child
  >
    <template #buttons>
      <RuiButton
        variant="outlined"
        color="primary"
        data-testid="hyperliquid-refresh"
        :loading="loading"
        @click="load(true)"
      >
        <template #prepend>
          <RuiIcon name="lu-refresh-ccw" />
        </template>
        {{ t('common.refresh') }}
      </RuiButton>
    </template>

    <div class="flex flex-col gap-4">
      <RuiAlert
        v-if="error"
        type="error"
        data-testid="hyperliquid-staking-error"
      >
        {{ t('staking_page.hyperliquid.fetch_failed', { message: error }) }}
      </RuiAlert>

      <div class="grid md:grid-cols-3 gap-4">
        <RuiCard>
          <template #header>
            {{ t('staking_page.hyperliquid.table.delegated') }}
          </template>
          <BalanceDisplay
            class="text-h5"
            data-testid="hyperliquid-delegated-total"
            :asset="HYPE_IDENTIFIER"
            :value="{ amount: total.delegated }"
            :loading="loading"
            calculate-value
          />
        </RuiCard>
        <RuiCard>
          <template #header>
            {{ t('staking_page.hyperliquid.table.undelegated') }}
          </template>
          <BalanceDisplay
            class="text-h5"
            data-testid="hyperliquid-undelegated-total"
            :asset="HYPE_IDENTIFIER"
            :value="{ amount: total.undelegated }"
            :loading="loading"
            calculate-value
          />
        </RuiCard>
        <RuiCard>
          <template #header>
            {{ t('staking_page.hyperliquid.table.pending_withdrawal') }}
          </template>
          <BalanceDisplay
            class="text-h5"
            data-testid="hyperliquid-pending-withdrawal-total"
            :asset="HYPE_IDENTIFIER"
            :value="{ amount: total.pendingWithdrawal }"
            :loading="loading"
            calculate-value
          />
        </RuiCard>
      </div>

      <HyperliquidStakingTable
        :rows="rows"
        :loading="loading"
      />

      <HistoryEventsView
        :section-title="t('staking_page.hyperliquid.events')"
        :restrictions="HYPERLIQUID_STAKING_RESTRICTIONS"
      />
    </div>
  </TablePageLayout>
</template>
