<template>
  <v-btn
    outlined
    color="primary"
    :loading="refreshing"
    :disabled="refreshing || loadingData"
    @click="refreshPrices({ ignoreCache: true })"
  >
    <v-icon left>mdi-refresh</v-icon>
    {{ t('price_refresh.button') }}
  </v-btn>
</template>

<script setup lang="ts">
import { get } from '@vueuse/core';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { useSectionLoading } from '@/composables/common';
import { useBalancesStore } from '@/store/balances';
import { Section } from '@/store/const';
import { useTasks } from '@/store/tasks';
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
