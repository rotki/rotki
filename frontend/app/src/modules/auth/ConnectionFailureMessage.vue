<script setup lang="ts">
import { LogLevel } from '@shared/log-level';
import { startPromise } from '@shared/utils';
import { api } from '@/modules/core/api/rotki-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useControl } from '@/modules/core/control/use-control';
import { useBackendConnection } from '@/modules/shell/app/use-backend-connection';
import { useBackendManagement } from '@/modules/shell/app/use-backend-management';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

const restarting = ref<boolean>(false);
const restartError = ref<string>();

const { t } = useI18n({ useScope: 'global' });

const { connect } = useBackendConnection();
const { saveOptions } = useBackendManagement();
const { available, probe, restart: controlRestart, supportsOptions } = useControl();
const interop = useInterop();

const defaultBackend = api.defaultBackend;
// A debug retry restarts the backend *with* a log level, so it needs a runtime
// that will carry one. The desktop persists it through the saved backend
// options; docker sends it on the `/_control` restart, which accepts `loglevel`
// and nothing else. Where neither is true the button is hidden rather than shown
// and then refused — until now the web build rendered it and threw on the
// `window.interop` assertion behind it.
const canRestartWithDebug = computed<boolean>(() => supportsOptions || get(available));

async function retry(enableDebug = false): Promise<void> {
  if (enableDebug) {
    set(restarting, true);
    set(restartError, undefined);
    try {
      if (supportsOptions)
        await saveOptions({ loglevel: LogLevel.DEBUG });
      else
        await controlRestart(LogLevel.DEBUG);
    }
    catch (error_: unknown) {
      // Very likely on this screen: the session may have lapsed, or the proxy
      // may not reach core to authorise. Report it and still reconnect — an
      // unhandled rejection here would skip the retry the button is named for.
      set(restartError, getErrorMessage(error_));
    }
    finally {
      set(restarting, false);
    }
  }
  connect(api.serverUrl);
}
const toDefault = (): void => connect();
const terminate = (): Promise<void> => interop.closeApp();

onBeforeMount(() => {
  // This screen is reachable before login, so the probe is the only way to know
  // whether a restart is on offer at all.
  startPromise(probe());
});
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
    <RuiAlert
      v-if="restartError"
      class="mt-4"
      type="error"
    >
      {{ restartError }}
    </RuiAlert>
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
        v-if="canRestartWithDebug"
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
