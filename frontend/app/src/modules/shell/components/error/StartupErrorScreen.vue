<script setup lang="ts">
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import ErrorScreen from '@/modules/shell/components/error/ErrorScreen.vue';

defineProps<{
  message: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const { closeApp } = useInterop();
</script>

<template>
  <ErrorScreen
    class="fixed top-0 left-0"
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
