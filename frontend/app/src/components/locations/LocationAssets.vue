<script setup lang="ts">
import AssetBalances from '@/components/AssetBalances.vue';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

const props = defineProps<{
  identifier: string;
}>();

const { identifier } = toRefs(props);
const { useIsTaskRunning } = useTaskStore();

const { t } = useI18n({ useScope: 'global' });

const { useLocationBreakdown } = useAggregatedBalances();
const locationBreakdown = useLocationBreakdown(identifier);

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
