<script setup lang="ts">
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import ErrorScreen from '@/modules/shell/components/error/ErrorScreen.vue';

const { t } = useI18n({ useScope: 'global' });
const { closeApp } = useInterop();
</script>

<template>
  <ErrorScreen
    class="py-8"
    :header="t('win_unsupported.header')"
    :alternative="t('win_unsupported.message')"
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
