<script setup lang="ts">
import { useScramble } from '@/modules/settings/use-scramble';
import { type ActivityOutcome, activityOutcome } from '@/modules/task-center/activity-outcome';
import { formatElapsed } from '@/modules/task-center/core/elapsed';
import { isTerminalStatus } from '@/modules/task-center/core/status';
import { type Activity, ActivityStatus, type ActivitySteps, type ActivityText, resolveText } from '@/modules/task-center/core/types';

const { activity, cancellable, nested = false, now, percentage, steps } = defineProps<{
  activity: Activity;
  /** Ticks once a second, owned by the panel so one timer serves every row. */
  now: number;
  /** 0-100, or `-1` for indeterminate. Parents pass their subtree's; leaves their own. */
  percentage: number;
  /** Present for a parent: the leaf tally behind {@link percentage}. */
  steps?: ActivitySteps;
  /** Decided by the caller — a parent is not cancellable until cancel cascades. */
  cancellable: boolean;
  /** A child row: the job above it already names the work, so its own label is enough. */
  nested?: boolean;
}>();

const emit = defineEmits<{
  cancel: [activity: Activity];
}>();

const { t } = useI18n({ useScope: 'global' });

const { scrambleAddress } = useScramble();

/**
 * Rewrites a param that may hold one address or several.
 *
 * @remarks
 * A batch joins several addresses into one string, so each is scrambled separately and the
 * separators put back verbatim. `scrambleAddress` returns its input unchanged while privacy mode
 * is off, so this needs no condition of its own.
 *
 * @param value a subtitle param, which is only rewritten when it is a string
 * @returns the value with each address replaced
 */
function scrambleAddresses(value: unknown): unknown {
  if (typeof value !== 'string')
    return value;

  return value
    .split(/([\s,]+)/)
    .map(part => (/^[\s,]*$/.test(part) ? part : scrambleAddress(part)))
    .join('');
}

/**
 * The subtitle with its address param scrambled, before {@link resolveText} interpolates it —
 * afterwards nothing can tell the address apart from the wording around it. Every producer that
 * carries an address passes it as `address`, so that is the one key rewritten.
 */
const displaySubtitle = computed<ActivityText | undefined>(() => {
  const value = activity.subtitle;
  if (value === undefined || typeof value === 'string' || value.params?.address === undefined)
    return value;

  return { ...value, params: { ...value.params, address: scrambleAddresses(value.params.address) } };
});

// Resolved here rather than at submit time, so a language change updates work already in flight.
const subtitle = computed<string | undefined>(() => resolveText(t, get(displaySubtitle)));

// A child of "History refresh" reads better as "Ethereum" than as "Transaction sync / Ethereum":
// a chain and its accounts carry the same title, so under a parent the subtitle is the identity.
const label = computed<string>(() => (nested ? get(subtitle) ?? activity.title : activity.title));

const secondary = computed<string | undefined>(() => (nested ? undefined : get(subtitle)));

const isRunning = computed<boolean>(() => activity.status === ActivityStatus.RUNNING);

// `-1` is the orchestrator's "indeterminate": no producer reported steps for this activity.
const hasDeterminateProgress = computed<boolean>(() => percentage >= 0);

const elapsed = computed<string | undefined>(() => {
  if (!get(isRunning) || activity.startedAt === undefined)
    return undefined;

  return formatElapsed(now - activity.startedAt);
});

const meta = computed<string | undefined>(() => {
  const parts: string[] = [];
  const elapsedTime = get(elapsed);
  if (elapsedTime)
    parts.push(elapsedTime);

  if (steps && steps.total > 0)
    parts.push(t('pending_task.steps', { current: steps.current, total: steps.total }));

  return parts.length > 0 ? parts.join(' · ') : undefined;
});

const outcome = computed<ActivityOutcome>(() => activityOutcome(activity.status));

/**
 * The status word, plus the producer's reason when there is one ("Skipped: disabled in settings").
 *
 * Used for the tooltip and the `aria-label` alike, so the reason is not sighted-hover-only — the
 * chip is icon-only, and this is the sole place a skip's reason is ever shown.
 */
const outcomeText = computed<string>(() => {
  const status = t(get(outcome).key);
  const { reason } = activity;
  return reason ? t('pending_task.status.with_reason', { reason, status }) : status;
});

// The ring only earns the slot when it has a real number to put in it. Everything else — including
// a running row the producer never counted steps for — says its status in words instead.
const showRing = computed<boolean>(() => get(isRunning) && get(hasDeterminateProgress));
</script>

<template>
  <div class="flex items-center justify-between flex-nowrap gap-3">
    <div class="flex flex-col flex-1 min-w-0 gap-0.5">
      <!--
        `truncate`, not `text-ellipsis`: the latter is inert without `whitespace-nowrap`, so every
        long chain name wrapped to two lines and the panel had no vertical rhythm at all. One line
        per row, with the full text on hover.
      -->
      <div
        class="truncate text-sm leading-5"
        :class="[nested ? 'font-normal' : 'font-medium', { 'text-rui-text-secondary': isTerminalStatus(activity.status) }]"
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
      <div
        v-if="meta"
        class="text-xs leading-4 text-rui-text-secondary tabular-nums"
      >
        {{ meta }}
      </div>
    </div>

    <RuiProgress
      v-if="showRing"
      color="primary"
      circular
      variant="determinate"
      :value="percentage"
      size="24"
      show-label
      thickness="2"
    />
    <!--
      Icon only. The drawer is 400px and a nested row spends most of it on its label; "Refreshing
      Arbitrum One" wrapped to two lines to make room for the word "Running". Colour plus icon
      carries the status, the tooltip carries the word, and `aria-label` keeps it for anyone not
      reading either.
    -->
    <RuiTooltip
      v-else
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <!--
          ⚠️ `role` and `tabindex` are overrides, not decoration. RuiChip hardcodes `role="button"`
          and `tabindex="0"` on its root whether or not it is clickable, so an untouched status chip
          is a focusable fake button: a keyboard user tabs through a "Done" button on every row and
          hears one announced per settled child. `role="img"` makes the icon carry its `aria-label`.
        -->
        <RuiChip
          size="sm"
          role="img"
          tabindex="-1"
          :color="outcome.color"
          :variant="outcome.variant"
          :aria-label="outcomeText"
          :class-names="{ content: '!px-1' }"
          class="shrink-0"
          data-testid="activity-outcome"
        >
          <RuiIcon
            :name="outcome.icon"
            size="14"
          />
        </RuiChip>
      </template>
      <span data-testid="activity-outcome-text">{{ outcomeText }}</span>
    </RuiTooltip>

    <RuiTooltip
      v-if="cancellable"
      :popper="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          variant="text"
          color="primary"
          class="shrink-0"
          size="sm"
          icon
          data-testid="cancel-activity"
          @click="emit('cancel', activity)"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </template>
      {{ t('collapsed_pending_tasks.cancel_task') }}
    </RuiTooltip>
  </div>
</template>
