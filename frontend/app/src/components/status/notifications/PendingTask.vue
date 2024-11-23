<script setup lang="ts">
import dayjs from 'dayjs';
import { TaskType } from '@/types/task-type';
import { useReportsStore } from '@/store/reports';
import type { Task, TaskMeta } from '@/types/task';

const props = defineProps<{ task: Task<TaskMeta> }>();
const emit = defineEmits<{ (e: 'cancel', task: Task<TaskMeta>): void }>();

const { task } = toRefs(props);
const isHistory = computed(() => task.value.type === TaskType.TRADE_HISTORY);

const { progress: taskProgress } = storeToRefs(useReportsStore());
const { t } = useI18n();

const time = computed(() => dayjs(task.value.time).format('LLL'));
const progress = useToNumber(taskProgress);
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
      color="primary"
      circular
      :variant="isHistory ? 'determinate' : 'indeterminate'"
      :value="progress"
      size="24"
      :show-label="isHistory"
      thickness="2"
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
