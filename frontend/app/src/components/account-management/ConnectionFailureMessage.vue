<script setup lang="ts">
import { useInterop } from '@/composables/electron-interop';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/main';

const { t } = useI18n();

const { connect } = useMainStore();
const interop = useInterop();

const defaultBackend = api.defaultBackend;
const retry = () => connect(api.serverUrl);
const toDefault = () => connect();
const terminate = () => interop.closeApp();
</script>

<template>
  <RuiCard
    variant="flat"
    class="max-w-[27.5rem] mx-auto !bg-transparent"
  >
    <template #header>
      {{ t('connection_failure.title') }}
    </template>
    <div class="text-rui-text-secondary">
      {{ t('connection_failure.message') }}
    </div>
    <template #footer>
      <RuiButton
        v-if="!defaultBackend"
        variant="text"
        @click="toDefault()"
      >
        {{ t('connection_failure.default') }}
      </RuiButton>
      <RuiButton
        variant="text"
        @click="terminate()"
      >
        {{ t('common.actions.terminate') }}
      </RuiButton>
      <RuiButton
        class="ml-4"
        color="primary"
        @click="retry()"
      >
        {{ t('connection_failure.retry') }}
      </RuiButton>
    </template>
  </RuiCard>
</template>
