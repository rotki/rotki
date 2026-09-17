<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { JobBreakdownEntry } from '@/modules/task-center/use-job-breakdown';
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

/**
 * The one coloured element per section. Trouble outranks completion, so a fully counted section
 * with a failure beneath it never reads as a clean one; unfinished work waits in grey rather than
 * spinning, since a column of spinners says less than the job's own bar.
 */
function markOf(entry: JobBreakdownEntry): SectionMark {
  if (entry.problem === ActivityStatus.FAILED)
    return { className: 'text-rui-error', icon: 'lu-circle-x', label: t('pending_task.status.failed') };
  if (entry.problem === ActivityStatus.CANCELLED)
    return { className: 'text-rui-warning', icon: 'lu-circle-alert', label: t('pending_task.status.cancelled') };
  if (entry.total > 0 && entry.settled === entry.total)
    return { className: 'text-rui-success', icon: 'lu-circle-check', label: t('pending_task.status.done') };
  return { className: 'text-rui-text-disabled', icon: 'lu-clock', label: t('pending_task.status.running') };
}
</script>

<template>
  <div
    class="flex flex-wrap gap-x-3 gap-y-0.5 text-xs leading-5 text-rui-text-secondary"
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
