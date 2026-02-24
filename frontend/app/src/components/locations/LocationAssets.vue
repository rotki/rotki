<script setup lang="ts">
import AssetBalances from '@/components/AssetBalances.vue';
import { useBalancesLoading } from '@/composables/balances/loading';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';

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
