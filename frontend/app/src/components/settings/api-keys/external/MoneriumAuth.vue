<script setup lang="ts">
import type { OAuthResult } from '@shared/ipc';
import { Severity } from '@rotki/common';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import { useMoneriumOAuthApi } from '@/composables/api/settings/monerium-oauth';
import { useInterop } from '@/composables/electron-interop';
import { useBackendMessagesStore } from '@/store/backend-messages';
import { useNotificationsStore } from '@/store/notifications';
import { useMoneriumOAuthStore } from '@/store/settings/monerium-oauth';
import { logger } from '@/utils/logging';

const { t } = useI18n({ useScope: 'global' });

const websiteUrl = import.meta.env.VITE_ROTKI_WEBSITE_URL as string | undefined;

const isAuthorizing = ref(false);
const showTokenInput = ref(false);
const manualAccessToken = ref('');
const manualRefreshToken = ref('');

const moneriumApi = useMoneriumOAuthApi();
const { isPackaged, openUrl } = useInterop();
const { notify } = useNotificationsStore();
const { registerOAuthCallbackHandler, unregisterOAuthCallbackHandler } = useBackendMessagesStore();
const moneriumStore = useMoneriumOAuthStore();
const { authenticated, status } = storeToRefs(moneriumStore);

const moneriumConnected = computed(() => get(authenticated));
const connectedEmail = computed(() => get(status)?.userEmail ?? '');

async function loadStatus() {
  await moneriumStore.refreshStatus();
}

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
    const result = await moneriumApi.completeOAuth(
      accessToken,
      refreshToken,
      expiresIn ?? 3600,
    );

    moneriumStore.setStatus({
      authenticated: true,
      defaultProfileId: result.defaultProfileId,
      profiles: result.profiles,
      userEmail: result.userEmail,
    });

    await moneriumStore.refreshStatus();

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
      set(isAuthorizing, false);
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
    set(isAuthorizing, false);
  }
}

async function disconnect(): Promise<void> {
  set(isAuthorizing, true);
  try {
    await moneriumApi.disconnect();
    moneriumStore.setStatus({ authenticated: false });
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

async function submitManualToken() {
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

function cancelTokenInput() {
  set(showTokenInput, false);
  set(manualAccessToken, '');
  set(manualRefreshToken, '');
}

const primaryActionLabel = computed(() => moneriumConnected.value
  ? t('external_services.monerium.disconnect')
  : t('external_services.monerium.connect'));

async function primaryActionHandler() {
  if (moneriumConnected.value)
    await disconnect();
  else
    await connect();
}

onMounted(() => {
  loadStatus();
  registerOAuthCallbackHandler(handleOAuthCallback);
});

onUnmounted(() => {
  unregisterOAuthCallbackHandler(handleOAuthCallback);
});
</script>

<template>
  <ServiceKeyCard
    need-premium
    :key-set="moneriumConnected"
    :title="t('external_services.monerium.title')"
    :subtitle="t('external_services.monerium.description')"
    image-src="./assets/images/services/monerium.png"
    :primary-action="primaryActionLabel"
    :action-disabled="isAuthorizing"
    @confirm="primaryActionHandler()"
  >
    <RuiAlert
      type="info"
      class="mb-4"
    >
      {{ t('external_services.monerium.warning') }}
    </RuiAlert>

    <div class="flex flex-col gap-4">
      <div v-if="moneriumConnected">
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
