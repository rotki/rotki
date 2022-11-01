<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ t('transactions.loading') }}
    </template>
    {{ t('transactions.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <transaction-content @fetch="fetchTransactions" />
  </div>
</template>

<script setup lang="ts">
import { isSectionLoading, useSectionLoading } from '@/composables/common';
import { useTransactions } from '@/store/history/transactions';
import { useTasks } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';

const ProgressScreen = defineAsyncComponent(
  () => import('@/components/helper/ProgressScreen.vue')
);
const TransactionContent = defineAsyncComponent(
  () => import('@/components/history/transactions/TransactionContent.vue')
);
const { fetchTransactions } = useTransactions();
const { pause, resume, isActive } = useIntervalFn(
  () => fetchTransactions(),
  10000
);

const { isTaskRunning } = useTasks();

const sectionLoading = isSectionLoading(Section.TX);
const eventTaskLoading = isTaskRunning(TaskType.TX_EVENTS);

watch(
  [sectionLoading, eventTaskLoading],
  ([sectionLoading, eventTaskLoading]) => {
    if ((sectionLoading || eventTaskLoading) && !get(isActive)) {
      resume();
    } else if (!sectionLoading && !eventTaskLoading && get(isActive)) {
      pause();
    }
  }
);

onBeforeMount(async () => {
  await fetchTransactions();
});

onUnmounted(() => {
  pause();
});

const { shouldShowLoadingScreen } = useSectionLoading();

const loading = shouldShowLoadingScreen(Section.TX);

const { t } = useI18n();
</script>
