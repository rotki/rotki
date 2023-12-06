<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    header?: string;
    title?: string;
    subtitle?: string;
    message?: string;
    error?: string;
    alternative?: string;
  }>(),
  {
    header: '',
    title: '',
    subtitle: '',
    message: '',
    error: '',
    alternative: ''
  }
);

const { error, message } = toRefs(props);

const { t } = useI18n();

const errorText = computed(() => {
  const errorText = get(error);
  const errorMessage = get(message);
  return !errorText ? errorMessage : `${errorMessage}\n\n${errorText}`;
});
</script>

<template>
  <div class="error-screen">
    <div>
      <VIcon size="120" color="error">mdi-alert-circle</VIcon>
    </div>
    <div v-if="header" class="error-screen__title">
      <div class="text-h1">
        {{ header }}
      </div>
    </div>

    <slot />

    <VCard v-if="!alternative" outlined class="error-screen__message mt-3">
      <VCardTitle>
        {{ title }}
        <VSpacer />
        <CopyButton
          :tooltip="t('error_screen.copy_tooltip')"
          :value="errorText"
        />
      </VCardTitle>
      <VCardSubtitle>
        {{ subtitle }}
      </VCardSubtitle>
      <VCardText class="font-light error-screen__description">
        <pre
          class="font-weight-regular text-caption text-wrap error-screen__description__message"
        >
          {{ message }}
          <VDivider v-if="error" class="mt-4 mb-2"/>
          {{ error }}
        </pre>
        <textarea v-model="errorText" class="error-screen__copy-area" />
      </VCardText>
    </VCard>
    <div v-else class="text-h5 mt-12">{{ alternative }}</div>
    <slot name="bottom" />
  </div>
</template>

<style scoped lang="scss">
.error-screen {
  height: 100%;
  width: 100%;
  z-index: 99999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  &__message {
    max-width: 80%;
  }

  &__title {
    margin-top: 25px;
    margin-bottom: 20px;
  }

  &__copy-area {
    position: absolute;
    top: -999em;
    left: -999em;
  }

  &__description {
    height: 300px;
    overflow: auto;

    &__message {
      max-width: 500px;
      width: 100%;
    }
  }

  @apply bg-white dark:bg-black;
}
</style>
