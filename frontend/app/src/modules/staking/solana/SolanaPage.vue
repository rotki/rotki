<script setup lang="ts">
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import { SOL_IDENTIFIER, SOLANA_STAKING_RESTRICTIONS } from '@/modules/staking/solana/constants';
import SolanaStakeAccountsTable from '@/modules/staking/solana/SolanaStakeAccountsTable.vue';
import { useSolanaStakeAccounts } from '@/modules/staking/solana/use-solana-stake-accounts';

defineOptions({
  name: 'SolanaPage',
});

const { t } = useI18n({ useScope: 'global' });

const { error, loading, refresh, rows, total } = useSolanaStakeAccounts();
const { fetchPrices } = usePriceTaskManager();

async function load(ignoreCache: boolean = false): Promise<void> {
  await Promise.all([
    refresh(),
    fetchPrices({ ignoreCache, selectedAssets: [SOL_IDENTIFIER] }),
  ]);
}

onMounted(async () => {
  await load();
});
</script>

<template>
  <TablePageLayout
    :title="[t('navigation_menu.staking'), t('staking.solana')]"
    child
  >
    <template #buttons>
      <RuiButton
        variant="outlined"
        color="primary"
        data-testid="solana-refresh"
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
        data-testid="solana-staking-error"
      >
        {{ t('staking_page.solana.fetch_failed', { message: error }) }}
      </RuiAlert>

      <RuiCard>
        <template #header>
          {{ t('staking_page.solana.staked') }}
        </template>
        <BalanceDisplay
          class="text-h5 mb-4"
          data-testid="solana-staked-total"
          :asset="SOL_IDENTIFIER"
          :value="{ amount: total }"
          :loading="loading"
          calculate-value
        />
        <SolanaStakeAccountsTable
          :rows="rows"
          :loading="loading"
        />
      </RuiCard>

      <HistoryEventsView
        :section-title="t('staking_page.solana.events')"
        :restrictions="SOLANA_STAKING_RESTRICTIONS"
      />
    </div>
  </TablePageLayout>
</template>
