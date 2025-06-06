<script setup lang="ts">
import { useBalances } from '@/composables/balances';
import { useAggregatedBalances } from '@/composables/balances/aggregated';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';

const emit = defineEmits<{
  (e: 'click'): void;
}>();

const { useIsTaskRunning } = useTaskStore();
const { refreshPrices } = useBalances();
const { isLoading } = useStatusStore();

const refreshing = isLoading(Section.PRICES);
const { t } = useI18n({ useScope: 'global' });

const loadingData = logicOr(
  useIsTaskRunning(TaskType.QUERY_BALANCES),
  useIsTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES),
  useIsTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES),
  useIsTaskRunning(TaskType.MANUAL_BALANCES),
);

const { assets } = useAggregatedBalances();

async function refresh() {
  emit('click');
  await refreshPrices(true, get(assets));
}

const disabled = computed<boolean>(() => get(refreshing) || get(loadingData));
</script>

<template>
  <RuiButton
    variant="outlined"
    color="primary"
    :loading="refreshing"
    data-cy="price-refresh"
    :disabled="disabled"
    @click="refresh()"
  >
    <template #prepend>
      <RuiIcon name="lu-refresh-ccw" />
    </template>
    {{ t('price_refresh.button') }}
  </RuiButton>
</template>
