<script setup lang="ts">
import FullSizeContent from '@/modules/shell/components/FullSizeContent.vue';

const { progress = '' } = defineProps<{
  progress?: string;
}>();

defineSlots<{
  default: () => any;
  message: () => any;
}>();

const progressValue = computed<string | number>(() => {
  const currentProgress = progress;
  if (!currentProgress)
    return 0;

  const number = Number.parseFloat(currentProgress);
  return Number.isNaN(number) ? 0 : number.toFixed(2);
});

const percentage = useToNumber(progressValue);

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <FullSizeContent>
    <div
      class="flex flex-col items-center justify-center mb-10 w-full"
      :class="{ 'max-w-xl': progress, 'md:w-5/6': !progress }"
    >
      <template v-if="progress">
        <div
          class="text-2xl font-semibold tabular-nums text-rui-text mb-4"
          data-testid="progress-screen-percentage"
        >
          {{ t('progress_screen.progress', { progress: progressValue }) }}
        </div>
        <RuiProgress
          thickness="8"
          :value="percentage"
          color="primary"
          class="w-full rounded-full overflow-hidden"
        />
      </template>
      <RuiProgress
        v-else
        circular
        variant="indeterminate"
        color="primary"
        size="70"
      />
    </div>
    <p class="text-center font-light mb-6">
      <slot name="message" />
    </p>
    <RuiDivider class="w-full md:w-1/4" />
    <div class="font-light text-subtitle-2 text-center mt-8">
      <slot />
    </div>
  </FullSizeContent>
</template>
