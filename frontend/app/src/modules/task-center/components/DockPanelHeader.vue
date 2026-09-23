<script setup lang="ts">
import type { StatusTally } from '@/modules/task-center/core/status';
import { ActivityStatus } from '@/modules/task-center/core/types';

const { summary = false, tally, title, total } = defineProps<{
  title: string;
  /** Leaves by status, across every job the panel lists. */
  tally: StatusTally;
  /** Leaves in {@link tally}. */
  total: number;
  /**
   * Whether to draw the bar and count line. A single job's own row already carries both, so the
   * panel only summarises when it lists more than one.
   */
  summary?: boolean;
}>();

const emit = defineEmits<{
  collapse: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const settled = computed<number>(() => tally[ActivityStatus.COMPLETE] + tally[ActivityStatus.FAILED]
  + tally[ActivityStatus.SKIPPED] + tally[ActivityStatus.CANCELLED]);

/** What still needs saying beside the count: failures once there are any, otherwise what is running. */
const detail = computed<{ text: string; failed: boolean } | undefined>(() => {
  const failed = tally[ActivityStatus.FAILED];
  if (failed > 0)
    return { failed: true, text: t('task_dock.panel.detail.failed', { count: failed }) };

  const running = tally[ActivityStatus.RUNNING];
  return running > 0 ? { failed: false, text: t('task_dock.panel.detail.running', { count: running }) } : undefined;
});

/**
 * The bar's coloured segments, in the order they fill: done, failed, skipped, cancelled.
 *
 * @remarks
 * One bar split by outcome rather than a single fill, so a run at 100% with two failures does not
 * read as a clean one before the reader gets to the rows.
 */
const segments = computed<{ key: string; className: string; width: string }[]>(() => {
  if (total === 0)
    return [];

  const width = (count: number): string => `${(count / total) * 100}%`;
  return [
    { className: 'bg-rui-success', count: tally[ActivityStatus.COMPLETE], key: 'complete' },
    { className: 'bg-rui-error', count: tally[ActivityStatus.FAILED], key: 'failed' },
    { className: 'bg-rui-warning', count: tally[ActivityStatus.SKIPPED], key: 'skipped' },
    { className: 'bg-rui-grey-400', count: tally[ActivityStatus.CANCELLED], key: 'cancelled' },
  ].filter(segment => segment.count > 0).map(({ className, count, key }) => ({ className, key, width: width(count) }));
});
</script>

<template>
  <div
    class="flex flex-col gap-1.5"
    data-testid="dock-panel-header"
  >
    <div class="flex items-center justify-between gap-2 min-w-0">
      <div class="font-medium leading-6 truncate">
        {{ title }}
      </div>
      <RuiTooltip
        class="shrink-0"
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            class="-m-1"
            variant="text"
            icon
            size="sm"
            :aria-label="t('pending_task.collapse')"
            data-testid="dock-panel-collapse"
            @click="emit('collapse')"
          >
            <RuiIcon name="lu-chevron-down" />
          </RuiButton>
        </template>
        {{ t('pending_task.collapse') }}
      </RuiTooltip>
    </div>
    <template v-if="summary && total > 0">
      <div
        class="flex h-1 rounded-full bg-rui-grey-200 dark:bg-rui-grey-800 overflow-hidden"
        role="progressbar"
        aria-valuemin="0"
        :aria-valuemax="total"
        :aria-valuenow="settled"
        :aria-label="t('task_dock.panel.settled', { settled, total })"
      >
        <div
          v-for="segment in segments"
          :key="segment.key"
          class="h-full transition-[width] duration-500"
          :class="segment.className"
          :style="{ width: segment.width }"
          :data-testid="`dock-panel-bar-${segment.key}`"
        />
      </div>
      <div class="flex items-center justify-between gap-2 text-xs leading-4 tabular-nums">
        <span
          class="text-rui-text-secondary"
          data-testid="dock-panel-settled"
        >
          {{ t('task_dock.panel.settled', { settled, total }) }}
        </span>
        <span
          v-if="detail"
          :class="detail.failed ? 'text-rui-error font-medium' : 'text-rui-text-secondary'"
          data-testid="dock-panel-detail"
        >
          {{ detail.text }}
        </span>
      </div>
    </template>
  </div>
</template>
