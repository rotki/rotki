<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import StakingHeadlineBalance from '@/modules/staking/components/StakingHeadlineBalance.vue';
import StakingPageLayout from '@/modules/staking/components/StakingPageLayout.vue';
import { SOL_IDENTIFIER, SOLANA_STAKING_RESTRICTIONS } from '@/modules/staking/solana/constants';
import SolanaStakeAccountsTable from '@/modules/staking/solana/SolanaStakeAccountsTable.vue';
import { useSolanaStakeAccounts } from '@/modules/staking/solana/use-solana-stake-accounts';

defineOptions({
  name: 'SolanaPage',
});

const { t } = useI18n({ useScope: 'global' });

const { failedAddresses, loaded, loading, refresh, rows, total } = useSolanaStakeAccounts();
</script>

<template>
  <StakingPageLayout
    location="solana"
    :chain="Blockchain.SOLANA"
    :asset="SOL_IDENTIFIER"
    :failed-addresses="failedAddresses"
    :loading="loading"
    :refresh="refresh"
    :restrictions="SOLANA_STAKING_RESTRICTIONS"
  >
    <RuiCard>
      <template #header>
        {{ t('staking_page.solana.staked') }}
      </template>
      <StakingHeadlineBalance
        data-testid="solana-staked-total"
        :asset="SOL_IDENTIFIER"
        :value="{ amount: total }"
        :loading="loading"
        calculate-value
      />
    </RuiCard>

    <SolanaStakeAccountsTable
      :rows="rows"
      :loaded="loaded"
      :loading="loading"
    />
  </StakingPageLayout>
</template>
