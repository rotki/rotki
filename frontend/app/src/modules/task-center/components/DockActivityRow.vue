<script setup lang="ts">
import { type ActivityOutcome, activityOutcome } from '@/modules/task-center/activity-outcome';
import DockActivityDetail from '@/modules/task-center/components/DockActivityDetail.vue';
import { formatElapsed } from '@/modules/task-center/core/elapsed';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { type Activity, ActivityStatus, type ActivitySteps } from '@/modules/task-center/core/types';
import { useActivityLabel } from '@/modules/task-center/use-activity-label';

const { activity, cancellable, dismissible = false, nested = false, now, outcomeStatus, percentage, steps } = defineProps<{
  activity: Activity;
  /** Ticks once a second, owned by the panel so one timer serves every row. */
  now: number;
  /** 0-100, or `-1` for indeterminate. Parents pass their subtree's; leaves their own. */
  percentage: number;
  /** Present for a parent: the leaf tally behind {@link percentage}. */
  steps?: ActivitySteps;
  cancellable: boolean;
  /** Whether the row offers to dismiss the outcome it reports; the caller decides which outcomes stay until dismissed. */
  dismissible?: boolean;
  /** The status the row reports, when it differs from the activity's own; a parent passes its subtree's failure. */
  outcomeStatus?: ActivityStatus;
  /** A child row: the job above it already names the work, so its own label is enough. */
  nested?: boolean;
}>();

const emit = defineEmits<{
  cancel: [activity: Activity];
  dismiss: [activity: Activity];
  retry: [activity: Activity];
}>();

defineSlots<{
  /** Replaces the tally line when the row is not showing a progress bar; a settled job puts its outcome here. */
  summary?: () => unknown;
}>();

const { t } = useI18n({ useScope: 'global' });

const { labelOf, subtitleOf } = useActivityLabel();

/** Tailwind only sees class names written out in full, so each outcome colour is spelled here. */
const TEXT_COLOR: Record<ActivityOutcome['color'], string> = {
  error: 'text-rui-error',
  grey: 'text-rui-text-secondary',
  primary: 'text-rui-primary',
  success: 'text-rui-success',
  warning: 'text-rui-warning',
};

const label = computed<string>(() => labelOf(activity, nested));

const secondary = computed<string | undefined>(() => (nested ? undefined : subtitleOf(activity)));

const status = computed<ActivityStatus>(() => outcomeStatus ?? activity.status);

const isRunning = computed<boolean>(() => activity.status === ActivityStatus.RUNNING);

const isFailed = computed<boolean>(() => get(status) === ActivityStatus.FAILED);

/** Only an activity that failed itself can be run again; a parent reporting a child's failure retries through that child. */
const retryable = computed<boolean>(() => activity.status === ActivityStatus.FAILED && activity.rerunnable);

const outcome = computed<ActivityOutcome>(() => activityOutcome(get(status)));

/** The status word, plus the producer's reason when there is one, so the mark says what the colour means. */
const outcomeText = computed<string>(() => {
  const word = t(get(outcome).key);
  const { reason } = activity;
  return reason ? t('pending_task.status.with_reason', { reason, status: word }) : word;
});

const elapsed = computed<string | undefined>(() => {
  if (!get(isRunning) || activity.startedAt === undefined)
    return undefined;

  return formatElapsed(now - activity.startedAt);
});

/** A bar earns its line only with a real number to fill it; indeterminate work says so with its mark. */
const showMeter = computed<boolean>(() => get(isRunning) && percentage >= 0);

const count = computed<string>(() => (steps && steps.total > 0
  ? t('pending_task.steps', { current: steps.current, total: steps.total })
  : t('percentage_display.value', { value: percentage })));

const reasonColor = computed<string>(() => (get(isFailed) ? 'text-rui-error' : 'text-rui-warning'));

/** A settled child with nothing but its name is one line, so it takes less room than a row that has more to say. */
const compact = computed<boolean>(() => nested && isTerminalStatus(activity.status) && !activity.reason && !steps);
</script>

<template>
  <div
    class="flex items-start gap-2.5 px-1 rounded"
    :class="[compact ? 'py-0.5' : 'py-1.5', { 'bg-rui-error/5': isFailed && !steps }]"
    data-testid="dock-activity-row"
  >
    <RuiProgress
      v-if="showMeter"
      class="shrink-0 mt-0.5"
      color="primary"
      circular
      variant="determinate"
      :value="percentage"
      size="16"
      thickness="2"
      role="img"
      :aria-label="outcomeText"
      data-testid="activity-outcome"
    />
    <RuiTooltip
      v-else
      class="shrink-0 mt-0.5"
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiIcon
          :name="outcome.icon"
          size="16"
          :class="TEXT_COLOR[outcome.color]"
          role="img"
          :aria-label="outcomeText"
          data-testid="activity-outcome"
        />
      </template>
      {{ outcomeText }}
    </RuiTooltip>

    <div class="flex flex-col flex-1 min-w-0 gap-0.5">
      <div
        class="truncate text-sm leading-5"
        :class="[nested ? 'font-normal' : 'font-medium', { 'text-rui-text-secondary': isTerminalStatus(activity.status) && !isFailed }]"
        :title="label"
      >
        {{ label }}
      </div>
      <div
        v-if="secondary"
        class="truncate text-xs leading-4 text-rui-text-secondary"
        :title="secondary"
      >
        {{ secondary }}
      </div>
      <DockActivityDetail :activity="activity" />
      <div
        v-if="activity.reason"
        class="text-xs leading-4 break-words"
        :class="reasonColor"
        data-testid="activity-reason"
      >
        {{ activity.reason }}
      </div>
      <div
        v-if="showMeter"
        class="flex items-center gap-2"
        data-testid="activity-meter"
      >
        <div class="h-1 flex-1 rounded-full bg-rui-grey-200 dark:bg-rui-grey-800 overflow-hidden">
          <div
            class="h-full bg-rui-primary transition-[width] duration-500"
            :style="{ width: `${percentage}%` }"
          />
        </div>
        <span class="text-xs text-rui-text-secondary tabular-nums shrink-0">{{ count }}</span>
      </div>
      <slot
        v-else
        name="summary"
      >
        <div
          v-if="steps && steps.total > 0"
          class="text-xs leading-4 text-rui-text-secondary tabular-nums"
        >
          {{ t('pending_task.steps', { current: steps.current, total: steps.total }) }}
        </div>
      </slot>
    </div>

    <div class="flex items-center gap-1 shrink-0">
      <span
        v-if="elapsed"
        class="text-xs text-rui-text-secondary tabular-nums"
      >
        {{ elapsed }}
      </span>
      <RuiTooltip
        v-if="cancellable && !isTerminalStatus(activity.status)"
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            color="primary"
            size="sm"
            icon
            data-testid="cancel-activity"
            @click="emit('cancel', activity)"
          >
            <RuiIcon
              name="lu-x"
              size="16"
            />
          </RuiButton>
        </template>
        {{ t('collapsed_pending_tasks.cancel_task') }}
      </RuiTooltip>
      <RuiButton
        v-if="retryable"
        variant="text"
        color="primary"
        size="sm"
        data-testid="retry-activity"
        @click="emit('retry', activity)"
      >
        {{ t('pending_task.retry') }}
      </RuiButton>
      <RuiButton
        v-if="dismissible"
        variant="text"
        color="primary"
        size="sm"
        data-testid="dismiss-activity"
        @click="emit('dismiss', activity)"
      >
        {{ t('pending_task.dismiss') }}
      </RuiButton>
    </div>
  </div>
</template>
