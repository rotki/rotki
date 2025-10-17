<script setup lang="ts">
interface Props {
  stepNumber: number;
  title: string;
  isComplete: boolean;
  isCurrent: boolean;
  isClickable?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isClickable: false,
});

const emit = defineEmits<{
  'click-step': [stepNumber: number];
}>();

const shouldShowContent = computed<boolean>(() => props.isCurrent || props.isComplete);
const isHeaderClickable = computed<boolean>(() => props.isComplete && props.isClickable);
const stepBadgeClass = computed<string>(() => props.isComplete ? 'bg-rui-success' : 'bg-rui-primary');

function handleHeaderClick(): void {
  if (get(isHeaderClickable)) {
    emit('click-step', props.stepNumber);
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
