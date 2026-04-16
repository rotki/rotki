<script setup lang="ts">
import { useBlockchainBalanceStaleness } from '@/modules/balances/use-blockchain-balance-staleness';

const { lastRefreshed, lastRefreshTimestamp } = useBlockchainBalanceStaleness();
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    v-if="lastRefreshTimestamp"
    class="inline-flex"
    :popper="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <span class="inline-flex items-center gap-1 text-xs text-rui-text-secondary whitespace-nowrap">
        <RuiIcon
          name="lu-refresh-ccw"
          size="14"
        />
        {{ lastRefreshed }}
      </span>
    </template>
    {{ t('blockchain_balances.last_refresh_tooltip') }}
  </RuiTooltip>
</template>
