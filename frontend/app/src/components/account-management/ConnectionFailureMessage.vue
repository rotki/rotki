<script setup lang="ts">
import { LogLevel } from '@shared/log-level';
import { useBackendManagement } from '@/composables/backend';
import { useInterop } from '@/composables/electron-interop';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/main';

const restarting = ref(false);

const { t } = useI18n({ useScope: 'global' });

const { connect } = useMainStore();
const { restartBackend, saveOptions } = useBackendManagement();
const interop = useInterop();

const defaultBackend = api.defaultBackend;

async function retry(enableDebug = false) {
  if (enableDebug) {
    set(restarting, true);
    await saveOptions({ loglevel: LogLevel.DEBUG });
    await restartBackend();
    set(restarting, false);
  }
  connect(api.serverUrl);
}
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
        variant="text"
        :loading="restarting"
        @click="retry(true)"
      >
        {{ t('connection_failure.retry_with_debug') }}
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
