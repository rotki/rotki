<script setup lang="ts">
import { RuiIcon, RuiProgress } from '@rotki/ui-library';
import { StageStepStatus } from '@/modules/auth/stage/stage-step';

const { progress, status } = defineProps<{
  status: StageStepStatus;
  /** How far the current step is, in percent; left out, the spinner is indeterminate. */
  progress?: number;
}>();
</script>

<template>
  <span
    class="size-4 shrink-0 flex items-center justify-center"
    :data-status="status"
  >
    <RuiIcon
      v-if="status === StageStepStatus.DONE"
      name="lu-check"
      size="16"
      class="text-rui-success"
    />
    <RuiIcon
      v-else-if="status === StageStepStatus.FAILED"
      name="lu-circle-x"
      size="16"
      class="text-rui-error"
    />
    <RuiProgress
      v-else-if="status === StageStepStatus.CURRENT"
      circular
      color="primary"
      size="16"
      thickness="2"
      :variant="progress === undefined ? 'indeterminate' : 'determinate'"
      :value="progress ?? 0"
    />
    <span
      v-else
      class="size-3 rounded-full border-2 border-rui-grey-400 dark:border-rui-grey-600"
    />
  </span>
</template>
