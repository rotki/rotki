<script setup lang="ts">
import DockActivityRow from '@/modules/task-center/components/DockActivityRow.vue';
import DockFailedGroup from '@/modules/task-center/components/DockFailedGroup.vue';
import DockJobBreakdown from '@/modules/task-center/components/DockJobBreakdown.vue';
import DockOutcomeSummary from '@/modules/task-center/components/DockOutcomeSummary.vue';
import DockSkippedGroup from '@/modules/task-center/components/DockSkippedGroup.vue';
import DockSyncHint from '@/modules/task-center/components/DockSyncHint.vue';
import { isTerminalStatus, type StatusTally, tallyStatuses } from '@/modules/task-center/core/status';
import { someInSubtree, subtreeLeaves, subtreeProgress, subtreeSteps } from '@/modules/task-center/core/tree';
import { type Activity, type ActivityId, ActivityKind, ActivityStatus, type ActivitySteps } from '@/modules/task-center/core/types';
import { arrangeChildren, type DockChildEntry, groupFailedLeaves } from '@/modules/task-center/dock-children';
import { type JobBreakdownEntry, useJobBreakdown } from '@/modules/task-center/use-job-breakdown';

const { activity, children, depth = 0, dismissible = false, now, parent } = defineProps<{
  activity: Activity;
  /** The whole tree, passed down rather than looked up per node. */
  children: ReadonlyMap<ActivityId, Activity[]>;
  now: number;
  depth?: number;
  /** The node this one is unfolded under; absent for a job. */
  parent?: Activity;
  /** Offers a dismiss control on this row only; the outcome it reports covers the whole subtree. */
  dismissible?: boolean;
}>();

const emit = defineEmits<{
  cancel: [activity: Activity];
  dismiss: [activity: Activity];
  retry: [activity: Activity];
}>();

const { t } = useI18n({ useScope: 'global' });

/**
 * How many entries a settled nested parent lists before a "show more", as the sync panel did per
 * chain. A job's own children (the chains of a refresh) are all listed, since they are what it is
 * made of, and so is a running parent's, since a cap over rows in start order would hide the ones
 * still working.
 */
const NESTED_LIMIT = 5;

/**
 * Whether this node's children are shown. Every parent starts closed, at every depth.
 *
 * @remarks
 * The rolled-up row already answers what a reader arrives asking: what is running, and how far
 * along. A parent that opened its own fan-out pushed the other jobs off the panel in order to
 * repeat that, so expanding is left as a deliberate click.
 */
const expanded = ref<boolean>(false);

const showAll = ref<boolean>(false);

const jobBreakdown = useJobBreakdown(() => activity, () => children);

const descendants = computed<Activity[]>(() => children.get(activity.id) ?? []);

/** How a child ended: a completed parent over a failure reads as failed, as its own row does. */
function outcomeOf(child: Activity): ActivityStatus {
  return child.status === ActivityStatus.COMPLETE && someInSubtree(children, child, node => node.status === ActivityStatus.FAILED)
    ? ActivityStatus.FAILED
    : child.status;
}

/** The unfolded children: start order while the job runs, sorted and grouped once it settles. */
const entries = computed<DockChildEntry[]>(() => arrangeChildren(
  get(descendants),
  isTerminalStatus(activity.status),
  child => (children.get(child.id)?.length ?? 0) === 0,
  outcomeOf,
));

const limited = computed<boolean>(() => depth > 0
  && isTerminalStatus(activity.status)
  && !get(showAll)
  && get(entries).length > NESTED_LIMIT);

const visibleEntries = computed<DockChildEntry[]>(() => (get(limited) ? get(entries).slice(0, NESTED_LIMIT) : get(entries)));

const isParent = computed<boolean>(() => get(descendants).length > 0);

const toggleLabel = computed<string>(() => (get(expanded) ? t('pending_task.collapse') : t('pending_task.expand')));

/** Sections are a job's summary; a nested parent is itself one section's row. */
const breakdown = computed<JobBreakdownEntry[]>(() => (depth === 0 ? get(jobBreakdown) : []));

/** The sync hint explains a history refresh, so it sits under that job, and only while it runs. */
const showSyncHint = computed<boolean>(() => depth === 0 && activity.kind === ActivityKind.HISTORY_SYNC && !isTerminalStatus(activity.status));

/** A parent counts the units it is named by, so its bar and its "3 of 5" agree. See `subtreeUnits`. */
const steps = computed<ActivitySteps | undefined>(() => (get(isParent) ? subtreeSteps(children, activity) : undefined));

/** A parent rolls its units up, giving each its fractional progress. */
const percentage = computed<number>(() => (get(isParent) ? subtreeProgress(children, activity) : activity.percentage));

/**
 * A parent completes once its children settle, however they settled, so its own COMPLETE would
 * show a success check beside a failed chain. A completed parent reports a failure anywhere
 * beneath it instead; a cancelled one keeps saying so, since the user stopped it.
 */
const outcomeStatus = computed<ActivityStatus | undefined>(() => {
  const outcome = outcomeOf(activity);
  return outcome === activity.status ? undefined : outcome;
});

/** A parent that settles with its first child's error would say it twice; the children beneath say it once. */
const repeatsChildReason = computed<boolean>(() => get(isParent)
  && activity.reason !== undefined
  && someInSubtree(children, activity, child => child.id !== activity.id && child.reason === activity.reason));

