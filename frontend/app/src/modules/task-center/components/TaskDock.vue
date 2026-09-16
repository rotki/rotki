<script setup lang="ts">
import type { Activity } from '@/modules/task-center/core/types';
import CollapsedPendingTasks from '@/modules/core/notifications/CollapsedPendingTasks.vue';
import PendingTaskNode from '@/modules/core/notifications/PendingTaskNode.vue';
import { useCancelConfirmation } from '@/modules/task-center/use-cancel-confirmation';
import { DockState, useTaskDock } from '@/modules/task-center/use-task-dock';
import { useTaskDockCaption } from '@/modules/task-center/use-task-dock-caption';

const { t } = useI18n({ useScope: 'global' });

const {
  acknowledge,
  children,
  dismissed,
  failed,
  finished,
  holdPeek,
  isPrimaryRanked,
  jobs,
  modelExpanded,
  otherJobs,
  percentage,
  primary,
  primarySteps,
  state,
  steps,
  visible,
} = useTaskDock();
const { confirmCancel } = useCancelConfirmation();
const caption = useTaskDockCaption();

const now = useTimestamp({ interval: 1000 });

const isWorking = computed<boolean>(() => get(state) === DockState.WORKING);

/** The jobs in flight while working; once the run settles, the jobs whose outcome is being reported. */
const panelRoots = computed<Activity[]>(() => {
  switch (get(state)) {
    case DockState.WORKING:
      return get(jobs).map(job => job.activity);
    case DockState.FAILED:
      return get(failed);
    case DockState.DISMISSED:
      return get(dismissed);
    case DockState.DONE:
      return get(finished);
    default:
      return [];
  }
});

/** The panel needs a row to list; queued-only work keeps the pill but has nothing to expand into. */
const showPanel = computed<boolean>(() => get(modelExpanded) && get(panelRoots).length > 0);

const hasDeterminateRing = computed<boolean>(() => get(isPrimaryRanked) && (get(primary)?.percentage ?? -1) >= 0);

const isFailed = computed<boolean>(() => get(state) === DockState.FAILED);

/** Acknowledged failures keep only the icon on the pill, so they stay reachable without holding the corner. */
const isIconOnly = computed<boolean>(() => get(state) === DockState.DISMISSED);

function toggle(): void {
  set(modelExpanded, !get(modelExpanded));
}
</script>

<template>
  <div
    v-if="visible"
    class="fixed bottom-4 right-4 z-[7] flex flex-col items-end gap-2 max-w-[calc(100vw-2rem)]"
    @mouseenter="holdPeek(true)"
    @mouseleave="holdPeek(false)"
    @focusin="holdPeek(true)"
    @focusout="holdPeek(false)"
  >
    <RuiCard
      v-if="showPanel"
      dense
      class="w-[25rem] max-w-full flex flex-col gap-2 shadow-lg"
      data-testid="task-dock-panel"
    >
      <CollapsedPendingTasks
        v-if="isWorking"
        v-model="modelExpanded"
        :count="jobs.length"
        :steps="steps"
        :percentage="percentage"
      />
      <div
        v-else
        class="flex justify-between items-center gap-2"
      >
        <div class="font-medium leading-5 truncate">
          {{ caption }}
        </div>
        <RuiButton
          class="-m-1 shrink-0"
          variant="text"
          icon
          size="sm"
          :aria-label="t('pending_task.collapse')"
          @click="modelExpanded = false"
        >
          <RuiIcon name="lu-chevron-up" />
        </RuiButton>
      </div>
      <div class="flex flex-col divide-y divide-rui-grey-200 dark:divide-rui-grey-800 max-h-[50vh] overflow-y-auto">
        <PendingTaskNode
          v-for="root in panelRoots"
          :key="root.id"
          :activity="root"
          :children="children"
          :now="now"
          :dismissible="isFailed"
          @cancel="confirmCancel($event)"
          @dismiss="acknowledge($event.id)"
        />
      </div>
    </RuiCard>

    <button
      type="button"
      class="flex items-center gap-2 max-w-full rounded-full border border-default bg-white dark:bg-rui-grey-900 shadow-md py-1.5 text-sm"
      :class="isIconOnly ? 'px-1.5' : 'pl-2 pr-3'"
      :aria-expanded="showPanel"
      :aria-label="showPanel ? t('task_dock.hide') : t('task_dock.show')"
      :data-state="state"
      data-testid="task-dock-pill"
      @click="toggle()"
    >
      <RuiIcon
        v-if="isFailed || isIconOnly"
        name="lu-circle-x"
        size="20"
        class="text-rui-error shrink-0"
      />
      <RuiIcon
        v-else-if="state === DockState.DONE"
        name="lu-check"
        size="20"
        class="text-rui-success shrink-0"
      />
      <RuiProgress
        v-else-if="hasDeterminateRing"
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
        :class="{ 'sr-only': isIconOnly }"
        aria-live="polite"
        data-testid="task-dock-caption"
      >
        {{ caption }}
      </span>
      <template v-if="isWorking">
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
      </template>
    </button>
  </div>
</template>
