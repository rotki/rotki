<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('transactions.loading') }}
    </template>
    {{ $t('transactions.loading_subtitle') }}
  </progress-screen>
  <div v-else>
    <transaction-content @fetch="fetchTransactions" />
  </div>
</template>

<script lang="ts">
import { get, useIntervalFn } from '@vueuse/core';
import {
  defineAsyncComponent,
  defineComponent,
  onBeforeMount,
  onUnmounted,
  watch
} from 'vue';
import { isSectionLoading, setupStatusChecking } from '@/composables/common';
import { Section } from '@/store/const';
import { useTransactions } from '@/store/history';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

export default defineComponent({
  name: 'Transactions',
  components: {
    ProgressScreen: defineAsyncComponent(
      () => import('@/components/helper/ProgressScreen.vue')
    ),
    TransactionContent: defineAsyncComponent(
      () => import('@/views/history/transactions/TransactionContent.vue')
    )
  },
  setup() {
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

    const { shouldShowLoadingScreen } = setupStatusChecking();

    return {
      fetchTransactions,
      loading: shouldShowLoadingScreen(Section.TX)
    };
  }
});
</script>
