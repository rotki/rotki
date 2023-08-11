<script setup lang="ts">
import { api } from '@/services/rotkehlchen-api';

const { t } = useI18n();

const { connect } = useMainStore();
const interop = useInterop();

const defaultBackend = api.defaultBackend;
const retry = () => connect(api.serverUrl);
const toDefault = () => connect();
const terminate = () => interop.closeApp();
</script>

<template>
  <div class="pa-4">
    <div class="text-h6">{{ t('connection_failure.title') }}</div>
    <div class="text-body-1 mt-2 text--secondary">
      {{ t('connection_failure.message') }}
    </div>
    <div class="w-full d-flex mt-4">
      <VBtn v-if="!defaultBackend" text @click="toDefault()">
        {{ t('connection_failure.default') }}
      </VBtn>
      <VSpacer />
      <VBtn depressed @click="terminate()">
        {{ t('common.actions.terminate') }}
      </VBtn>
      <VBtn class="ml-4" depressed color="primary" @click="retry()">
        {{ t('connection_failure.retry') }}
      </VBtn>
    </div>
  </div>
</template>
