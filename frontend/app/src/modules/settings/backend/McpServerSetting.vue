<script setup lang="ts">
import { StarlingServiceStatus } from '@shared/ipc';
import { StarlingService } from '@shared/starling/starling-protocol';
import { startPromise } from '@shared/utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useControl } from '@/modules/core/control/use-control';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { useMcpApi } from '@/modules/settings/api/use-mcp-api';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { McpPrivacyMode, type McpPrivacyMode as McpPrivacyModeValue, type McpToken } from '@/modules/settings/types/mcp';
import { useSettingModel } from '@/modules/settings/use-setting-model';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import CopyTooltip from '@/modules/shell/components/CopyTooltip.vue';
import GetPremiumPlaceholder from '@/modules/shell/components/GetPremiumPlaceholder.vue';
import McpPrivacyPreview from './McpPrivacyPreview.vue';
import { useMcpServerState } from './use-mcp-server-state';

const { t } = useI18n({ useScope: 'global' });
const isDocker = import.meta.env.VITE_DOCKER === 'true';

const { getMcpServerStatus, isPackaged, setMcpAutoStart } = useInterop();
const { available, probe, serviceState, setServiceRunning, supportsOptions } = useControl();
const { generateMcpToken } = useMcpApi();
const { allowed: mcpAllowed, minimumTier: mcpMinimumTier, premium } = useFeatureAccess(PremiumFeature.MCP);

const state = ref<StarlingServiceStatus>();
const autoStart = ref<boolean>(false);
const serverError = ref<string>();
const loading = ref<boolean>(true);
const token = ref<McpToken>();
const tokenError = ref<string>();
const tokenVisible = ref<boolean>(false);
const mcpServerState = useMcpServerState();
const {
  error: privacyModeError,
  model: privacyMode,
  pending: privacyModePending,
  success: privacyModeSuccess,
} = useSettingModel('mcpPrivacyMode');

// `useSettingModel` keeps `success` true until the next write, which beside a heading would read as
// a permanent label rather than a confirmation. Show it only for as long as it is news.
const savedVisible = ref<boolean>(false);
const { start: hideSaved } = useTimeoutFn(() => {
  set(savedVisible, false);
}, 4000, { immediate: false });

interface PrivacyModeOption {
  readonly classes: string;
  readonly description: string;
  /** The backend default, and the one the copy points at. */
  readonly recommended: boolean;
  readonly title: string;
  readonly value: McpPrivacyModeValue;
}

// Raw is the only mode that sends anything unmasked, so selecting it carries the warning tone
// rather than the ordinary selected tint.
function optionClasses(value: McpPrivacyModeValue, selected: McpPrivacyModeValue): string {
  if (value !== selected)
    return 'border-default';

  return value === McpPrivacyMode.RAW
    ? 'border-rui-warning/50 bg-rui-warning/10'
    : 'border-rui-primary bg-rui-primary/5';
}

const privacyModes = computed<PrivacyModeOption[]>(() => {
  const selected = get(privacyMode);
  return [
    {
      classes: optionClasses(McpPrivacyMode.STRICT, selected),
      description: t('backend_settings.settings.mcp_server.privacy_mode.strict.description'),
      recommended: false,
      title: t('backend_settings.settings.mcp_server.privacy_mode.strict.title'),
      value: McpPrivacyMode.STRICT,
    },
    {
      classes: optionClasses(McpPrivacyMode.BALANCED, selected),
      description: t('backend_settings.settings.mcp_server.privacy_mode.balanced.description'),
      recommended: true,
      title: t('backend_settings.settings.mcp_server.privacy_mode.balanced.title'),
      value: McpPrivacyMode.BALANCED,
    },
    {
      classes: optionClasses(McpPrivacyMode.RAW, selected),
      description: t('backend_settings.settings.mcp_server.privacy_mode.raw.description'),
      recommended: false,
      title: t('backend_settings.settings.mcp_server.privacy_mode.raw.title'),
      value: McpPrivacyMode.RAW,
    },
  ];
});

const transitioningStates: ReadonlySet<StarlingServiceStatus> = new Set([
  StarlingServiceStatus.RESTARTING,
  StarlingServiceStatus.SPAWNING,
  StarlingServiceStatus.STOPPING,
  StarlingServiceStatus.WAITING_READY,
]);

// Docker reaches MCP through the proxy on the page's own origin; the desktop
// binds it on loopback, and only Electron knows the address it actually used.
const endpoint = ref<string>(isDocker ? `${window.location.origin}/mcp` : '');

