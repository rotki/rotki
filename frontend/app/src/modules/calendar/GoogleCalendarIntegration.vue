<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { useGoogleCalendarIntegration } from '@/modules/calendar/use-google-calendar-integration';
import { useBackendMessages } from '@/modules/shell/app/use-backend-messages';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

const { t } = useI18n({ useScope: 'global' });

const { isPackaged } = useInterop();
const { registerOAuthCallbackHandler, unregisterOAuthCallbackHandler } = useBackendMessages();

const {
  cancelAuthorization,
  cancelTokenInput,
  checkStatus,
  connect,
  connectedUserEmail,
  disconnect,
  handleOAuthCallback,
  isAuthorizing,
  isConnected,
  isSyncing,
  modelManualRefreshToken,
  modelManualToken,
  showTokenInput,
  submitManualToken,
  sync,
} = useGoogleCalendarIntegration();

onMounted(() => {
  startPromise(checkStatus());
  registerOAuthCallbackHandler(handleOAuthCallback);
});

onUnmounted(() => {
  unregisterOAuthCallbackHandler(handleOAuthCallback);
});
</script>

<template>
  <div class="border-t border-default pt-4">
    <div class="text-subtitle-1 font-medium mb-1 ">
      {{ t('external_services.google_calendar.title') }}
    </div>

    <div
      v-if="!isConnected"
      class="space-y-3"
    >
      <div class="text-body-2 text-rui-text-secondary">
        {{ t('external_services.google_calendar.description') }}
      </div>
      <div class="flex gap-2">
        <RuiButton
          color="primary"
          size="sm"
          data-testid="google-calendar-connect"
          :disabled="isAuthorizing"
          :loading="isAuthorizing"
          @click="connect()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-link"
              size="16"
            />
          </template>
          {{ t('external_services.google_calendar.connect_to_google') }}
        </RuiButton>

        <RuiButton
          v-if="isAuthorizing"
          color="primary"
          size="sm"
          variant="outlined"
          data-testid="google-calendar-cancel-authorization"
          @click="cancelAuthorization()"
        >
          {{ t('common.actions.cancel') }}
        </RuiButton>
      </div>

      <!-- Manual Token Input for Docker Mode -->
      <div
        v-if="showTokenInput && !isPackaged"
        class="space-y-3 border-t pt-3 mt-3"
      >
        <div class="text-body-2 text-rui-text-secondary">
          {{ t('external_services.google_calendar.paste_token_instruction') }}
        </div>
        <RuiTextArea
          v-model="modelManualToken"
          data-testid="google-calendar-access-token"
          :label="t('external_services.google_calendar.access_token')"
          placeholder="ya29.a0AfH6..."
          variant="outlined"
          color="primary"
          rows="4"
          dense
        />
        <RuiTextArea
          v-model="modelManualRefreshToken"
          data-testid="google-calendar-refresh-token"
          :label="t('external_services.google_calendar.refresh_token')"
          placeholder="1//04abc..."
          variant="outlined"
          color="primary"
          rows="4"
          dense
        />
        <div class="flex gap-2">
          <RuiButton
            color="primary"
            size="sm"
            data-testid="google-calendar-submit-token"
            :disabled="isAuthorizing || !modelManualToken.trim() || !modelManualRefreshToken.trim()"
            :loading="isAuthorizing"
            @click="submitManualToken()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-check"
                size="16"
              />
            </template>
            {{ t('external_services.google_calendar.submit_token') }}
          </RuiButton>
          <RuiButton
            variant="outlined"
            size="sm"
            data-testid="google-calendar-cancel-token"
            :disabled="isAuthorizing"
            @click="cancelTokenInput()"
          >
            {{ t('common.actions.cancel') }}
          </RuiButton>
        </div>
      </div>
    </div>

    <div
      v-else
      class="space-y-3"
    >
      <div class="flex items-center gap-2 text-rui-success">
        <RuiIcon
          name="lu-circle-check"
          size="16"
        />
        <span
          class="text-body-2"
          data-testid="google-calendar-status"
        >
          {{ connectedUserEmail
            ? t('external_services.google_calendar.connected_as', { email: connectedUserEmail })
            : t('external_services.google_calendar.connected_status') }}
        </span>
      </div>

      <div class="flex gap-2">
        <RuiButton
          color="primary"
          variant="outlined"
          size="sm"
          data-testid="google-calendar-sync"
          :loading="isSyncing"
          :disabled="isSyncing"
          @click="sync()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-refresh-ccw"
              size="16"
            />
          </template>
          {{ t('external_services.google_calendar.sync_now') }}
        </RuiButton>

        <RuiButton
          color="error"
          variant="outlined"
          size="sm"
          data-testid="google-calendar-disconnect"
          @click="disconnect()"
        >
          {{ t('external_services.google_calendar.disconnect') }}
        </RuiButton>
      </div>
    </div>
  </div>
</template>
