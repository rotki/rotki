<script setup lang="ts">
import dayjs from 'dayjs';
import { type Activity, resolveText } from '@/modules/task-center/core/types';

const { activity } = defineProps<{ activity: Activity }>();
const emit = defineEmits<{
  cancel: [activity: Activity];
}>();

const { t } = useI18n({ useScope: 'global' });

// `-1` is the orchestrator's "indeterminate": no producer reported steps for this activity.
const hasDeterminateProgress = computed<boolean>(() => activity.percentage >= 0);

const time = computed<string>(() => (activity.startedAt ? dayjs(activity.startedAt).format('LLL') : ''));

// Resolved here rather than at submit time, so a language change updates work already in flight.
const subtitle = computed<string | undefined>(() => resolveText(t, activity.subtitle));
</script>

<template>
  <div class="flex items-center justify-between flex-nowrap gap-4">
    <div class="flex flex-col flex-1 break-words">
      <div class="overflow-hidden text-ellipsis text-sm font-medium mb-1 leading-4">
        {{ activity.title }}
      </div>
      <div
        v-if="subtitle"
        class="text-xs text-rui-text-secondary mb-2"
      >
        {{ subtitle }}
      </div>
      <div
        v-if="time"
        class="text-caption text-xs"
      >
        {{ time }}
      </div>
    </div>
    <RuiProgress
      v-if="hasDeterminateProgress"
      color="primary"
      circular
      variant="determinate"
      :value="activity.percentage"
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
      v-if="activity.cancellable"
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
          @click="emit('cancel', activity)"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </template>
      {{ t('collapsed_pending_tasks.cancel_task') }}
    </RuiTooltip>
  </div>
</template>