const isRunning = computed<boolean>(() => get(state) === StarlingServiceStatus.READY);
const tokenDisplay = computed<string>(() => (
  get(tokenVisible) ? get(token)?.accessToken ?? '' : '••••••••••••••••'
));
const tokenVisibilityLabel = computed<string>(() => (
  get(tokenVisible)
    ? t('backend_settings.settings.mcp_server.hide_token')
    : t('backend_settings.settings.mcp_server.reveal_token')
));
const statusLabels = computed<Record<StarlingServiceStatus, string>>(() => ({
  [StarlingServiceStatus.DEGRADED]: t('backend_settings.settings.mcp_server.status.failed'),
  [StarlingServiceStatus.FAILED]: t('backend_settings.settings.mcp_server.status.failed'),
  [StarlingServiceStatus.IDLE]: t('backend_settings.settings.mcp_server.status.stopped'),
  [StarlingServiceStatus.READY]: t('backend_settings.settings.mcp_server.status.running'),
  [StarlingServiceStatus.RESTARTING]: t('backend_settings.settings.mcp_server.status.starting'),
  [StarlingServiceStatus.SPAWNING]: t('backend_settings.settings.mcp_server.status.starting'),
  [StarlingServiceStatus.STOPPED]: t('backend_settings.settings.mcp_server.status.stopped'),
  [StarlingServiceStatus.STOPPING]: t('backend_settings.settings.mcp_server.status.stopping'),
  [StarlingServiceStatus.UNAVAILABLE]: t('backend_settings.settings.mcp_server.status.unavailable'),
  [StarlingServiceStatus.WAITING_READY]: t('backend_settings.settings.mcp_server.status.starting'),
}));
const isLifecycleDisabled = computed<boolean>(() => {
  const current = get(state);
  return current === undefined
    || current === StarlingServiceStatus.UNAVAILABLE
    || transitioningStates.has(current);
});
// Nothing to drive the server with. In the plain web build that is simply the
// truth (no supervisor is reachable); in docker it means the deployment has no
// session cookie configured, so starling never mounted `/_control`.
const unavailableMessage = computed<string>(() => (
  isPackaged || isDocker
    ? t('backend_settings.settings.mcp_server.control_unavailable')
    : t('backend_settings.settings.mcp_server.desktop_only')
));
// a premium subscriber whose tier is too low needs a different answer than someone
// with no subscription at all: one has to upgrade, the other has to subscribe.
const gateTitle = computed<string>(() => (
  get(premium)
    ? t('backend_settings.settings.mcp_server.premium_plan_title')
    : t('backend_settings.settings.mcp_server.premium_title')
));

function statusLabel(current: StarlingServiceStatus | undefined): string {
  if (!current && get(loading))
    return t('backend_settings.settings.mcp_server.status.loading');
  return get(statusLabels)[current ?? StarlingServiceStatus.UNAVAILABLE];
}

async function loadStatus(): Promise<void> {
  set(loading, true);
  set(serverError, undefined);
  try {
    if (!await probe())
      return;

    set(state, await serviceState(StarlingService.MCP));
    // Auto-start and the loopback endpoint are Electron app settings, readable
    // only where a restart may carry options at all.
    if (supportsOptions) {
      const status = await getMcpServerStatus();
      set(autoStart, status.autoStart);
      set(endpoint, status.endpoint);
    }
  }
  catch (error_: unknown) {
    set(serverError, getErrorMessage(error_));
  }
  finally {
    set(loading, false);
  }
}

async function updateAutoStart(enabled: boolean): Promise<void> {
  set(loading, true);
  set(serverError, undefined);
  try {
    const status = await setMcpAutoStart(enabled);
    set(autoStart, status.autoStart);
    set(state, status.state);
  }
  catch (error_: unknown) {
    set(serverError, getErrorMessage(error_));
  }
  finally {
    set(loading, false);
  }
}

async function toggleServer(): Promise<void> {
  set(loading, true);
  set(serverError, undefined);
  try {
    set(state, await setServiceRunning(StarlingService.MCP, !get(isRunning)));
  }
  catch (error_: unknown) {
    const message = getErrorMessage(error_);
    await loadStatus();
    set(serverError, message);
  }
  finally {
    set(loading, false);
  }
}

async function createToken(): Promise<void> {
  set(loading, true);
  set(tokenError, undefined);
  try {
    set(token, await generateMcpToken());
    set(tokenVisible, false);
  }
  catch (error_: unknown) {
    set(tokenError, getErrorMessage(error_));
  }
  finally {
    set(loading, false);
  }
}

function toggleTokenVisibility(): void {
  set(tokenVisible, !get(tokenVisible));
}

watch(privacyModeSuccess, (saved) => {
  set(savedVisible, saved);
  if (saved)
    hideSaved();
});

watch(mcpServerState, (pushed) => {
  if (pushed)
    set(state, pushed);
});

