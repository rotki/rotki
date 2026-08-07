<script setup lang="ts">
import type { ActivitySteps } from '@/modules/task-center/core/types';

const model = defineModel<boolean>({ required: true });

const { count, percentage, steps } = defineProps<{
  /** Jobs, not activities: what the user started, not what it fanned out into. */
  count: number;
  steps: ActivitySteps;
  /** 0-100, or `-1` when nothing in flight can be quantified. */
  percentage: number;
}>();

const { t } = useI18n({ useScope: 'global' });

// Producers declare their subtrees up front, so a refresh knows its own denominator from the first
// tick. The header used to spin indeterminately beside that number and throw it away.
const isDeterminate = computed<boolean>(() => percentage >= 0 && steps.total > 0);
</script>

<template>
  <div class="flex justify-between items-center">
    <div class="flex items-center gap-4">
      <RuiProgress
        v-if="isDeterminate"
        color="primary"
        variant="determinate"
        circular
        :value="percentage"
        size="24"
        thickness="2"
        show-label
      />
      <RuiProgress
        v-else
        color="primary"
        variant="indeterminate"
        circular
        size="20"
        thickness="2"
      />
      <div class="flex flex-col">
        <div class="font-medium">
          {{ t('collapsed_pending_tasks.title', { count }, count) }}
        </div>
        <div
          v-if="isDeterminate"
          class="text-xs text-rui-text-secondary tabular-nums"
        >
          {{ t('collapsed_pending_tasks.steps', { current: steps.current, total: steps.total }) }}
        </div>
      </div>
    </div>

    <RuiButton
      class="-m-1"
      variant="text"
      icon
      size="sm"
      :aria-label="model ? t('pending_task.collapse') : t('pending_task.expand')"
      @click="model = !model"
    >
      <RuiIcon
        v-if="model"
        name="lu-chevron-up"
      />
      <RuiIcon
        v-else
        name="lu-chevron-down"
      />
    </RuiButton>
  </div>
</template>
