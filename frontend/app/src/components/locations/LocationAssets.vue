<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import AssetBalances from '@/components/AssetBalances.vue';
import { useBalancesBreakdown } from '@/composables/balances/breakdown';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

const props = defineProps<{
  identifier: string;
}>();

const { identifier } = toRefs(props);
const { useIsTaskRunning } = useTaskStore();

const { t } = useI18n();

const { locationBreakdown: breakdown } = useBalancesBreakdown();
const locationBreakdown: ComputedRef<AssetBalanceWithPrice[]> = breakdown(identifier);

const loadingData = logicOr(
  useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES),
  useIsTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES),
  useIsTaskRunning(TaskType.QUERY_BALANCES),
);
</script>

<template>
  <RuiCard v-if="loadingData || locationBreakdown.length > 0">
    <template #header>
      {{ t('common.assets') }}
    </template>
    <AssetBalances
      :loading="loadingData"
      :balances="locationBreakdown"
      hide-breakdown
      sticky-header
    />
  </RuiCard>
</template>
