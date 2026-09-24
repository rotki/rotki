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
import { useWaitingLabel } from '@/modules/task-center/use-waiting-label';

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
  /**
   * The row's last control; a job puts its expand toggle here, so every toggle sits in one column at
   * the row's end. A row without one keeps the space when it has other buttons, so theirs line up.
   */
  toggle?: () => unknown;
}>();

const { t } = useI18n({ useScope: 'global' });

const { labelOf, subtitleOf } = useActivityLabel();
const { waitingLabel } = useWaitingLabel();

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

/**
 * The message key of a top-level subtitle that names the row's own address and nothing else, as
 * "Adding" and the address does, so the address can be drawn as a link inside the sentence. Any other
 * subtitle stays text: the message would lose the params a link slot cannot carry.
 */
const addressSubtitle = computed<string | undefined>(() => {
  const { subtitle } = activity;
  if (get(nested) || subtitle === undefined || typeof subtitle === 'string' || subtitle.plural !== undefined)
    return undefined;
  const params = Object.keys(subtitle.params ?? {});
  return params.length === 1 && subtitle.params?.address === get(subject)?.address ? subtitle.key : undefined;
});

/** The chain or location icon is left off when the parent's row already shows the same one. */
const repeatsParentIcon = computed<boolean>(() => {
  const own = get(subject);
  const above = parent === undefined ? undefined : activitySubject(parent);
  if (own === undefined || above === undefined)
    return false;
  return own.chain !== undefined ? own.chain === above.chain : own.location !== undefined && own.location === above.location;
});

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

/** The mark turns into a progress ring only with a real number to fill it; indeterminate work keeps its icon. */
const showRing = computed<boolean>(() => get(isRunning) && percentage >= 0);

/**
 * A bar only on a job or a parent. A nested leaf sits under its parent's bar, so a second one would
 * repeat it; the ring already carries the leaf's own progress, and a tally it has stays as text.
 */
const showBar = computed<boolean>(() => get(showRing) && (!get(nested) || steps !== undefined));

const count = computed<string>(() => {
  const tally = get(rowSteps);
  return tally && tally.total > 0
    ? t('pending_task.steps', { current: tally.current, total: tally.total })
    : t('percentage_display.value', { value: percentage });
});

const reasonColor = computed<string>(() => (get(isFailed) ? 'text-rui-error' : 'text-rui-warning'));

const reasonLine = computed<string | undefined>(() => (hideReason ? undefined : activity.reason));

const waitingLine = computed<string | undefined>(() => waitingLabel(activity));

/**
 * A settled nested row's label fades, so the rows still working stand out among its siblings. A
 * job's title keeps its strength once settled, since it heads the rows beneath it.
 */
const recedes = computed<boolean>(() => get(nested) && isTerminalStatus(activity.status) && !get(isFailed));

const showsIcon = computed<boolean>(() => (get(subject)?.chain !== undefined || get(subject)?.location !== undefined) && !get(repeatsParentIcon));

/**
 * Whether the row has the fixed-width column its subject icon sits in. A nested row keeps the column
 * even with no icon to show, so its label starts where its siblings' do; an account row is exempt,
 * since its avatar already takes that place.
 */
const iconColumn = computed<boolean>(() => get(showsIcon) || (get(nested) && !get(linkedAddress)));

const cancellable = computed<boolean>(() => activity.cancellable && !isTerminalStatus(activity.status));

const hasButtons = computed<boolean>(() => get(cancellable) || get(retryable) || dismissible);

/** A settled child with nothing but its name is one line, so it takes less room than a row that has more to say. */
const compact = computed<boolean>(() => get(nested) && isTerminalStatus(activity.status) && !get(reasonLine) && !get(rowSteps));
</script>