// Runs regardless of the premium gate: the probe is what decides whether there is a
// supervisor at all, and that answer is shown ahead of any upsell. Gating it on
// `mcpAllowed` would also leave a user who unlocks mid-session without a status.
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

    <!-- the environment check comes first: where there is no server to reach, the answer is
         "not here", not "buy premium". Offering premium there would be selling nothing. -->
    <RuiAlert
      v-if="!available && !loading"
      type="info"
    >
      {{ unavailableMessage }}
    </RuiAlert>

    <div
      v-else-if="!loading && !mcpAllowed"
      class="max-w-2xl rounded-lg border border-default bg-rui-grey-50 dark:bg-rui-grey-900 px-4 py-5"
      data-testid="mcp-premium-gate"
    >
      <GetPremiumPlaceholder
        :title="gateTitle"
        :description="t('backend_settings.settings.mcp_server.premium_description')"
        :minimum-tier="mcpMinimumTier"
      />
    </div>

    <div
      v-else
      class="flex flex-col gap-4"
    >
      <RuiAlert
        v-if="serverError"
        type="error"
      >
        {{ t('backend_settings.settings.mcp_server.error', { message: serverError }) }}
      </RuiAlert>

      <div class="flex max-w-4xl flex-col gap-3 rounded-lg border border-default bg-rui-grey-50 p-4 dark:bg-rui-grey-900 sm:flex-row sm:items-center">
        <RuiChip
          data-testid="mcp-status"
          size="sm"
          :color="isRunning ? 'success' : 'secondary'"
        >
          {{ statusLabel(state) }}
        </RuiChip>
        <code
          v-if="endpoint"
          class="min-w-0 flex-1 break-all font-mono text-sm text-rui-text-secondary"
        >
          {{ endpoint }}
        </code>
        <CopyTooltip
          v-if="endpoint"
          :value="endpoint"
        >
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
        <RuiButton
          data-testid="mcp-lifecycle"
          :color="isRunning ? 'error' : 'primary'"
          :disabled="isLifecycleDisabled"
          :loading="loading"
          @click="toggleServer()"
        >
          {{ isRunning
            ? t('backend_settings.settings.mcp_server.actions.stop')
            : t('backend_settings.settings.mcp_server.actions.start') }}
        </RuiButton>
      </div>

      <section class="flex max-w-4xl flex-col gap-4">
        <div>
          <div class="flex flex-wrap items-baseline justify-between gap-x-4">
            <h6 class="text-h6 font-semibold">
              {{ t('backend_settings.settings.mcp_server.privacy_mode.label') }}
            </h6>
            <!-- Beside the heading rather than under the last option: the group's own detail slot
                 renders below Raw, where a confirmation reads as if it belonged to Raw. -->
            <span
              v-if="savedVisible"
              class="text-sm text-rui-success"
            >
              {{ t('backend_settings.settings.mcp_server.privacy_mode.success') }}
            </span>
          </div>
          <p class="text-sm text-rui-text-secondary">
            {{ t('backend_settings.settings.mcp_server.privacy_mode.hint') }}
          </p>
        </div>

        <RuiAlert
          v-if="privacyModeError"
          type="error"
        >
          {{ t('backend_settings.settings.mcp_server.privacy_mode.error', { message: privacyModeError }) }}
        </RuiAlert>

        <RuiRadioGroup
          v-model="privacyMode"
          data-testid="mcp-privacy-mode"
          color="primary"
          hide-details
          :disabled="privacyModePending"
        >
          <RuiRadio
            v-for="option in privacyModes"
            :key="option.value"
            :value="option.value"
            class="mb-2 w-full rounded border pl-4 transition-colors last:mb-0"
            :class="option.classes"
          >
            <div class="py-2 pr-3">
              <div class="flex items-center gap-2 font-medium">
                {{ option.title }}
                <RuiChip
                  v-if="option.recommended"
                  size="sm"
                  color="success"
                >
                  {{ t('backend_settings.settings.mcp_server.privacy_mode.default') }}
                </RuiChip>
              </div>
              <div class="mt-0.5 max-w-prose text-sm text-rui-text-secondary">
                {{ option.description }}
              </div>
            </div>
          </RuiRadio>
        </RuiRadioGroup>

        <RuiAlert
          v-if="privacyMode === McpPrivacyMode.RAW"
          type="warning"
        >
          <strong>
            {{ t('backend_settings.settings.mcp_server.privacy_mode.raw_warning.title') }}
          </strong>
          {{ t('backend_settings.settings.mcp_server.privacy_mode.raw_warning.description') }}
        </RuiAlert>

        <McpPrivacyPreview :mode="privacyMode" />
      </section>

      <div class="flex max-w-4xl flex-wrap items-center gap-4 border-t border-default pt-4">
        <RuiSwitch
          v-if="supportsOptions"
          data-testid="mcp-auto-start"
          :model-value="autoStart"
          :disabled="loading"
          hide-details
          color="primary"
          :label="t('backend_settings.settings.mcp_server.auto_start')"
          @update:model-value="updateAutoStart($event)"
        />
      </div>

      <template v-if="isDocker">
        <RuiAlert
          v-if="tokenError"
          type="error"
        >
          {{ t('backend_settings.settings.mcp_server.token_error', { message: tokenError }) }}
        </RuiAlert>

        <RuiButton
          data-testid="mcp-generate-token"
          type="button"
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
              {{ tokenDisplay }}
            </code>
            <RuiButton
              data-testid="mcp-toggle-token"
              icon
              variant="text"
              color="primary"
              size="sm"
              :aria-label="tokenVisibilityLabel"
              @click="toggleTokenVisibility()"
            >
              <RuiIcon
                :name="tokenVisible ? 'lu-eye-off' : 'lu-eye'"
                size="16"
              />
            </RuiButton>
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
          <RuiAlert type="warning">
            {{ t('backend_settings.settings.mcp_server.token_expiry_hint') }}
          </RuiAlert>
        </div>
      </template>
    </div>
  </SettingsItem>
</template>