const leaves = computed<Activity[]>(() => (get(isParent) ? subtreeLeaves(children, activity) : []));

/**
 * The failed leaves of a settled job, shown under it while it stays folded.
 *
 * @remarks
 * Folding keeps a 21-chain job to one row, but a failure is the one part a reader has to act on,
 * so it should not take a click to find. Only a settled job surfaces them: while work runs a leaf
 * can still fail, and rows appearing under a job mid-run would jump the list.
 */
const failedLeaves = computed<Activity[]>(() => {
  if (!get(isParent) || !isTerminalStatus(activity.status))
    return [];
  return get(leaves).filter(leaf => leaf.status === ActivityStatus.FAILED);
});

const failedEntries = computed<DockChildEntry[]>(() => groupFailedLeaves(get(failedLeaves)));

const hiddenCount = computed<number>(() => get(leaves).length - get(failedLeaves).length);

/** A settled parent's leaves by status, which its row shows in place of a tally that is now always full. */
const leafTally = computed<StatusTally | undefined>(() => (get(isParent) && isTerminalStatus(activity.status)
  ? tallyStatuses(get(leaves).map(leaf => leaf.status))
  : undefined));
</script>

<template>
  <div class="flex flex-col">
    <DockActivityRow
      :activity="activity"
      :now="now"
      :percentage="percentage"
      :steps="steps"
      :dismissible="dismissible"
      :outcome-status="outcomeStatus"
      :parent="parent"
      :hide-reason="repeatsChildReason"
      @cancel="emit('cancel', $event)"
      @dismiss="emit('dismiss', $event)"
      @retry="emit('retry', $event)"
    >
      <template
        v-if="isParent"
        #toggle
      >
        <RuiTooltip
          :options="{ placement: 'top' }"
          :open-delay="400"
        >
          <template #activator>
            <RuiButton
              variant="text"
              size="sm"
              icon
              :aria-expanded="expanded"
              :aria-label="toggleLabel"
              data-testid="dock-job-toggle"
              @click="expanded = !expanded"
            >
              <RuiIcon
                :name="expanded ? 'lu-chevron-down' : 'lu-chevron-right'"
                size="16"
              />
            </RuiButton>
          </template>
          {{ toggleLabel }}
        </RuiTooltip>
      </template>
      <template
        v-if="leafTally"
        #summary
      >
        <DockOutcomeSummary :tally="leafTally" />
      </template>
      <template
        v-if="breakdown.length > 0 || showSyncHint"
        #details
      >
        <DockJobBreakdown
          v-if="breakdown.length > 0"
          class="mt-1"
          :entries="breakdown"
        />
        <DockSyncHint
          v-if="showSyncHint"
          class="mt-1"
        />
      </template>
    </DockActivityRow>

    <!--
      16px of indent per level, not 24. The panel is 400px and a history refresh nests three deep,
      so the wider step spent a fifth of the width on guide lines and truncated the labels instead.
    -->
    <div
      v-if="isParent && expanded"
      class="flex flex-col ml-2 pl-2 border-l border-default"
    >
      <template
        v-for="entry in visibleEntries"
        :key="entry.type === 'node' ? entry.activity.id : entry.key"
      >
        <DockJobNode
          v-if="entry.type === 'node'"
          :activity="entry.activity"
          :children="children"
          :now="now"
          :depth="depth + 1"
          :parent="activity"
          @cancel="emit('cancel', $event)"
          @retry="emit('retry', $event)"
        />
        <DockFailedGroup
          v-else-if="entry.type === 'failed'"
          :activities="entry.activities"
          :reason="entry.reason"
          :parent="activity"
          :now="now"
          @retry="emit('retry', $event)"
        />
        <DockSkippedGroup
          v-else
          :activities="entry.activities"
          :reason="entry.reason"
        />
      </template>
      <RuiButton
        v-if="limited"
        class="self-start"
        variant="text"
        size="sm"
        data-testid="dock-show-more-children"
        @click="showAll = true"
      >
        {{ t('task_dock.panel.show_all', { count: entries.length - NESTED_LIMIT }, entries.length - NESTED_LIMIT) }}
      </RuiButton>
    </div>
    <div
      v-else-if="failedLeaves.length > 0"
      class="flex flex-col ml-2 pl-2 border-l border-default"
      data-testid="dock-failed-leaves"
    >
      <template
        v-for="entry in failedEntries"
        :key="entry.type === 'node' ? entry.activity.id : entry.key"
      >
        <DockActivityRow
          v-if="entry.type === 'node'"
          :activity="entry.activity"
          :now="now"
          :percentage="entry.activity.percentage"
          :parent="activity"
          @retry="emit('retry', $event)"
        />
        <DockFailedGroup
          v-else-if="entry.type === 'failed'"
          :activities="entry.activities"
          :reason="entry.reason"
          :parent="activity"
          :now="now"
          @retry="emit('retry', $event)"
        />
      </template>
      <!-- The same spacer a row has for its icon, so the button's text lines up with the labels above it. -->
      <div
        v-if="hiddenCount > 0"
        class="flex items-center gap-2.5 px-1"
      >
        <div class="w-4 shrink-0" />
        <RuiButton
          class="-ml-2"
          variant="text"
          size="sm"
          data-testid="dock-show-all"
          @click="expanded = true"
        >
          {{ t('task_dock.panel.show_all', { count: hiddenCount }, hiddenCount) }}
        </RuiButton>
      </div>
    </div>
  </div>
</template>
