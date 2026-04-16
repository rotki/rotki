<script setup lang="ts">
import CopyButton from '@/modules/shell/components/CopyButton.vue';

const {
  alternative = '',
  error = '',
  header = '',
  message = '',
  subtitle = '',
  title = '',
} = defineProps<{
  header?: string;
  title?: string;
  subtitle?: string;
  message?: string;
  error?: string;
  alternative?: string;
}>();

defineSlots<{
  default: () => any;
  bottom: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const errorText = computed(() => !error ? message : `${message}\n\n${error}`);
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
      <div class="font-light text-rui-text-secondary text-caption">
        <pre v-text="message" />
        <template v-if="error">
          <RuiDivider
            class="mt-4 mb-2"
          />
          <pre v-text="error" />
        </template>
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
