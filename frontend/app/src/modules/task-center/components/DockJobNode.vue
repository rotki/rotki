<script setup lang="ts">
import DockActivityRow from '@/modules/task-center/components/DockActivityRow.vue';
import DockOutcomeSummary from '@/modules/task-center/components/DockOutcomeSummary.vue';
import { isTerminalStatus, type StatusTally, tallyStatuses } from '@/modules/task-center/core/status';
import { someInSubtree, subtreeLeaves, subtreeProgress, subtreeSteps } from '@/modules/task-center/core/tree';
import { type Activity, type ActivityId, ActivityStatus, type ActivitySteps } from '@/modules/task-center/core/types';

const { activity, children, depth = 0, dismissible = false, now } = defineProps<{
  activity: Activity;
  /** The whole tree, passed down rather than looked up per node. */
  children: ReadonlyMap<ActivityId, Activity[]>;
  now: number;
  depth?: number;
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
 * Whether this node's children are shown. Every parent starts closed, at every depth.
 *
 * @remarks
 * The rolled-up row already answers what a reader arrives asking: what is running, and how far
 * along. A parent that opened its own fan-out pushed the other jobs off the panel in order to
 * repeat that, so expanding is left as a deliberate click.
 */
const expanded = ref<boolean>(false);

const descendants = computed<Activity[]>(() => children.get(activity.id) ?? []);

const isParent = computed<boolean>(() => get(descendants).length > 0);

/** A parent counts its subtree's leaves, so its bar and its "4 of 11" agree. */
const steps = computed<ActivitySteps | undefined>(() => (get(isParent) ? subtreeSteps(children, activity) : undefined));

/** A parent rolls its subtree up, giving each leaf fractional credit for its own progress. */
const percentage = computed<number>(() => (get(isParent) ? subtreeProgress(children, activity) : activity.percentage));

/**
 * A parent completes once its children settle, however they settled, so its own COMPLETE would
 * show a success check beside a failed chain. A completed parent reports a failure anywhere
 * beneath it instead; a cancelled one keeps saying so, since the user stopped it.
 */
const outcomeStatus = computed<ActivityStatus | undefined>(() => {
  const failedBeneath = get(isParent)
    && activity.status === ActivityStatus.COMPLETE
    && someInSubtree(children, activity, child => child.status === ActivityStatus.FAILED);
  return failedBeneath ? ActivityStatus.FAILED : undefined;
});

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
  return subtreeLeaves(children, activity).filter(leaf => leaf.status === ActivityStatus.FAILED);
});

const hiddenCount = computed<number>(() => (get(steps)?.total ?? 0) - get(failedLeaves).length);

/** A settled parent's leaves by status, which its row shows in place of a tally that is now always full. */
const leafTally = computed<StatusTally | undefined>(() => (get(isParent) && isTerminalStatus(activity.status)
  ? tallyStatuses(subtreeLeaves(children, activity).map(leaf => leaf.status))
  : undefined));
</script>

<template>
  <div class="flex flex-col">
    <div class="flex items-start gap-1">
      <RuiButton
        v-if="isParent"
        variant="text"
        size="sm"
        icon
        class="shrink-0 mt-0.5"
        :aria-expanded="expanded"
        :aria-label="expanded ? t('pending_task.collapse') : t('pending_task.expand')"
        @click="expanded = !expanded"
      >
        <RuiIcon
          :name="expanded ? 'lu-chevron-down' : 'lu-chevron-right'"
          size="16"
        />
      </RuiButton>
      <div
        v-else-if="depth > 0"
        class="w-6 shrink-0"
      />

      <DockActivityRow
        class="flex-1 min-w-0"
        :activity="activity"
        :now="now"
        :percentage="percentage"
        :steps="steps"
        :cancellable="activity.cancellable"
        :dismissible="dismissible"
        :outcome-status="outcomeStatus"
        :nested="depth > 0"
        @cancel="emit('cancel', $event)"
        @dismiss="emit('dismiss', $event)"
        @retry="emit('retry', $event)"
      >
        <template
          v-if="leafTally"
          #summary
        >
          <DockOutcomeSummary :tally="leafTally" />
        </template>
      </DockActivityRow>
    </div>

    <!--
      16px of indent per level, not 24. The panel is 400px and a history refresh nests three deep,
      so the wider step spent a fifth of the width on guide lines and truncated the labels instead.
    -->
    <div
      v-if="isParent && expanded"
      class="flex flex-col ml-2 pl-2 border-l border-default"
    >
      <DockJobNode
        v-for="child in descendants"
        :key="child.id"
        :activity="child"
        :children="children"
        :now="now"
        :depth="depth + 1"
        @cancel="emit('cancel', $event)"
        @retry="emit('retry', $event)"
      />
    </div>
    <div
      v-else-if="failedLeaves.length > 0"
      class="flex flex-col ml-2 pl-2 border-l border-default"
      data-testid="dock-failed-leaves"
    >
      <div
        v-for="leaf in failedLeaves"
        :key="leaf.id"
        class="flex items-start gap-1"
      >
        <div class="w-6 shrink-0" />
        <DockActivityRow
          class="flex-1 min-w-0"
          :activity="leaf"
          :now="now"
          :percentage="leaf.percentage"
          :cancellable="false"
          nested
          @retry="emit('retry', $event)"
        />
      </div>
      <!-- The same spacers a row has before its label, so the button's text lines up with the labels above it. -->
      <div
        v-if="hiddenCount > 0"
        class="flex items-center gap-1"
      >
        <div class="w-6 shrink-0" />
        <div class="flex items-center gap-2.5 px-1">
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
  </div>
</template>
