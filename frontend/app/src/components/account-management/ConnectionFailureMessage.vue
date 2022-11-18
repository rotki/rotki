<template>
  <div class="pa-4">
    <div class="text-h6">{{ t('connection_failure.title') }}</div>
    <div class="text-body-1 mt-2 text--secondary">
      {{ t('connection_failure.message') }}
    </div>
    <div class="fill-width d-flex mt-4">
      <v-btn v-if="!defaultBackend" text @click="toDefault">
        {{ t('connection_failure.default') }}
      </v-btn>
      <v-spacer />
      <v-btn depressed @click="terminate">
        {{ t('common.actions.terminate') }}
      </v-btn>
      <v-btn class="ml-4" depressed color="primary" @click="retry">
        {{ t('connection_failure.retry') }}
      </v-btn>
    </div>
  </div>
</template>
<script setup lang="ts">
import { useInterop } from '@/electron-interop';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/main';

const { connect } = useMainStore();
const interop = useInterop();

const defaultBackend = api.defaultBackend;
const retry = () => connect(api.serverUrl);
const toDefault = () => connect();
const terminate = () => interop.closeApp();

const { t } = useI18n();
</script>
