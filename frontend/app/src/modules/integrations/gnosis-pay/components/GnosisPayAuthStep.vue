<script setup lang="ts">
interface Props {
  stepNumber: number;
  title: string;
  isComplete: boolean;
  isCurrent: boolean;
  isClickable?: boolean;
}

const { isCurrent, isComplete, isClickable, stepNumber } = defineProps<Props>();

const emit = defineEmits<{
  'click-step': [stepNumber: number];
}>();

defineSlots<{
  default: () => any;
}>();

const shouldShowContent = computed<boolean>(() => isCurrent || isComplete);
const isHeaderClickable = computed<boolean>(() => isComplete && isClickable);
/** Done reads as a tick, the current step as the filled one, and a step still ahead stays quiet. */
const stepBadgeClass = computed<string>(() => {
  if (isComplete)
    return 'bg-rui-success/10 text-rui-success';
  if (isCurrent)
    return 'bg-rui-primary text-white';
  return 'border border-rui-divider text-rui-text-secondary';
});

function handleHeaderClick(): void {
  if (get(isHeaderClickable)) {
    emit('click-step', stepNumber);
  }
}
</script>

<template>
  <div class="flex flex-col gap-2 pb-4 last:pb-0">
    <div
      class="flex items-center gap-3"
      :class="isHeaderClickable ? 'cursor-pointer hover:opacity-80' : ''"
      @click="handleHeaderClick()"
    >
      <div
        class="shrink-0 size-7 rounded-full flex items-center justify-center text-xs font-semibold"
        :class="stepBadgeClass"
      >
        <RuiIcon
          v-if="isComplete"
          name="lu-check"
          size="14"
        />
        <span v-else>{{ stepNumber }}</span>
      </div>
      <div
        class="text-sm font-semibold"
        :class="isCurrent || isComplete ? 'text-rui-text' : 'text-rui-text-secondary'"
      >
        {{ title }}
      </div>
    </div>

    <div
      v-if="shouldShowContent"
      class="ml-3.5 flex flex-col gap-3 border-l border-rui-divider pl-6 pb-1"
    >
      <slot />
    </div>
  </div>
</template>
