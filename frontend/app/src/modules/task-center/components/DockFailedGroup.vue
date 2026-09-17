<script setup lang="ts">
import type { Activity } from '@/modules/task-center/core/types';
import DockActivityRow from '@/modules/task-center/components/DockActivityRow.vue';

const { activities, now, parent, reason } = defineProps<{
  /** The failed leaves the group stands for, in the order they sorted. */
  activities: Activity[];
  reason: string | undefined;
  /** The row the group sits under, which names what each leaf acts on. */
  parent: Activity;
  now: number;
}>();

const emit = defineEmits<{
  retry: [activity: Activity];
}>();

const { t } = useI18n({ useScope: 'global' });

const retryable = computed<Activity[]>(() => activities.filter(activity => activity.rerunnable));

function retryAll(): void {
  for (const activity of get(retryable))
    emit('retry', activity);
}
</script>

<template>
  <div
    class="flex flex-col rounded bg-rui-error/5"
    data-testid="dock-failed-group"
  >
    <div class="flex items-start gap-2.5 py-1.5 px-1">
      <RuiIcon
        name="lu-circle-x"
        size="16"
        class="shrink-0 mt-0.5 text-rui-error"
      />
      <div class="flex flex-col flex-1 min-w-0 gap-0.5">
        <div class="text-sm leading-5 font-medium text-rui-error">
          {{ t('task_dock.panel.outcome.failed', { count: activities.length }) }}
        </div>
        <div
          v-if="reason"
          class="text-xs leading-4 text-rui-error break-words"
          data-testid="dock-failed-group-reason"
        >
          {{ reason }}
        </div>
      </div>
      <RuiButton
        v-if="retryable.length > 0"
        class="shrink-0"
        variant="text"
        color="primary"
        size="sm"
        data-testid="dock-failed-group-retry"
        @click="retryAll()"
      >
        {{ t('task_dock.panel.retry_failed', { count: retryable.length }, retryable.length) }}
      </RuiButton>
    </div>
    <div class="flex flex-col pl-6">
      <DockActivityRow
        v-for="activity in activities"
        :key="activity.id"
        :activity="activity"
        :parent="parent"
        :now="now"
        :percentage="activity.percentage"
        hide-reason
        @retry="emit('retry', $event)"
      />
    </div>
  </div>
</template>
