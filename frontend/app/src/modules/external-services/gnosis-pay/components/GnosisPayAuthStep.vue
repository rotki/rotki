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

const shouldShowContent = computed<boolean>(() => isCurrent || isComplete);
const isHeaderClickable = computed<boolean>(() => isComplete && isClickable);
const stepBadgeClass = computed<string>(() => isComplete ? 'bg-rui-success' : 'bg-rui-primary');

function handleHeaderClick(): void {
  if (get(isHeaderClickable)) {
    emit('click-step', stepNumber);
  }
}
</script>

<template>
  <div class="mb-5">
    <!-- Step header -->
    <div
      class="flex items-center gap-3 mb-2"
      :class="isHeaderClickable ? 'cursor-pointer hover:opacity-80' : ''"
      @click="handleHeaderClick()"
    >
      <div
        class="shrink-0 size-8 rounded-full flex items-center justify-center font-bold text-white text-sm"
        :class="stepBadgeClass"
      >
        <RuiIcon
          v-if="isComplete"
          name="lu-check"
          size="16"
        />
        <span v-else>{{ stepNumber }}</span>
      </div>
      <div class="font-medium text-base">
        {{ title }}
      </div>
    </div>

    <!-- Step content -->
    <div
      v-if="shouldShowContent"
      class="ml-4 pl-7 space-y-4 border-l border-default"
    >
      <slot />
    </div>
  </div>
</template>
