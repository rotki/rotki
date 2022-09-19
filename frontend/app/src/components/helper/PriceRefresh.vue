<template>
  <v-btn
    outlined
    color="primary"
    :loading="refreshing"
    :disabled="refreshing || loadingData"
    @click="refreshPrices(true)"
  >
    <v-icon left>mdi-refresh</v-icon>
    {{ t('price_refresh.button') }}
  </v-btn>
</template>

<script setup lang="ts">
import { useSectionLoading } from '@/composables/common';
import { useBalancesStore } from '@/store/balances';
import { useTasks } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';

const { isTaskRunning } = useTasks();
const { refreshPrices } = useBalancesStore();
const { isSectionRefreshing } = useSectionLoading();

const refreshing = isSectionRefreshing(Section.PRICES);

const loadingData = computed<boolean>(() => {
  return (
    get(isTaskRunning(TaskType.QUERY_BALANCES)) ||
    get(isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES)) ||
    get(isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES)) ||
    get(isTaskRunning(TaskType.MANUAL_BALANCES))
  );
});

const { t } = useI18n();
</script>
