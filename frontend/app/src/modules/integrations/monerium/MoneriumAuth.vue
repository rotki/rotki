<script setup lang="ts">
import type { OAuthResult } from '@shared/ipc';
import { type Notification, NotificationGroup, Priority, Severity } from '@rotki/common';
import { getPublicServiceImagePath } from '@/modules/core/common/file/file';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import ServiceKeyCard, { type FeatureGate, type ServiceKeyAction } from '@/modules/settings/api-keys/ServiceKeyCard.vue';
import { useBackendMessages } from '@/modules/shell/app/use-backend-messages';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { useMoneriumOAuth } from './use-monerium-auth';

const { t } = useI18n({ useScope: 'global' });
const name = 'monerium';

const { allowed, minimumTier, premium } = useFeatureAccess(PremiumFeature.MONERIUM);
const featureGate = computed<FeatureGate>(() => {
  const tier = get(minimumTier);
  const message = !get(premium)
    ? t('external_services.need_premium')
    : t('external_services.need_tier', { tier });

  return { allowed: get(allowed), message };
});

const websiteUrl = import.meta.env.VITE_ROTKI_WEBSITE_URL;

const isAuthorizing = ref<boolean>(false);
const showTokenInput = ref<boolean>(false);
/** The desktop app opened the browser and waits for the approval to come back through its callback. */
const awaitingApproval = ref<boolean>(false);
const manualAccessToken = ref<string>('');
const manualRefreshToken = ref<string>('');

const { isPackaged, openUrl } = useInterop();
const { notify, removeMatching } = useNotifications();
const { registerOAuthCallbackHandler, unregisterOAuthCallbackHandler } = useBackendMessages();
const { authenticated, completeOAuth, disconnect: disconnectOAuth, status } = useMoneriumOAuth();

const connectedEmail = computed<string>(() => get(status)?.userEmail ?? '');

/** How connecting works; the desktop app picks the result up itself, the web asks for the tokens. */
const steps = computed<string[]>(() => [
  t('external_services.monerium.steps.approve'),
  isPackaged ? t('external_services.monerium.steps.return_app') : t('external_services.monerium.steps.return_web'),
]);

/**
 * The dialog's one action follows the flow: connect; then on the web submit the pasted tokens, and in
 * the app reopen the approval page while waiting for it to come back.
 */
const primaryText = computed<string>(() => {
  if (get(showTokenInput))
    return t('external_services.monerium.submit_token');
  if (get(awaitingApproval))
    return t('external_services.monerium.reopen');
  return t('external_services.monerium.connect');
});

const cardAction = computed<ServiceKeyAction>(() => ({
  addText: t('external_services.actions.authenticate'),
  disabled: get(isAuthorizing),
  editText: t('external_services.actions.manage'),
  hidden: get(authenticated),
  primary: get(primaryText),
  statusText: t('external_services.status.connected'),
}));

async function confirm(): Promise<void> {
  if (get(showTokenInput))
    await submitManualToken();
  else
    await connect();
}

/**
 * Every notification raised here is a step of the same connection flow - opening the browser,
 * the outcome of the callback, a disconnect - so they all share one group. The dispatcher then
 * replaces the entry of the previous step instead of leaving a trail of stale ones behind.
 */
function notifyAuthStep(payload: Notification): void {
  notify({
    ...payload,
    group: NotificationGroup.MONERIUM_AUTH,
    priority: Priority.HIGH,
  });
}

/**
 * A successful authorization already reports itself where the user is looking: the card flips to
 * the connected state naming the account. Saying it again in the notification area would leave an
 * entry to dismiss for something already on screen, so success instead clears the flow's own
 * trail, such as the "opening browser" step. One call is enough because a group holds a single
 * entry: the dispatcher replaces it rather than appending. An expired session is an action center
 * row, not part of this group, and leaves once the status reads authenticated.
 */
function clearAuthNotifications(): void {
  removeMatching(({ group }) => group === NotificationGroup.MONERIUM_AUTH);
}

function notifyOAuthError(error: unknown): void {
  logger.error('Monerium OAuth failed:', error);
  notifyAuthStep({
    message: getErrorMessage(error) || t('external_services.monerium.auth_failed'),
    severity: Severity.ERROR,
    title: t('external_services.monerium.error'),
  });
}

async function handleOAuthCallback(oAuthResult: OAuthResult): Promise<void> {
  if (oAuthResult.service !== name)
    return;

  // whatever came back, the wait for the browser is over
  set(awaitingApproval, false);
  try {
    if (!oAuthResult.success) {
      notifyOAuthError(oAuthResult.error);
      return;
    }

    const { accessToken, expiresIn, refreshToken } = oAuthResult;
    if (!accessToken || !refreshToken) {
      notifyOAuthError(new Error(t('external_services.monerium.token_required')));
      return;
    }

    set(isAuthorizing, true);
    await completeOAuth(
      accessToken,
      refreshToken,
      expiresIn ?? 3600,
    );

    clearAuthNotifications();
    set(showTokenInput, false);
    set(manualAccessToken, '');
    set(manualRefreshToken, '');
  }
  catch (error: unknown) {
    notifyOAuthError(error);
  }
  finally {
    set(isAuthorizing, false);
  }
}

