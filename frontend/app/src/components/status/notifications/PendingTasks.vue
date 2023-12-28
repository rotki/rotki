<script setup lang="ts">
import { type Task, type TaskMeta } from '@/types/task';

const expanded = ref(false);

const { t } = useI18n();
const store = useTaskStore();
const { hasRunningTasks, tasks } = storeToRefs(store);
const { cancelTask } = store;
const { show } = useConfirmStore();

const showConfirmation = (task: Task<TaskMeta>) =>
  show(
    {
      title: t('collapsed_pending_tasks.cancel_task'),
      message: t('collapsed_pending_tasks.cancel_task_info', {
        title: task.meta.title
      }),
      type: 'warning'
    },
    () => {
      cancelTask(task);
    }
  );
</script>

<template>
  <div class="px-3.5 mb-2">
    <RuiCard v-if="hasRunningTasks" class="flex flex-col gap-2">
      <CollapsedPendingTasks v-model="expanded" :count="tasks.length" />
      <div v-if="expanded" class="flex flex-col pt-4 -mb-4">
        <PendingTask
          v-for="task in tasks"
          :key="task.id"
          :task="task"
          class="border-t border-default py-4"
          @cancel="showConfirmation($event)"
        />
      </div>
    </RuiCard>
    <div v-else>
      <NoTasksRunning />
    </div>
  </div>
</template>
