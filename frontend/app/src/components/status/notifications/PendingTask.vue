<script setup lang="ts">
import dayjs from 'dayjs';
import { type Task, type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

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
  <div class="flex items-center justify-between flex-nowrap break-all gap-4">
    <div>
      <div class="break-normal overflow-hidden text-ellipsis">
        {{ task.meta.title }}
      </div>
      <div
        v-if="task.meta.description"
        class="text-sm text-rui-text-secondary mb-2"
      >
        {{ task.meta.description }}
      </div>
      <div class="text-caption text-sm">
        {{ time }}
      </div>
    </div>
    <span class="grow" />
    <RuiProgress
      color="primary"
      circular
      :variant="isHistory ? 'determinate' : 'indeterminate'"
      :value="progress"
      size="24"
      :show-label="isHistory"
      thickness="2"
    />
    <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
      <template #activator>
        <RuiButton
          variant="text"
          color="primary"
          class="shrink-0"
          size="sm"
          icon
          @click="emit('cancel', task)"
        >
          <RuiIcon name="close-line" />
        </RuiButton>
      </template>
      {{ t('collapsed_pending_tasks.cancel_task') }}
    </RuiTooltip>
  </div>
</template>