async function connect(): Promise<void> {
  if (!websiteUrl) {
    notifyOAuthError(new Error(t('external_services.monerium.website_url_missing')));
    return;
  }

  set(isAuthorizing, true);
  try {
    const mode = isPackaged ? 'app' : 'docker';
    const oauthUrl = `${websiteUrl}/oauth/monerium?mode=${mode}`;

    if (isPackaged) {
      await openUrl(oauthUrl);
      set(awaitingApproval, true);
    }
    else {
      window.open(oauthUrl, '_blank');
      set(showTokenInput, true);
    }

    notifyAuthStep({
      message: t('external_services.monerium.opening_browser'),
      severity: Severity.INFO,
      title: t('external_services.monerium.authorizing'),
    });
  }
  catch (error: unknown) {
    notifyOAuthError(error);
  }
  finally {
    set(isAuthorizing, false);
  }
}

async function disconnect(): Promise<void> {
  set(isAuthorizing, true);
  try {
    await disconnectOAuth();
    notifyAuthStep({
      message: t('external_services.monerium.disconnected'),
      severity: Severity.INFO,
      title: t('external_services.monerium.success'),
    });
  }
  catch (error: unknown) {
    notifyOAuthError(error);
  }
  finally {
    set(isAuthorizing, false);
  }
}

async function submitManualToken(): Promise<void> {
  if (!get(manualAccessToken) || !get(manualRefreshToken)) {
    notifyAuthStep({
      message: t('external_services.monerium.token_required'),
      severity: Severity.ERROR,
      title: t('external_services.monerium.error'),
    });
    return;
  }

  await handleOAuthCallback({
    accessToken: get(manualAccessToken).trim(),
    refreshToken: get(manualRefreshToken).trim(),
    service: name,
    success: true,
  });
}

function cancelTokenInput(): void {
  set(showTokenInput, false);
  set(awaitingApproval, false);
  set(manualAccessToken, '');
  set(manualRefreshToken, '');
}

onMounted(async () => {
  registerOAuthCallbackHandler(handleOAuthCallback);
});

onUnmounted(() => {
  unregisterOAuthCallbackHandler(handleOAuthCallback);
});
</script>

<template>
  <ServiceKeyCard
    :name="name"
    :feature-gate="featureGate"
    :key-set="authenticated"
    :title="t('external_services.monerium.title')"
    :subtitle="t('external_services.monerium.description')"
    :image-src="getPublicServiceImagePath('monerium.png')"
    :action="cardAction"
    @confirm="confirm()"
  >
    <template
      v-if="authenticated || showTokenInput || awaitingApproval"
      #left-buttons
    >
      <RuiButton
        v-if="authenticated"
        :disabled="isAuthorizing"
        color="error"
        variant="text"
        data-testid="monerium-disconnect"
        @click="disconnect()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-unplug"
            size="16"
          />
        </template>
        {{ t('external_services.monerium.disconnect') }}
      </RuiButton>
      <RuiButton
        v-else
        :disabled="isAuthorizing"
        variant="text"
        color="primary"
        data-testid="monerium-start-over"
        @click="cancelTokenInput()"
      >
        {{ t('external_services.monerium.start_over') }}
      </RuiButton>
    </template>

    <div
      v-if="authenticated"
      class="flex items-center gap-3 rounded-rui-control border border-rui-divider px-4 py-3"
      data-testid="monerium-connected"
    >
      <div class="flex size-9 shrink-0 items-center justify-center rounded-full bg-rui-success/10 text-rui-success">
        <RuiIcon
          name="lu-circle-check"
          size="20"
        />
      </div>
      <div class="flex flex-col min-w-0">
        <span class="text-sm font-semibold text-rui-text">{{ t('external_services.status.connected') }}</span>
        <span class="text-sm text-rui-text-secondary truncate">{{ connectedEmail || t('external_services.monerium.unknown_email') }}</span>
      </div>
    </div>

    <div
      v-else-if="awaitingApproval"
      class="flex items-center gap-3 rounded-rui-control border border-rui-divider px-4 py-3"
      data-testid="monerium-waiting"
    >
      <RuiProgress
        variant="indeterminate"
        circular
        size="20"
        thickness="2"
        color="primary"
      />
      <div class="flex flex-col min-w-0">
        <span class="text-sm font-semibold text-rui-text">{{ t('external_services.monerium.waiting.title') }}</span>
        <span class="text-sm text-rui-text-secondary">{{ t('external_services.monerium.waiting.description') }}</span>
      </div>
    </div>

    <div
      v-else-if="showTokenInput"
      class="flex flex-col gap-2"
    >
      <p class="m-0 mb-2 text-sm text-rui-text-secondary">
        {{ t('external_services.monerium.paste_tokens') }}
      </p>
      <RuiTextField
        v-model.trim="manualAccessToken"
        :label="t('external_services.monerium.access_token')"
        color="primary"
        :disabled="isAuthorizing"
      />
      <RuiTextField
        v-model.trim="manualRefreshToken"
        :label="t('external_services.monerium.refresh_token')"
        color="primary"
        :disabled="isAuthorizing"
      />
    </div>

    <ol
      v-else
      class="m-0 p-0 list-none flex flex-col gap-3"
      data-testid="monerium-steps"
    >
      <li
        v-for="(step, index) in steps"
        :key="step"
        class="flex items-start gap-3"
      >
        <span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-rui-primary/10 text-xs font-semibold text-rui-primary">
          {{ index + 1 }}
        </span>
        <span class="pt-0.5 text-sm text-rui-text">{{ step }}</span>
      </li>
    </ol>

    <p
      v-if="!authenticated"
      class="m-0 mt-4 flex items-center gap-2 text-xs text-rui-text-secondary"
    >
      <RuiIcon
        name="lu-lock-keyhole"
        size="14"
      />
      {{ t('external_services.monerium.privacy') }}
    </p>
  </ServiceKeyCard>
</template>
