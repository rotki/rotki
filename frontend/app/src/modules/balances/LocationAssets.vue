<script setup lang="ts">
import AssetBalances from '@/modules/balances/AssetBalances.vue';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';

const { identifier } = defineProps<{
  identifier: string;
}>();

const { t } = useI18n({ useScope: 'global' });

const { useLocationBreakdown } = useAggregatedBalances();
const locationBreakdown = useLocationBreakdown(() => identifier);

const { loadingBalances } = useBalancesLoading();
</script>

<template>
  <RuiCard v-if="loadingBalances || locationBreakdown.length > 0">
    <template #header>
      {{ t('common.assets') }}
    </template>
    <AssetBalances
      :loading="loadingBalances"
      :balances="locationBreakdown"
      hide-breakdown
      sticky-header
    />
  </RuiCard>
</template>
