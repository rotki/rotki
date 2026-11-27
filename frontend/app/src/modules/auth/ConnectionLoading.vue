<script setup lang="ts">
import { RuiProgress } from '@rotki/ui-library';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

const { connected, loggingIn = false } = defineProps<{
  connected: boolean;
  loggingIn?: boolean;
}>();
const { t } = useI18n({ useScope: 'global' });

const message = computed<string>(() => {
  if (loggingIn)
    return t('connection_loading.logging_in');
  return t('connection_loading.message');
});
</script>

<template>
  <div
    v-if="!connected"
    class="grow w-full max-w-110 mx-auto flex flex-col gap-4 justify-center items-center py-12"
  >
    <RuiProgress
      color="primary"
      variant="indeterminate"
      circular
      size="48"
    />
    <p
      class="mb-0 text-rui-text-secondary text-center"
      data-testid="connection-loading-content"
    >
      {{ message }}
    </p>
  </div>
</template>
