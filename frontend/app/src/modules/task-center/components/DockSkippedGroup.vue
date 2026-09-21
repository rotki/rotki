<script setup lang="ts">
import type { Activity } from '@/modules/task-center/core/types';
import { useActivityLabel } from '@/modules/task-center/use-activity-label';

const { activities, reason } = defineProps<{
  /** The skipped leaves the group stands for, in the order they sorted. */
  activities: Activity[];
  reason: string | undefined;
}>();

const { t } = useI18n({ useScope: 'global' });

const { labelOf } = useActivityLabel();

/** How many names the row spells out before it only counts the rest. */
const NAMED = 3;

const names = computed<string>(() => {
  const labels = activities.map(activity => labelOf(activity, true));
  const shown = labels.slice(0, NAMED).join(', ');
  const rest = labels.length - NAMED;
  return rest > 0 ? t('task_dock.panel.skipped_names_more', { count: rest, names: shown }) : shown;
});
</script>

<template>
  <div
    class="flex items-start gap-2.5 py-1 px-1"
    data-testid="dock-skipped-group"
  >
    <RuiIcon
      name="lu-skip-forward"
      size="16"
      class="shrink-0 mt-0.5 text-rui-warning"
    />
    <!-- The subject icon's slot, empty, so the label lines up with the chain rows beside it. -->
    <div class="size-5 shrink-0 -ml-1" />
    <div class="flex flex-col flex-1 min-w-0 gap-0.5">
      <div class="text-sm leading-5 text-rui-text-secondary">
        {{ t('task_dock.panel.skipped_count', { count: activities.length }, activities.length) }}
      </div>
      <div
        v-if="reason"
        class="text-xs leading-4 text-rui-warning break-words"
      >
        {{ reason }}
      </div>
      <div
        class="text-xs leading-4 text-rui-text-secondary truncate"
        :title="activities.map(activity => labelOf(activity, true)).join(', ')"
        data-testid="dock-skipped-names"
      >
        {{ names }}
      </div>
    </div>
  </div>
</template>
