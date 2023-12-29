<script setup lang="ts">
import { type Task, type TaskMeta } from '@/types/task';

const expanded = ref(false);

const { t } = useI18n();
const store = useTaskStore();
const { hasRunningTasks, tasks } = storeToRefs(store);
const { cancelTask, isTaskRunning } = store;
const { show, dismiss } = useConfirmStore();

const debounceDismiss = useDebounceFn(
  (running: boolean) => !running && dismiss(),
  1000
);

const showConfirmation = (task: Task<TaskMeta>) => {
  const taskRef = isTaskRunning(task.type, task.meta);
  const unwatch = watch(taskRef, debounceDismiss);

  return show(
    {
      title: t('collapsed_pending_tasks.cancel_task'),
      message: t('collapsed_pending_tasks.cancel_task_info', {
        title: task.meta.title
      }),
      type: 'warning'
    },
    () => {
      unwatch();
      cancelTask(task);
    },
    () => {
      unwatch();
    }
  );
};
</script>

<template>
  <div class="px-3.5 mb-2">
    <RuiCard v-if="hasRunningTasks" class="flex flex-col gap-2 max-h-[50vh]">
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
