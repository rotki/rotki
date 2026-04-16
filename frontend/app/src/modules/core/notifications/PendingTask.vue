<script setup lang="ts">
import type { Task, TaskMeta } from '@/modules/core/tasks/types';
import { bigNumberify } from '@rotki/common';
import dayjs from 'dayjs';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { calculatePercentage } from '@/modules/core/common/data/calculation';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useReportsStore } from '@/modules/reports/use-reports-store';

const { task } = defineProps<{ task: Task<TaskMeta> }>();
const emit = defineEmits<{
  cancel: [task: Task<TaskMeta>];
}>();

const { progress: taskProgress } = storeToRefs(useReportsStore());
const { historicalDailyPriceStatus } = storeToRefs(useHistoricCachePriceStore());
const { t } = useI18n({ useScope: 'global' });

const hasDeterminateProgress = computed<boolean>(() => {
  const { type } = task;
  return type === TaskType.TRADE_HISTORY || type === TaskType.FETCH_DAILY_HISTORIC_PRICE;
});

const time = computed<string>(() => dayjs(task.time).format('LLL'));

const progress = computed<number | undefined>(() => {
  const { type } = task;
  if (type === TaskType.TRADE_HISTORY) {
    return parseInt(get(taskProgress));
  }
  else if (type === TaskType.FETCH_DAILY_HISTORIC_PRICE) {
    if (!isDefined(historicalDailyPriceStatus)) {
      return 0;
    }
    const { processed, total } = get(historicalDailyPriceStatus);
    return parseInt(calculatePercentage(bigNumberify(processed), bigNumberify(total)));
  }
  return undefined;
});
</script>

<template>
  <div class="flex items-center justify-between flex-nowrap gap-4">
    <div class="flex flex-col flex-1 break-words">
      <div class="overflow-hidden text-ellipsis text-sm font-medium mb-1 leading-4">
        {{ task.meta.title }}
      </div>
      <div
        v-if="task.meta.description"
        class="text-xs text-rui-text-secondary mb-2"
      >
        {{ task.meta.description }}
      </div>
      <div class="text-caption text-xs">
        {{ time }}
      </div>
    </div>
    <RuiProgress
      v-if="hasDeterminateProgress"
      color="primary"
      circular
      variant="determinate"
      :value="progress"
      size="24"
      show-label
      thickness="2"
    />
    <RuiIcon
      v-else
      name="lu-loader"
      size="20"
      class="text-rui-text-secondary shrink-0"
    />
    <RuiTooltip
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
          @click="emit('cancel', task)"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </template>
      {{ t('collapsed_pending_tasks.cancel_task') }}
    </RuiTooltip>
  </div>
</template>
