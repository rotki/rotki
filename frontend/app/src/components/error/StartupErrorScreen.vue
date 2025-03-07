<script setup lang="ts">
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import { useInterop } from '@/composables/electron-interop';

defineProps<{
  message: string;
}>();

const { t } = useI18n();
const { closeApp } = useInterop();
</script>

<template>
  <ErrorScreen
    :class="$style.overlay"
    :header="t('error_screen.start_failure')"
    :title="t('error_screen.backend_error')"
    :subtitle="t('error_screen.message')"
    :message="message"
  >
    <RuiButton
      color="primary"
      @click="closeApp()"
    >
      {{ t('common.actions.terminate') }}
    </RuiButton>
  </ErrorScreen>
</template>

<style module lang="scss">
.overlay {
  @apply fixed top-0 left-0;
}
</style>
