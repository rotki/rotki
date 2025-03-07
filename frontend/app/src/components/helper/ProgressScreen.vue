<script setup lang="ts">
import FullSizeContent from '@/components/common/FullSizeContent.vue';

const props = withDefaults(
  defineProps<{
    progress?: string;
  }>(),
  { progress: '' },
);

defineSlots<{
  default: () => any;
  message: () => any;
}>();

const progress = computed(() => {
  const currentProgress = props.progress;
  if (!currentProgress)
    return 0;

  const number = Number.parseFloat(currentProgress);
  return Number.isNaN(number) ? 0 : number.toFixed(2);
});

const percentage = useToNumber(progress);

const { t } = useI18n();
</script>

<template>
  <FullSizeContent>
    <div class="flex flex-col items-center justify-center mb-10 w-full md:w-5/6">
      <template v-if="progress">
        <div class="text-4xl mb-8">
          {{ t('progress_screen.progress', { progress }) }}
        </div>
        <RuiProgress
          thickness="16"
          :value="percentage"
          color="primary"
          class="w-full rounded overflow-hidden"
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
