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
/**
 * Whether this runtime can carry a log level through a restart.
 *
 * @remarks
 * The desktop persists one through its saved backend options, and docker sends it on the
 * `/_control` restart. Where neither holds, the button is hidden rather than offered and refused.
 */
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
