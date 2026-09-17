<script setup lang="ts">
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { type ActivityOutcome, activityOutcome } from '@/modules/task-center/activity-outcome';
import { type ActivitySubject, activitySubject } from '@/modules/task-center/activity-subject';
import DockActivityDetail from '@/modules/task-center/components/DockActivityDetail.vue';
import { formatElapsed } from '@/modules/task-center/core/elapsed';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { type Activity, ActivityKind, ActivityStatus, type ActivitySteps } from '@/modules/task-center/core/types';
import { useActivityLabel } from '@/modules/task-center/use-activity-label';

const { activity, dismissible = false, hideReason = false, now, outcomeStatus, parent, percentage, steps } = defineProps<{
  activity: Activity;
  /**
   * The row this one sits under; absent for a job. A child row is labelled by what it acts on, since
   * the job above it already names the work, and says more when that is only what its parent names.
   */
  parent?: Activity;
  /** Ticks once a second, owned by the panel so one timer serves every row. */
  now: number;
  /** 0-100, or `-1` for indeterminate. Parents pass their subtree's; leaves their own. */
  percentage: number;
  /** Present for a parent: the unit tally behind {@link percentage}. */
  steps?: ActivitySteps;
  /** Whether the row offers to dismiss the outcome it reports; the caller decides which outcomes stay until dismissed. */
  dismissible?: boolean;
  /** The status the row reports, when it differs from the activity's own; a parent passes its subtree's failure. */
  outcomeStatus?: ActivityStatus;
  /** Leaves the reason line out, for a row whose reason is already stated once above it. The mark's label keeps it. */
  hideReason?: boolean;
}>();

const emit = defineEmits<{
  cancel: [activity: Activity];
  dismiss: [activity: Activity];
  retry: [activity: Activity];
}>();

defineSlots<{
  /** Replaces the tally line when the row is not showing a progress bar; a settled job puts its outcome here. */
  summary?: () => unknown;
  /** Extra lines under everything else, aligned with the label; a job puts its sections and hints here. */
  details?: () => unknown;
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

const nested = computed<boolean>(() => parent !== undefined);

const label = computed<string>(() => labelOf(activity, get(nested), parent));

const secondary = computed<string | undefined>(() => (get(nested) ? undefined : subtitleOf(activity)));

const subject = computed<ActivitySubject | undefined>(() => activitySubject(activity));

/** A nested account row is named by its address, so it gets the copy and explorer link an address has everywhere else. */
const linkedAddress = computed<boolean>(() => get(nested) && get(subject)?.address !== undefined);

/**
 * The tally the row prints: a parent's leaf count, or a leaf's own steps.
 *
 * An account sync is left out, since its steps are seconds of the queried range; the range line
 * already names those dates, and "86400 of 604800" would say nothing.
 */
const rowSteps = computed<ActivitySteps | undefined>(() => steps ?? (activity.kind === ActivityKind.TX_SYNC ? undefined : activity.steps));

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

const count = computed<string>(() => {
  const tally = get(rowSteps);
  return tally && tally.total > 0
    ? t('pending_task.steps', { current: tally.current, total: tally.total })
    : t('percentage_display.value', { value: percentage });
});

const reasonColor = computed<string>(() => (get(isFailed) ? 'text-rui-error' : 'text-rui-warning'));

const reasonLine = computed<string | undefined>(() => (hideReason ? undefined : activity.reason));

/** A settled child with nothing but its name is one line, so it takes less room than a row that has more to say. */
const compact = computed<boolean>(() => get(nested) && isTerminalStatus(activity.status) && !get(reasonLine) && !get(rowSteps));
</script>

<template>
  <div
    class="flex items-start gap-2.5 px-1 rounded"
    :class="[compact ? 'py-0.5' : 'py-1.5', { 'bg-rui-error/5': isFailed && !steps && !hideReason }]"
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
      <div class="flex items-center gap-1.5 min-w-0">
        <ChainIcon
          v-if="subject?.chain"
          class="shrink-0"
          :chain="subject.chain"
          size="1rem"
          data-testid="dock-subject-icon"
        />
        <LocationIcon
          v-else-if="subject?.location"
          class="shrink-0"
          :item="subject.location"
          icon
          size="16px"
          data-testid="dock-subject-icon"
        />
        <HashLink
          v-if="linkedAddress && subject?.address"
          class="min-w-0 text-sm"
          :text="subject.address"
          :location="subject.chain"
          size="12"
          data-testid="dock-subject-address"
        />
        <div
          v-else
          class="truncate text-sm leading-5"
          :class="[nested ? 'font-normal' : 'font-medium', { 'text-rui-text-secondary': isTerminalStatus(activity.status) && !isFailed }]"
          :title="label"
        >
          {{ label }}
        </div>
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
        v-if="reasonLine"
        class="text-xs leading-4 break-words"
        :class="reasonColor"
        data-testid="activity-reason"
      >
        {{ reasonLine }}
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
          v-if="rowSteps && rowSteps.total > 0"
          class="text-xs leading-4 text-rui-text-secondary tabular-nums"
        >
          {{ t('pending_task.steps', { current: rowSteps.current, total: rowSteps.total }) }}
        </div>
      </slot>
      <slot name="details" />
    </div>

    <div class="flex items-center gap-1 shrink-0">
      <span
        v-if="elapsed"
        class="text-xs text-rui-text-secondary tabular-nums"
      >
        {{ elapsed }}
      </span>
      <RuiTooltip
        v-if="activity.cancellable && !isTerminalStatus(activity.status)"
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