<template>
  <div
    class="flex items-start gap-2.5 px-1 rounded"
    :class="[compact ? 'py-0.5' : 'py-1.5', { 'bg-rui-error/5': isFailed && !steps && !hideReason }]"
    :data-status="status"
    data-testid="dock-activity-row"
  >
    <RuiProgress
      v-if="showRing"
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

    <!-- The subject icon has a column of its own, so every line of the row starts where the label does. -->
    <div class="flex flex-1 min-w-0 gap-1.5">
      <div
        v-if="iconColumn"
        class="size-5 shrink-0 flex items-center justify-center"
        data-testid="dock-subject-icon-column"
      >
        <ChainIcon
          v-if="subject?.chain && !repeatsParentIcon"
          :chain="subject.chain"
          size="1rem"
          data-testid="dock-subject-icon"
        />
        <LocationIcon
          v-else-if="subject?.location && !repeatsParentIcon"
          :item="subject.location"
          icon
          size="16px"
          data-testid="dock-subject-icon"
        />
      </div>
      <div class="flex flex-col flex-1 min-w-0 gap-0.5">
        <HashLink
          v-if="linkedAddress && subject?.address"
          class="min-w-0 text-sm"
          :text="subject.address"
          :location="subject.chain"
          size="12"
          reveal-actions
          data-testid="dock-subject-address"
        />
        <div
          v-else
          class="truncate text-sm leading-5"
          :class="[nested ? 'font-normal' : 'font-medium', { 'text-rui-text-secondary': recedes }]"
          :title="label"
          data-testid="activity-label"
        >
          {{ label }}
        </div>
        <i18n-t
          v-if="addressSubtitle && subject?.address"
          scope="global"
          tag="div"
          :keypath="addressSubtitle"
          class="flex items-center gap-1 min-w-0 text-xs leading-4 text-rui-text-secondary whitespace-nowrap"
          data-testid="dock-root-address"
        >
          <template #address>
            <HashLink
              class="min-w-0"
              :text="subject.address"
              :location="subject.chain"
              size="12"
              reveal-actions
            />
          </template>
        </i18n-t>
        <div
          v-else-if="secondary"
          class="truncate text-xs leading-4 text-rui-text-secondary"
          :title="secondary"
        >
          {{ secondary }}
        </div>
        <div
          v-if="waitingLine"
          class="text-xs leading-4 text-rui-text-secondary break-words"
          data-testid="activity-waiting"
        >
          {{ waitingLine }}
        </div>
        <div
          v-if="reasonLine"
          class="text-xs leading-4 break-words"
          :class="reasonColor"
          data-testid="activity-reason"
        >
          {{ reasonLine }}
        </div>
        <DockActivityDetail :activity="activity" />
        <div
          v-if="showBar"
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
    </div>

    <div
      class="flex items-center gap-1 shrink-0 -my-0.5"
      data-testid="activity-actions"
    >
      <span
        v-if="elapsed"
        class="text-xs text-rui-text-secondary tabular-nums"
      >
        {{ elapsed }}
      </span>
      <RuiTooltip
        v-if="cancellable"
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            color="primary"
            size="sm"
            icon
            :aria-label="t('task_dock.panel.stop')"
            data-testid="cancel-activity"
            @click="emit('cancel', activity)"
          >
            <RuiIcon
              name="lu-x"
              size="16"
            />
          </RuiButton>
        </template>
        {{ t('task_dock.panel.stop') }}
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
      <RuiTooltip
        v-if="dismissible"
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            color="primary"
            size="sm"
            icon
            :aria-label="t('pending_task.dismiss')"
            data-testid="dismiss-activity"
            @click="emit('dismiss', activity)"
          >
            <RuiIcon
              name="lu-x"
              size="16"
            />
          </RuiButton>
        </template>
        {{ t('pending_task.dismiss') }}
      </RuiTooltip>
      <slot name="toggle">
        <div
          v-if="hasButtons"
          class="size-6 shrink-0"
          data-testid="activity-toggle-slot"
        />
      </slot>
    </div>
  </div>
</template>
