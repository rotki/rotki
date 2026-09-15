<script setup lang="ts">
import CollapsedPendingTasks from '@/modules/core/notifications/CollapsedPendingTasks.vue';
import PendingTaskNode from '@/modules/core/notifications/PendingTaskNode.vue';
import { useCancelConfirmation } from '@/modules/task-center/use-cancel-confirmation';
import { useTaskDock } from '@/modules/task-center/use-task-dock';

const { t } = useI18n({ useScope: 'global' });

const { children, isPrimaryLong, jobs, modelExpanded, otherJobs, percentage, primary, primarySteps, steps, visible } = useTaskDock();
const { confirmCancel } = useCancelConfirmation();

const now = useTimestamp({ interval: 1000 });

/** The panel needs a job to list; queued-only work keeps the pill but has nothing to expand into. */
const showPanel = computed<boolean>(() => get(modelExpanded) && get(jobs).length > 0);

const hasDeterminateRing = computed<boolean>(() => get(isPrimaryLong) && (get(primary)?.percentage ?? -1) >= 0);

const caption = computed<string>(() => get(primary)?.activity.title ?? t('task_dock.queued'));

function toggle(): void {
  set(modelExpanded, !get(modelExpanded));
}
</script>

<template>
  <div
    v-if="visible"
    class="fixed bottom-4 right-4 z-[7] flex flex-col items-end gap-2 max-w-[calc(100vw-2rem)]"
  >
    <RuiCard
      v-if="showPanel"
      dense
      class="w-[25rem] max-w-full flex flex-col gap-2 shadow-lg"
      data-testid="task-dock-panel"
    >
      <CollapsedPendingTasks
        v-model="modelExpanded"
        :count="jobs.length"
        :steps="steps"
        :percentage="percentage"
      />
      <div class="flex flex-col divide-y divide-rui-grey-200 dark:divide-rui-grey-800 max-h-[50vh] overflow-y-auto">
        <PendingTaskNode
          v-for="job in jobs"
          :key="job.activity.id"
          :activity="job.activity"
          :children="children"
          :now="now"
          @cancel="confirmCancel($event)"
        />
      </div>
    </RuiCard>

    <button
      type="button"
      class="flex items-center gap-2 max-w-full rounded-full border border-default bg-white dark:bg-rui-grey-900 shadow-md pl-2 pr-3 py-1.5 text-sm"
      :aria-expanded="showPanel"
      :aria-label="showPanel ? t('task_dock.hide') : t('task_dock.show')"
      data-testid="task-dock-pill"
      @click="toggle()"
    >
      <RuiProgress
        v-if="hasDeterminateRing"
        color="primary"
        variant="determinate"
        circular
        :value="primary?.percentage"
        size="20"
        thickness="2"
      />
      <RuiProgress
        v-else
        color="primary"
        variant="indeterminate"
        circular
        size="20"
        thickness="2"
      />
      <span
        class="truncate font-medium"
        data-testid="task-dock-caption"
      >
        {{ caption }}
      </span>
      <span
        v-if="primarySteps"
        class="text-rui-text-secondary tabular-nums shrink-0"
        data-testid="task-dock-steps"
      >
        {{ t('pending_task.steps', { current: primarySteps.current, total: primarySteps.total }) }}
      </span>
      <span
        v-if="otherJobs > 0"
        class="text-rui-text-secondary shrink-0"
        data-testid="task-dock-more"
      >
        {{ t('task_dock.more', { count: otherJobs }) }}
      </span>
    </button>
  </div>
</template>
