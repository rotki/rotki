<script setup lang="ts">
import type { StatusTally } from '@/modules/task-center/core/status';
import { ActivityStatus } from '@/modules/task-center/core/types';

const { tally } = defineProps<{
  /** A settled job's leaves, by status. */
  tally: StatusTally;
}>();

const { t } = useI18n({ useScope: 'global' });

/** A dot before every part but the first, drawn in CSS so it is neither translated nor read aloud. */
const SEPARATOR = 'before:content-[\'·\'] before:mx-1 before:text-rui-text-secondary';

/**
 * How a settled job ended, one part per outcome anyone had, failures last so the eye ends on them.
 *
 * @remarks
 * Only a failure is coloured. A skip or a cancel is expected, and the rows beneath already mark it
 * in their own colour; repeating it here made a benign "13 skipped" the loudest line of the job.
 *
 * Replaces a job's "21 of 21" once it settles: every leaf is counted by then, so the tally says
 * nothing, while how many were skipped or failed is the one thing the row cannot otherwise show.
 */
const parts = computed<{ key: string; text: string; className: string }[]>(() => [
  { className: 'text-rui-text-secondary', count: tally[ActivityStatus.COMPLETE], key: 'done', text: t('task_dock.panel.outcome.done', { count: tally[ActivityStatus.COMPLETE] }) },
  { className: 'text-rui-text-secondary', count: tally[ActivityStatus.SKIPPED], key: 'skipped', text: t('task_dock.panel.outcome.skipped', { count: tally[ActivityStatus.SKIPPED] }) },
  { className: 'text-rui-text-secondary', count: tally[ActivityStatus.CANCELLED], key: 'cancelled', text: t('task_dock.panel.outcome.cancelled', { count: tally[ActivityStatus.CANCELLED] }) },
  { className: 'text-rui-error font-medium', count: tally[ActivityStatus.FAILED], key: 'failed', text: t('task_dock.panel.outcome.failed', { count: tally[ActivityStatus.FAILED] }) },
]
  .filter(part => part.count > 0)
  .map(({ className, key, text }, index) => ({ className: index > 0 ? `${className} ${SEPARATOR}` : className, key, text })));
</script>

<template>
  <div
    class="text-xs leading-4 tabular-nums"
    data-testid="dock-outcome-summary"
  >
    <span
      v-for="part in parts"
      :key="part.key"
      :class="part.className"
      :data-testid="`dock-outcome-${part.key}`"
    >
      {{ part.text }}
    </span>
  </div>
</template>
