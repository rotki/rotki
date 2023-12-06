<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    progress?: string;
  }>(),
  { progress: '' }
);

const { progress } = toRefs(props);
const percentage = computed(() => {
  const currentProgress = get(progress);
  try {
    const number = Number.parseFloat(currentProgress);
    return number.toFixed(2);
  } catch {
    return currentProgress;
  }
});

const { t } = useI18n();
</script>

<template>
  <FullSizeContent>
    <div
      class="flex flex-col items-center justify-center mb-10 w-full md:w-5/6"
    >
      <template v-if="progress">
        <div class="text-4xl mb-8">
          {{ t('progress_screen.progress', { progress: percentage }) }}
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
