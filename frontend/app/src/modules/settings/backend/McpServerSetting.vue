<script setup lang="ts">
import type { McpServerStatus, McpServiceState } from '@shared/ipc';
import { startPromise } from '@shared/utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import CopyTooltip from '@/modules/shell/components/CopyTooltip.vue';

const { t } = useI18n({ useScope: 'global' });

const {
  getMcpServerStatus,
  isPackaged,
  setMcpAutoStart,
  startMcpServer,
  stopMcpServer,
} = useInterop();

const status = ref<McpServerStatus>();
const error = ref<string>();
const loading = ref<boolean>(false);

const failedStates: ReadonlySet<McpServiceState | undefined> = new Set(['Degraded', 'Failed']);
const startingStates: ReadonlySet<McpServiceState | undefined> = new Set([
  'Restarting',
  'Spawning',
  'WaitingReady',
]);

const isRunning = computed<boolean>(() => get(status)?.state === 'Ready');
const isTransitioning = computed<boolean>(() => {
  const state = get(status)?.state;
  return state === 'Restarting'
    || state === 'Spawning'
    || state === 'Stopping'
    || state === 'WaitingReady';
});

function statusLabel(state: McpServiceState | undefined): string {
  if (failedStates.has(state))
    return t('backend_settings.settings.mcp_server.status.failed');
  if (startingStates.has(state))
    return t('backend_settings.settings.mcp_server.status.starting');

  switch (state) {
    case 'Ready':
      return t('backend_settings.settings.mcp_server.status.running');
    case 'Stopping':
      return t('backend_settings.settings.mcp_server.status.stopping');
    case 'Idle':
    case 'Stopped':
      return t('backend_settings.settings.mcp_server.status.stopped');
    case 'Unavailable':
    default:
      return t('backend_settings.settings.mcp_server.status.unavailable');
  }
}

async function loadStatus(): Promise<void> {
  if (!isPackaged)
    return;

  set(error, undefined);
  try {
    set(status, await getMcpServerStatus());
  }
  catch (error_: unknown) {
    set(error, getErrorMessage(error_));
  }
}

async function updateAutoStart(enabled: boolean): Promise<void> {
  set(loading, true);
  set(error, undefined);
  try {
    set(status, await setMcpAutoStart(enabled));
  }
  catch (error_: unknown) {
    set(error, getErrorMessage(error_));
  }
  finally {
    set(loading, false);
  }
}

async function toggleServer(): Promise<void> {
  set(loading, true);
  set(error, undefined);
  try {
    set(status, await (get(isRunning) ? stopMcpServer() : startMcpServer()));
  }
  catch (error_: unknown) {
    const message = getErrorMessage(error_);
    await loadStatus();
    set(error, message);
  }
  finally {
    set(loading, false);
  }
}

onBeforeMount(() => {
  startPromise(loadStatus());
});
</script>

<template>
  <SettingsItem action-key="mcpServer">
    <template #title>
      {{ t('backend_settings.settings.mcp_server.label') }}
    </template>
    <template #subtitle>
      {{ t('backend_settings.settings.mcp_server.hint') }}
    </template>

    <RuiAlert
      v-if="!isPackaged"
      type="info"
    >
      {{ t('backend_settings.settings.mcp_server.desktop_only') }}
    </RuiAlert>

    <div
      v-else
      class="flex flex-col gap-4"
    >
      <RuiAlert
        v-if="error"
        type="error"
      >
        {{ t('backend_settings.settings.mcp_server.error', { message: error }) }}
      </RuiAlert>

      <div class="flex flex-wrap items-center gap-3">
        <span class="text-sm text-rui-text-secondary">
          {{ t('backend_settings.settings.mcp_server.status.label') }}
        </span>
        <RuiChip
          size="sm"
          :color="isRunning ? 'success' : 'secondary'"
        >
          {{ statusLabel(status?.state) }}
        </RuiChip>
      </div>

      <div
        v-if="status"
        class="flex items-center gap-2 rounded border border-default bg-rui-grey-50 dark:bg-rui-grey-900 p-3"
      >
        <code class="flex-1 min-w-0 text-sm break-all font-mono">
          {{ status.endpoint }}
        </code>
        <CopyTooltip :value="status.endpoint">
          <RuiButton
            icon
            variant="text"
            color="primary"
            size="sm"
          >
            <RuiIcon
              name="lu-copy"
              size="16"
            />
          </RuiButton>
          <template #label>
            {{ t('common.actions.copy_to_clipboard') }}
          </template>
        </CopyTooltip>
      </div>

      <div class="flex flex-wrap items-center gap-4">
        <RuiSwitch
          data-testid="mcp-auto-start"
          :model-value="status?.autoStart ?? false"
          :disabled="loading"
          hide-details
          color="primary"
          :label="t('backend_settings.settings.mcp_server.auto_start')"
          @update:model-value="updateAutoStart($event)"
        />
        <RuiButton
          data-testid="mcp-lifecycle"
          color="primary"
          :disabled="!status || isTransitioning"
          :loading="loading"
          @click="toggleServer()"
        >
          {{ isRunning
            ? t('backend_settings.settings.mcp_server.actions.stop')
            : t('backend_settings.settings.mcp_server.actions.start') }}
        </RuiButton>
      </div>
    </div>
  </SettingsItem>
</template>
