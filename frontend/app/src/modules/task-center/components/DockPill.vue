<script setup lang="ts">
import type { Activity, ActivityId } from '@/modules/task-center/core/types';
import type { PendingJob } from '@/modules/task-center/use-pending-jobs';
import { DockState } from '@/modules/task-center/dock-state';
import { useDockPrimary } from '@/modules/task-center/use-dock-primary';
import { useTaskDock } from '@/modules/task-center/use-task-dock';
import { allStopped, useTaskDockCaption } from '@/modules/task-center/use-task-dock-caption';

const { children, expanded, jobs, listed } = defineProps<{
  jobs: PendingJob[];
  children: ReadonlyMap<ActivityId, Activity[]>;
  /** The jobs the panel lists, which a settled outcome names. */
  listed: Activity[];
  /** Whether the panel above the pill is showing. */
  expanded: boolean;
}>();

const emit = defineEmits<{
  toggle: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { dismissedFailure, state } = useTaskDock();
const { isPrimaryRanked, otherJobs, primary, primarySteps } = useDockPrimary(() => jobs, () => children);
const caption = useTaskDockCaption(() => jobs, () => children, () => listed);

const isWorking = computed<boolean>(() => get(state) === DockState.WORKING);

/** Dismissed outcomes keep only the icon on the pill, so they stay reachable without holding the corner. */
const isIconOnly = computed<boolean>(() => get(state) === DockState.DISMISSED);

/** A failure marks the pill whether it is still reported or already dismissed. */
const showsFailure = computed<boolean>(() => get(state) === DockState.FAILED || (get(isIconOnly) && get(dismissedFailure)));

const showsAttention = computed<boolean>(() => get(state) === DockState.ATTENTION);

/** A clean outcome made only of jobs the user stopped shows the stop mark their rows show, not a check. */
const showsStopped = computed<boolean>(() => get(state) === DockState.DONE && allStopped(listed));

const showsSuccess = computed<boolean>(() => get(state) === DockState.DONE || (get(isIconOnly) && !get(dismissedFailure)));

const hasDeterminateRing = computed<boolean>(() => get(isPrimaryRanked) && (get(primary)?.percentage ?? -1) >= 0);
</script>

<template>
  <button
    type="button"
    class="flex items-center gap-2 max-w-full rounded-full border border-default bg-white dark:bg-rui-grey-900 shadow-md py-1.5 text-sm"
    :class="isIconOnly ? 'px-1.5' : 'pl-2 pr-3'"
    :aria-expanded="expanded"
    :aria-label="expanded ? t('task_dock.hide') : t('task_dock.show')"
    :data-state="state"
    data-testid="task-dock-pill"
    @click="emit('toggle')"
  >
    <RuiIcon
      v-if="showsFailure"
      name="lu-circle-x"
      size="20"
      class="text-rui-error shrink-0"
    />
    <RuiIcon
      v-else-if="showsAttention"
      name="lu-triangle-alert"
      size="20"
      class="text-rui-warning shrink-0"
    />
    <RuiIcon
      v-else-if="showsStopped"
      name="lu-ban"
      size="20"
      class="text-rui-text-secondary shrink-0"
      data-testid="task-dock-stopped"
    />
    <RuiIcon
      v-else-if="showsSuccess"
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
</template>
