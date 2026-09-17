<script setup lang="ts">
import { useBlockchainBalanceStaleness } from '@/modules/balances/use-blockchain-balance-staleness';

const { t } = useI18n({ useScope: 'global' });

const { lastRefreshed, lastRefreshTimestamp } = useBlockchainBalanceStaleness();
</script>

<template>
  <RuiTooltip
    v-if="lastRefreshTimestamp"
    class="self-start"
    :options="{ placement: 'bottom' }"
    :open-delay="400"
  >
    <template #activator>
      <span
        class="text-xs text-rui-text-secondary whitespace-nowrap"
        data-testid="dashboard-chains-updated"
      >
        {{ t('dashboard.refresh.chains_updated', { time: lastRefreshed }) }}
      </span>
    </template>
    {{ t('blockchain_balances.last_refresh_tooltip') }}
  </RuiTooltip>
</template>
