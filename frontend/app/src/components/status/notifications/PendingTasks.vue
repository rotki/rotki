<script setup lang="ts">
import type { Task, TaskMeta } from '@/types/task';
import CollapsedPendingTasks from '@/components/status/notifications/CollapsedPendingTasks.vue';
import NoTasksRunning from '@/components/status/notifications/NoTasksRunning.vue';
import PendingTask from '@/components/status/notifications/PendingTask.vue';
import { useConfirmStore } from '@/store/confirm';
import { useTaskStore } from '@/store/tasks';

const expanded = ref(false);

const { t } = useI18n();
const store = useTaskStore();
const { hasRunningTasks, tasks } = storeToRefs(store);
const { cancelTask, useIsTaskRunning } = store;
const { dismiss, show } = useConfirmStore();

const debounceDismiss = useDebounceFn((running: boolean) => !running && dismiss(), 1000);

function showConfirmation(task: Task<TaskMeta>) {
  const taskRef = useIsTaskRunning(task.type, task.meta);
  const unwatch = watch(taskRef, debounceDismiss);

  show(
    {
      message: t('collapsed_pending_tasks.cancel_task_info', {
        title: task.meta.title,
      }),
      title: t('collapsed_pending_tasks.cancel_task'),
      type: 'warning',
    },
    () => {
      unwatch();
      cancelTask(task);
    },
    () => {
      unwatch();
    },
  );
}
</script>

<template>
  <div class="px-3.5 mb-2">
    <RuiCard
      v-if="hasRunningTasks"
      dense
      class="flex flex-col gap-2 max-h-[50vh]"
    >
      <CollapsedPendingTasks
        v-model="expanded"
        :count="tasks.length"
      />
      <div
        v-if="expanded"
        class="flex flex-col pt-3 -mb-3"
      >
        <PendingTask
          v-for="task in tasks"
          :key="task.id"
          :task="task"
          class="border-t border-default py-2"
          @cancel="showConfirmation($event)"
        />
      </div>
    </RuiCard>
    <div v-else>
      <NoTasksRunning />
    </div>
  </div>
</template>
