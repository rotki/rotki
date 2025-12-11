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

const { t } = useI18n({ useScope: 'global' });

const errorText = computed(() => {
  const errorText = get(error);
  const errorMessage = get(message);
  return !errorText ? errorMessage : `${errorMessage}\n\n${errorText}`;
});
</script>

<template>
  <div class="py-6 bg-white dark:bg-black h-full w-full z-[99999] flex flex-col items-center justify-center">
    <div>
      <RuiIcon
        size="120"
        color="error"
        name="lu-circle-alert"
      />
    </div>
    <div
      v-if="header"
      class="mt-6 mb-5"
    >
      <div class="text-h4">
        {{ header }}
      </div>
    </div>

    <slot />

    <RuiCard
      v-if="!alternative"
      class="flex-1 my-6 overflow-hidden max-w-[80%]"
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
      <div class="font-light text-rui-text-secondary">
        <pre class="text-caption text-wrap">
          {{ message }}
          <RuiDivider
            v-if="error"
            class="mt-4 mb-2"
          />
          {{ error }}
        </pre>
        <textarea
          v-model="errorText"
          class="absolute -top-[999em] -left-[999em]"
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
