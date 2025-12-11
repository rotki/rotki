<script setup lang="ts">
import ErrorScreen from '@/components/error/ErrorScreen.vue';
import { useInterop } from '@/composables/electron-interop';

const { t } = useI18n({ useScope: 'global' });
const { closeApp } = useInterop();
</script>

<template>
  <ErrorScreen
    class="py-8"
    :header="t('macos_unsupported.header')"
    :alternative="t('macos_unsupported.message')"
  >
    <RuiButton
      depressed
      color="primary"
      @click="closeApp()"
    >
      {{ t('common.actions.terminate') }}
    </RuiButton>
  </ErrorScreen>
</template>
