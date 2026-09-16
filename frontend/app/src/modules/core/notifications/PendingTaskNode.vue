<script setup lang="ts">
import PendingTask from '@/modules/core/notifications/PendingTask.vue';
import { someInSubtree, subtreeProgress, subtreeSteps } from '@/modules/task-center/core/tree';
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

/** A parent counts its subtree's leaves, so its ring and its "4 of 11" agree. */
const steps = computed<ActivitySteps | undefined>(() => (get(isParent) ? subtreeSteps(children, activity) : undefined));

/** A parent rolls its subtree up, giving each leaf fractional credit for its own progress. */
const percentage = computed<number>(() => (get(isParent) ? subtreeProgress(children, activity) : activity.percentage));

/**
 * A parent's stop control ends its whole subtree, because `orchestrator.cancel` cascades: the
 * settle walks the children, each of which walks its own. Until that landed this row deliberately
 * rendered no control at all — cancelling a parent settled its row and stopped nothing, since the
 * handle only aborts a backend task id an umbrella never has.
 */
const cancellable = computed<boolean>(() => activity.cancellable);

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

      <PendingTask
        class="flex-1 min-w-0 py-1.5"
        :activity="activity"
        :now="now"
        :percentage="percentage"
        :steps="steps"
        :cancellable="cancellable"
        :dismissible="dismissible"
        :outcome-status="outcomeStatus"
        :nested="depth > 0"
        @cancel="emit('cancel', $event)"
        @dismiss="emit('dismiss', $event)"
      />
    </div>

    <!--
      16px of indent per level, not 24. The drawer is 400px and a history refresh nests three deep,
      so the wider step spent a fifth of the width on guide lines and truncated the labels instead.
    -->
    <div
      v-if="isParent && expanded"
      class="flex flex-col ml-2 pl-2 border-l border-default"
    >
      <PendingTaskNode
        v-for="child in descendants"
        :key="child.id"
        :activity="child"
        :children="children"
        :now="now"
        :depth="depth + 1"
        @cancel="emit('cancel', $event)"
      />
    </div>
  </div>
</template>
