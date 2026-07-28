<script setup lang="ts">
import type { McpServerStatus, McpServiceState } from '@shared/ipc';
import type { McpToken } from '@/modules/settings/types/mcp';
import { startPromise } from '@shared/utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMcpApi } from '@/modules/settings/api/use-mcp-api';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import CopyTooltip from '@/modules/shell/components/CopyTooltip.vue';
import { useMcpServerState } from './use-mcp-server-state';

const { t } = useI18n({ useScope: 'global' });
const isDocker = import.meta.env.VITE_DOCKER === 'true';

const {
  getMcpServerStatus,
  isPackaged,
  setMcpAutoStart,
  startMcpServer,
  stopMcpServer,
} = useInterop();
const { generateMcpToken } = useMcpApi();

const status = ref<McpServerStatus>();
const error = ref<string>();
const loading = ref<boolean>(isPackaged);
const token = ref<McpToken>();
const mcpServerState = useMcpServerState();

const transitioningStates: ReadonlySet<McpServiceState> = new Set([
  'Restarting',
  'Spawning',
  'Stopping',
  'WaitingReady',
]);

const isRunning = computed<boolean>(() => get(status)?.state === 'Ready');
const dockerEndpoint = computed<string>(() => `${window.location.origin}/mcp`);
const statusLabels = computed<Record<McpServiceState, string>>(() => ({
  Degraded: t('backend_settings.settings.mcp_server.status.failed'),
  Failed: t('backend_settings.settings.mcp_server.status.failed'),
  Idle: t('backend_settings.settings.mcp_server.status.stopped'),
  Ready: t('backend_settings.settings.mcp_server.status.running'),
  Restarting: t('backend_settings.settings.mcp_server.status.starting'),
  Spawning: t('backend_settings.settings.mcp_server.status.starting'),
  Stopped: t('backend_settings.settings.mcp_server.status.stopped'),
  Stopping: t('backend_settings.settings.mcp_server.status.stopping'),
  Unavailable: t('backend_settings.settings.mcp_server.status.unavailable'),
  WaitingReady: t('backend_settings.settings.mcp_server.status.starting'),
}));
const isLifecycleDisabled = computed<boolean>(() => {
  const state = get(status)?.state;
  return state === undefined || state === 'Unavailable' || transitioningStates.has(state);
});

function statusLabel(state: McpServiceState | undefined): string {
  if (!state && get(loading))
    return t('backend_settings.settings.mcp_server.status.loading');
  return get(statusLabels)[state ?? 'Unavailable'];
}

async function loadStatus(): Promise<void> {
  if (!isPackaged)
    return;

  set(loading, true);
  set(error, undefined);
  try {
    set(status, await getMcpServerStatus());
  }
  catch (error_: unknown) {
    set(error, getErrorMessage(error_));
  }
  finally {
    set(loading, false);
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

async function createToken(): Promise<void> {
  set(loading, true);
  set(error, undefined);
  try {
    set(token, await generateMcpToken());
  }
  catch (error_: unknown) {
    set(error, getErrorMessage(error_));
  }
  finally {
    set(loading, false);
  }
}

watch(mcpServerState, (state) => {
  const currentStatus = get(status);
  if (state && currentStatus)
    set(status, { ...currentStatus, state });
});

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

    <div
      v-if="isDocker"
      class="flex flex-col gap-4"
    >
      <RuiAlert type="info">
        {{ t('backend_settings.settings.mcp_server.docker_description') }}
      </RuiAlert>

      <RuiAlert
        v-if="error"
        type="error"
      >
        {{ t('backend_settings.settings.mcp_server.token_error', { message: error }) }}
      </RuiAlert>

      <div class="flex flex-col gap-1">
        <span class="text-sm text-rui-text-secondary">
          {{ t('backend_settings.settings.mcp_server.endpoint') }}
        </span>
        <div class="flex items-center gap-2 rounded border border-default bg-rui-grey-50 dark:bg-rui-grey-900 p-3">
          <code class="flex-1 min-w-0 text-sm break-all font-mono">
            {{ dockerEndpoint }}
          </code>
          <CopyTooltip :value="dockerEndpoint">
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
      </div>

      <RuiButton
        data-testid="mcp-generate-token"
        color="primary"
        :loading="loading"
        @click="createToken()"
      >
        {{ t('backend_settings.settings.mcp_server.generate_token') }}
      </RuiButton>

      <div
        v-if="token"
        class="flex flex-col gap-1"
      >
        <span class="text-sm text-rui-text-secondary">
          {{ t('backend_settings.settings.mcp_server.token') }}
        </span>
        <div class="flex items-center gap-2 rounded border border-default bg-rui-grey-50 dark:bg-rui-grey-900 p-3">
          <code
            data-testid="mcp-token"
            class="flex-1 min-w-0 text-sm break-all font-mono"
          >
            {{ token.accessToken }}
          </code>
          <CopyTooltip :value="token.accessToken">
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
        <span class="text-xs text-rui-text-secondary">
          {{ t('backend_settings.settings.mcp_server.token_expires', {
            timestamp: new Date(token.expiresAt * 1000).toLocaleString(),
          }) }}
        </span>
      </div>
    </div>

    <RuiAlert
      v-else-if="!isPackaged"
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
          :disabled="isLifecycleDisabled"
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
