<script setup lang="ts">
import BalanceDisplay from '@/modules/shell/components/display/BalanceDisplay.vue';
import StakingPageLayout from '@/modules/staking/components/StakingPageLayout.vue';
import { SOL_IDENTIFIER, SOLANA_STAKING_RESTRICTIONS } from '@/modules/staking/solana/constants';
import SolanaStakeAccountsTable from '@/modules/staking/solana/SolanaStakeAccountsTable.vue';
import { useSolanaStakeAccounts } from '@/modules/staking/solana/use-solana-stake-accounts';

defineOptions({
  name: 'SolanaPage',
});

const { t } = useI18n({ useScope: 'global' });

const { failedAddresses, loading, refresh, rows, total } = useSolanaStakeAccounts();
</script>

<template>
  <StakingPageLayout
    :title="t('staking.solana')"
    :asset="SOL_IDENTIFIER"
    :failed-addresses="failedAddresses"
    :events-title="t('staking_page.solana.events')"
    :loading="loading"
    :refresh="refresh"
    :restrictions="SOLANA_STAKING_RESTRICTIONS"
  >
    <RuiCard>
      <template #header>
        {{ t('staking_page.solana.staked') }}
      </template>
      <BalanceDisplay
        class="text-h5"
        data-testid="solana-staked-total"
        :asset="SOL_IDENTIFIER"
        :value="{ amount: total }"
        :loading="loading"
        calculate-value
      />
    </RuiCard>

    <SolanaStakeAccountsTable
      :rows="rows"
      :loading="loading"
    />
  </StakingPageLayout>
</template>
