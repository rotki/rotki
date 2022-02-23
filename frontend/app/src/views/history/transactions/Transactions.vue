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
import {
  defineComponent,
  onBeforeMount,
  onUnmounted,
  unref,
  watch
} from '@vue/composition-api';
import { useIntervalFn } from '@vueuse/core';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import { isSectionLoading, setupStatusChecking } from '@/composables/common';
import { Section } from '@/store/const';
import { useTransactions } from '@/store/history';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import TransactionContent from '@/views/history/transactions/TransactionContent.vue';

export default defineComponent({
  name: 'Transactions',
  components: {
    ProgressScreen,
    TransactionContent
  },
  setup() {
    const { fetchTransactions } = useTransactions();
    const { pause, resume, isActive } = useIntervalFn(
      () => fetchTransactions(),
      5000
    );

    const { isTaskRunning } = useTasks();

    const sectionLoading = isSectionLoading(Section.TX);
    const eventTaskLoading = isTaskRunning(TaskType.TX_EVENTS);

    watch(
      [sectionLoading, eventTaskLoading],
      ([sectionLoading, eventTaskLoading]) => {
        if ((sectionLoading || eventTaskLoading) && !unref(isActive)) {
          resume();
        } else if (!sectionLoading && !eventTaskLoading && unref(isActive)) {
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
