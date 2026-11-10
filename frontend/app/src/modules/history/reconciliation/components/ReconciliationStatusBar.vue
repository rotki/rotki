<script setup lang="ts">
import type { MessageKey } from '@/message-key';
import type { StatusCounts } from '@/modules/history/reconciliation/schemas';
import { STATUS_LABEL } from '@/modules/history/reconciliation/messages';
import { notCheckedCount, totalBuckets } from '@/modules/history/reconciliation/use-reconciliation-rows';

const { totals } = defineProps<{
  totals: StatusCounts;
}>();

const { t } = useI18n({ useScope: 'global' });

interface Segment {
  key: 'mismatch' | 'blocked' | 'matches' | 'not_checked';
  label: MessageKey;
  count: number;
  barClass: string;
  icon: string;
  iconClass: string;
}

/** Fixed order on purpose: needs action first, then uncheckable, then healthy. */
const segments = computed<Segment[]>(() => [
  {
    barClass: 'bg-rui-error',
    count: totals.mismatch,
    icon: 'lu-circle-x',
    iconClass: 'text-rui-error',
    key: 'mismatch',
    label: STATUS_LABEL.mismatch,
  },
  {
    barClass: 'bg-rui-warning',
    count: totals.blocked,
    icon: 'lu-triangle-alert',
    iconClass: 'text-rui-warning',
    key: 'blocked',
    label: STATUS_LABEL.blocked,
  },
  {
    barClass: 'bg-rui-success',
    count: totals.reconciled,
    icon: 'lu-circle-check',
    iconClass: 'text-rui-success',
    key: 'matches',
    label: STATUS_LABEL.matches,
  },
  {
    barClass: 'bg-rui-grey-300 dark:bg-rui-grey-600',
    count: notCheckedCount(totals),
    icon: 'lu-circle-minus',
    iconClass: 'text-rui-text-secondary',
    key: 'not_checked',
    label: STATUS_LABEL.not_checked,
  },
]);

const total = computed<number>(() => totalBuckets(totals));

function widthOf(segment: Segment): string {
  if (get(total) === 0)
    return '0%';
  return `${(segment.count / get(total)) * 100}%`;
}
</script>

<template>
  <div
    class="flex flex-col gap-2"
    data-testid="reconciliation-status-bar"
  >
    <div
      v-if="total > 0"
      class="flex h-2.5 w-full overflow-hidden rounded-full bg-rui-grey-100 dark:bg-rui-grey-800"
      role="img"
      :aria-label="t('data_issues.reconciliation.bar_label')"
    >
      <div
        v-for="segment in segments"
        v-show="segment.count > 0"
        :key="segment.key"
        :class="segment.barClass"
        :style="{ width: widthOf(segment) }"
        :title="t(segment.label)"
      />
    </div>
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
      <div
        v-for="segment in segments"
        :key="segment.key"
        class="flex items-center gap-1.5"
      >
        <RuiIcon
          :name="segment.icon"
          size="14"
          :class="segment.iconClass"
        />
        <span class="text-rui-text-secondary">{{ t(segment.label) }}</span>
        <span class="font-medium tabular-nums">{{ segment.count }}</span>
      </div>
    </div>
  </div>
</template>
