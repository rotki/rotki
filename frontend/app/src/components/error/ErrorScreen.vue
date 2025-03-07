<script setup lang="ts">
import CopyButton from '@/components/helper/CopyButton.vue';

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
    alternative: '',
    error: '',
    header: '',
    message: '',
    subtitle: '',
    title: '',
  },
);

defineSlots<{
  default: () => any;
  bottom: () => any;
}>();

const { error, message } = toRefs(props);

const { t } = useI18n();

const errorText = computed(() => {
  const errorText = get(error);
  const errorMessage = get(message);
  return !errorText ? errorMessage : `${errorMessage}\n\n${errorText}`;
});
</script>

<template>
  <div class="error-screen py-6">
    <div>
      <RuiIcon
        size="120"
        color="error"
        name="lu-circle-alert"
      />
    </div>
    <div
      v-if="header"
      class="error-screen__title"
    >
      <div class="text-h4">
        {{ header }}
      </div>
    </div>

    <slot />

    <RuiCard
      v-if="!alternative"
      class="error-screen__message flex-1 my-6 overflow-hidden"
      content-class="h-full"
    >
      <template #header>
        {{ title }}

        <CopyButton
          :tooltip="t('error_screen.copy_tooltip')"
          :value="errorText"
        />
      </template>
      <template #subheader>
        {{ subtitle }}
      </template>
      <div class="font-light text-rui-text-secondary error-screen__description">
        <pre class="text-caption text-wrap error-screen__description__message">
          {{ message }}
          <RuiDivider
            v-if="error"
            class="mt-4 mb-2"
          />
          {{ error }}
        </pre>
        <textarea
          v-model="errorText"
          class="error-screen__copy-area"
        />
      </div>
    </RuiCard>
    <div
      v-else
      class="text-h5 mt-12"
    >
      {{ alternative }}
    </div>
    <slot name="bottom" />
  </div>
</template>

<style scoped lang="scss">
.error-screen {
  @apply bg-white dark:bg-black;

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
}
</style>
