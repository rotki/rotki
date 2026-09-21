<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { JobBreakdownEntry } from '@/modules/task-center/use-job-breakdown';
import { type ActivityOutcome, activityOutcome } from '@/modules/task-center/activity-outcome';
import { ActivityStatus } from '@/modules/task-center/core/types';

defineProps<{
  entries: JobBreakdownEntry[];
}>();

const { t } = useI18n({ useScope: 'global' });

interface SectionMark {
  readonly icon: RuiIcons;
  readonly className: string;
  readonly label: string;
}

/** Tailwind only sees class names written out in full, so each outcome colour is spelled here. */
const TEXT_COLOR: Record<ActivityOutcome['color'], string> = {
  error: 'text-rui-error',
  grey: 'text-rui-text-secondary',
  primary: 'text-rui-primary',
  success: 'text-rui-success',
  warning: 'text-rui-warning',
};

/** The status a section reads as. Trouble outranks completion, so a fully counted section with a failure beneath it never reads as a clean one. */
function statusOf(entry: JobBreakdownEntry): ActivityStatus {
  if (entry.problem !== undefined)
    return entry.problem;
  return entry.total > 0 && entry.settled === entry.total ? ActivityStatus.COMPLETE : ActivityStatus.PENDING;
}

/**
 * The one coloured element per section, in the same icons and colours a row's mark uses, so a
 * cancelled section and a cancelled row read alike. Unfinished work waits rather than spinning,
 * since a column of spinners says less than the job's own bar.
 */
function markOf(entry: JobBreakdownEntry): SectionMark {
  const status = statusOf(entry);
  const { color, icon, key } = activityOutcome(status);
  const label = status === ActivityStatus.PENDING ? t('pending_task.status.running') : t(key);
  return { className: TEXT_COLOR[color], icon, label };
}
</script>

<template>
  <div
    class="flex flex-wrap gap-x-3 gap-y-1 text-xs leading-4 text-rui-text-secondary"
    data-testid="dock-job-breakdown"
  >
    <div
      v-for="entry in entries"
      :key="entry.key"
      class="flex items-center gap-1 whitespace-nowrap"
      data-testid="dock-job-breakdown-entry"
    >
      <RuiIcon
        :name="markOf(entry).icon"
        size="12"
        class="shrink-0"
        :class="markOf(entry).className"
        role="img"
        :aria-label="markOf(entry).label"
        data-testid="dock-job-breakdown-mark"
      />
      <span>{{ entry.label }}</span>
      <span class="tabular-nums text-rui-text">
        {{ t('task_dock.panel.breakdown_count', { settled: entry.settled, total: entry.total }) }}
      </span>
    </div>
  </div>
</template>
