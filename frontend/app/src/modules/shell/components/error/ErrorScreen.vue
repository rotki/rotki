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
  <div class="py-10 px-4 bg-white dark:bg-black h-full w-full z-[99999] flex flex-col items-center justify-center">
    <RuiIcon
      size="96"
      color="error"
      name="lu-circle-alert"
    />
    <h1
      v-if="header"
      class="text-h4 font-bold text-center mt-6"
    >
      {{ header }}
    </h1>

    <slot />

    <RuiCard
      v-if="!alternative"
      class="w-full max-w-4xl mt-8"
    >
      <template #header>
        <div class="flex items-center gap-2">
          <span>{{ title }}</span>
          <CopyButton
            :tooltip="t('error_screen.copy_tooltip')"
            :value="errorText"
          />
        </div>
      </template>
      <template #subheader>
        {{ subtitle }}
      </template>
      <div class="max-h-[50vh] overflow-y-auto rounded-md bg-rui-grey-100 dark:bg-rui-grey-900 p-4">
        <pre
          class="font-mono text-caption leading-relaxed text-rui-text-secondary whitespace-pre-wrap break-words"
          v-text="message"
        />
        <template v-if="error">
          <RuiDivider class="my-3" />
          <pre
            class="font-mono text-caption leading-relaxed text-rui-text-secondary whitespace-pre-wrap break-words"
            v-text="error"
          />
        </template>
        <textarea
          v-model="errorText"
          class="absolute -top-[999em] -left-[999em]"
        />
      </div>
    </RuiCard>
    <div
      v-else
      class="text-h5 text-center max-w-2xl mt-8"
    >
      {{ alternative }}
    </div>

    <div
      v-if="$slots.bottom"
      class="mt-8"
    >
      <slot name="bottom" />
    </div>
  </div>
</template>
