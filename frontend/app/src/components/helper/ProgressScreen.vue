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
    <div :class="$style.content">
      <VCol cols="12">
        <VRow
          v-if="progress"
          align="center"
          justify="center"
          class="font-light"
          :class="$style.percentage"
        >
          {{ t('progress_screen.progress', { progress: percentage }) }}
        </VRow>
        <VRow align="center" justify="center" :class="$style.loader">
          <VCol cols="10">
            <VProgressLinear
              v-if="progress"
              class="text-center"
              rounded
              height="16"
              color="primary"
              :value="progress"
            />
            <div v-else :class="$style.indeterminate">
              <VProgressCircular
                rounded
                indeterminate
                :size="70"
                color="primary"
              />
            </div>
          </VCol>
        </VRow>
        <VRow align="center" justify="center">
          <p class="text-center font-light" :class="$style.description">
            <slot name="message" />
          </p>
        </VRow>
        <VRow align="center" justify="center">
          <VCol cols="4">
            <VDivider />
          </VCol>
        </VRow>
        <VRow align="center" justify="center" :class="$style.warning">
          <div class="font-light text-subtitle-2 text-center">
            <slot />
          </div>
        </VRow>
      </VCol>
    </div>
  </FullSizeContent>
</template>

<style module lang="scss">
.indeterminate {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-bottom: 80px;
}

.content {
  display: flex;
  align-items: center;
  flex-direction: row;
  height: 100%;
  width: 100%;
}

.loader {
  min-height: 80px;
}

.percentage {
  font-size: 46px;
}

.description {
  font-size: 16px;
}

.warning {
  margin-top: 30px;
}
</style>
