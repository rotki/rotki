<script setup lang="ts">
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import CollapsedPendingTasks from '@/modules/core/notifications/CollapsedPendingTasks.vue';
import NoTasksRunning from '@/modules/core/notifications/NoTasksRunning.vue';
import PendingTask from '@/modules/core/notifications/PendingTask.vue';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { type Activity, resolveText } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import { useTaskController } from '@/modules/task-center/use-task-controller';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

const expanded = defineModel<boolean>({ required: true });

const { t } = useI18n({ useScope: 'global' });
const { active } = useTaskCenter();
const { activities } = useTaskOrchestrator();
const { cancel } = useTaskController();
const { dismiss, show } = useConfirmStore();

// Only work that is actually in flight. Producers now declare their whole tree up front, so every
// account of every chain exists as a queued activity from the moment a refresh starts — listing
// those would bury the running work under dozens of rows that have not begun. This is what the
// panel showed before the orchestrator too, when it read in-flight backend tasks.
const running = computed<Activity[]>(() => get(active));

// Visibility follows the list, not the orchestrator's phase. `isActive` is WORKING while anything
// is RUNNING *or PENDING*, but this panel lists RUNNING only — so cancelling the last running
// activity while queued siblings remained left the card up, spinning, headed "0 pending tasks".
const hasRunning = computed<boolean>(() => get(running).length > 0);

const debounceDismiss = useDebounceFn((live: boolean) => !live && dismiss(), 1000);

function showConfirmation(activity: Activity): void {
  // Close the dialog by itself if the work settles while it is open.
  const live = computed<boolean>(() => get(activities)
    .some(item => item.id === activity.id && !isTerminalStatus(item.status)));
  const unwatch = watch(live, debounceDismiss);

  show(
    {
      message: t('collapsed_pending_tasks.cancel_task_info', {
        title: resolveText(t, activity.subtitle) ?? activity.title,
      }),
      title: t('collapsed_pending_tasks.cancel_task'),
      type: 'warning',
    },
    async () => {
      unwatch();
      await cancel(activity);
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
      v-if="hasRunning"
      dense
      class="flex flex-col gap-2 max-h-[50vh]"
    >
      <CollapsedPendingTasks
        v-model="expanded"
        :count="running.length"
      />
      <div
        v-if="expanded"
        class="flex flex-col pt-3 -mb-3"
      >
        <PendingTask
          v-for="activity in running"
          :key="activity.id"
          :activity="activity"
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
