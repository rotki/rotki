<script setup lang="ts">
import type { OAuthResult } from '@shared/ipc';
import { Severity } from '@rotki/common';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import { useInterop } from '@/composables/electron-interop';
import { useBackendMessagesStore } from '@/store/backend-messages';
import { useNotificationsStore } from '@/store/notifications';
import { getPublicServiceImagePath } from '@/utils/file';
import { logger } from '@/utils/logging';
import { useMoneriumOAuth } from './use-monerium-auth';

const { t } = useI18n({ useScope: 'global' });

const websiteUrl = import.meta.env.VITE_ROTKI_WEBSITE_URL as string | undefined;

const isAuthorizing = ref<boolean>(false);
const showTokenInput = ref<boolean>(false);
const manualAccessToken = ref<string>('');
const manualRefreshToken = ref<string>('');

const { isPackaged, openUrl } = useInterop();
const { notify } = useNotificationsStore();
const { registerOAuthCallbackHandler, unregisterOAuthCallbackHandler } = useBackendMessagesStore();
const { authenticated, completeOAuth, disconnect: disconnectOAuth, status } = useMoneriumOAuth();

const connectedEmail = computed<string>(() => get(status)?.userEmail ?? '');

function notifyOAuthError(error: any): void {
  logger.error('Monerium OAuth failed:', error);
  notify({
    display: true,
    message: error.message || t('external_services.monerium.auth_failed'),
    severity: Severity.ERROR,
    title: t('external_services.monerium.error'),
  });
}

async function handleOAuthCallback(oAuthResult: OAuthResult): Promise<void> {
  if (oAuthResult.service !== 'monerium')
    return;

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
    const result = await completeOAuth(
      accessToken,
      refreshToken,
      expiresIn ?? 3600,
    );

    notify({
      display: true,
      message: result.message,
      severity: Severity.INFO,
      title: t('external_services.monerium.success'),
    });
    set(showTokenInput, false);
    set(manualAccessToken, '');
    set(manualRefreshToken, '');
  }
  catch (error: any) {
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
    }
    else {
      window.open(oauthUrl, '_blank');
      set(showTokenInput, true);
    }

    notify({
      display: true,
      message: t('external_services.monerium.opening_browser'),
      severity: Severity.INFO,
      title: t('external_services.monerium.authorizing'),
    });
  }
  catch (error: any) {
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
    notify({
      display: true,
      message: t('external_services.monerium.disconnected'),
      severity: Severity.INFO,
      title: t('external_services.monerium.success'),
    });
  }
  catch (error: any) {
    notifyOAuthError(error);
  }
  finally {
    set(isAuthorizing, false);
  }
}

async function submitManualToken(): Promise<void> {
  if (!get(manualAccessToken) || !get(manualRefreshToken)) {
    notify({
      display: true,
      message: t('external_services.monerium.token_required'),
      severity: Severity.ERROR,
      title: t('external_services.monerium.error'),
    });
    return;
  }

  await handleOAuthCallback({
    accessToken: get(manualAccessToken).trim(),
    refreshToken: get(manualRefreshToken).trim(),
    service: 'monerium',
    success: true,
  });
}

function cancelTokenInput(): void {
  set(showTokenInput, false);
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
    need-premium
    :key-set="authenticated"
    :title="t('external_services.monerium.title')"
    :subtitle="t('external_services.monerium.description')"
    :image-src="getPublicServiceImagePath('monerium.png')"
    :primary-action="t('external_services.monerium.connect')"
    :action-disabled="isAuthorizing"
    :hide-action="authenticated"
    :add-button-text="t('external_services.actions.authenticate')"
    :edit-button-text="t('external_services.actions.reauthenticate')"
    @confirm="connect()"
  >
    <template
      v-if="authenticated"
      #left-buttons
    >
      <RuiButton
        :disabled="isAuthorizing"
        color="error"
        variant="text"
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
    </template>
    <RuiAlert
      type="info"
      class="mb-4"
    >
      {{ t('external_services.monerium.warning') }}
    </RuiAlert>

    <div class="flex flex-col gap-4">
      <div v-if="authenticated">
        <RuiAlert type="success">
          {{ t('external_services.monerium.connected_as', { email: connectedEmail || t('external_services.monerium.unknown_email') }) }}
        </RuiAlert>
      </div>

      <div v-else>
        <p class="text-sm text-rui-text-secondary">
          {{ t('external_services.monerium.instructions') }}
        </p>
      </div>

      <div
        v-if="showTokenInput"
        class="flex flex-col gap-3"
      >
        <RuiTextField
          v-model.trim="manualAccessToken"
          :label="t('external_services.monerium.access_token')"
          variant="outlined"
          color="primary"
        />
        <RuiTextField
          v-model.trim="manualRefreshToken"
          :label="t('external_services.monerium.refresh_token')"
          variant="outlined"
          color="primary"
        />
        <div class="flex gap-2">
          <RuiButton
            color="primary"
            :loading="isAuthorizing"
            @click="submitManualToken()"
          >
            {{ t('external_services.monerium.submit_token') }}
          </RuiButton>
          <RuiButton
            variant="text"
            color="secondary"
            :disabled="isAuthorizing"
            @click="cancelTokenInput()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
        </div>
      </div>
    </div>
  </ServiceKeyCard>
</template>
