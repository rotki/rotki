<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useGoogleCalendarApi } from '@/composables/api/settings/google-calendar';
import { useInterop } from '@/composables/electron-interop';
import { useBackendMessagesStore } from '@/store/backend-messages';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { logger } from '@/utils/logging';
import { Severity } from '@rotki/common';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { onMounted, onUnmounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n({ useScope: 'global' });

const websiteUrl = import.meta.env.VITE_ROTKI_WEBSITE_URL;

const showMenu = ref(false);
const autoDelete = ref(true);
const autoCreateReminders = ref(true);

// Google Calendar integration
const googleCalendarApi = useGoogleCalendarApi();
const { notify } = useNotificationsStore();
const { isPackaged, openUrl } = useInterop();
const { registerOAuthCallbackHandler, unregisterOAuthCallbackHandler } = useBackendMessagesStore();
const isConnected = ref(false);
const isSyncing = ref(false);
const isAuthorizing = ref(false);
const connectedUserEmail = ref<string>('');
const manualToken = ref<string>('');
const showTokenInput = ref(false);

const { autoCreateCalendarReminders, autoDeleteCalendarEntries } = storeToRefs(useGeneralSettingsStore());

function setAutoDelete() {
  set(autoDelete, get(autoDeleteCalendarEntries));
}

function setAutoCreate() {
  set(autoCreateReminders, get(autoCreateCalendarReminders));
}

// Google Calendar functions
async function checkGoogleCalendarStatus() {
  try {
    const response = await googleCalendarApi.getStatus();
    set(isConnected, response.authenticated);

    // Update the connected user email
    if (response.authenticated && response.userEmail) {
      set(connectedUserEmail, response.userEmail);
    }
    else {
      set(connectedUserEmail, '');
    }
  }
  catch (error: any) {
    logger.error('Failed to check Google Calendar status:', error);
  }
}

async function connectToGoogle() {
  set(isAuthorizing, true);
  try {
    // Determine mode based on environment
    const mode = isPackaged ? 'app' : 'docker';
    const oauthUrl = `${websiteUrl}/oauth/google?mode=${mode}`;

    if (isPackaged) {
      await openUrl(oauthUrl);
    }
    else {
      // Docker mode - open OAuth page in new tab for manual token copy
      window.open(oauthUrl, '_blank');
      set(isAuthorizing, false); // Reset loading state immediately
      set(showTokenInput, true); // Show manual token input
    }

    notify({
      display: true,
      message: t('external_services.google_calendar.opening_browser'),
      severity: Severity.INFO,
      title: t('external_services.google_calendar.authorizing'),
    });
  }
  catch (error: any) {
    notify({
      display: true,
      message: error.message || t('external_services.google_calendar.auth_failed'),
      severity: Severity.ERROR,
      title: t('external_services.google_calendar.error'),
    });
    set(isAuthorizing, false);
  }
}

async function handleOAuthCallback(accessToken: string) {
  try {
    const result = await googleCalendarApi.completeOAuth(accessToken);

    // Debug logging to see what we get back
    logger.info('OAuth complete result:', JSON.stringify(result, null, 2));

    if (result.success) {
      set(isConnected, true);

      // Store the connected user email
      const userEmail = result.userEmail || '';
      set(connectedUserEmail, userEmail);

      // Refresh the connection status to make sure it's up to date
      await checkGoogleCalendarStatus();
    }
    else {
      logger.error('OAuth failed:', result);
      notify({
        display: true,
        message: result.message || t('external_services.google_calendar.auth_failed'),
        severity: Severity.ERROR,
        title: t('external_services.google_calendar.error'),
      });
    }
  }
  catch (error: any) {
    logger.error('OAuth callback error:', error);
    notify({
      display: true,
      message: error.message || t('external_services.google_calendar.auth_failed'),
      severity: Severity.ERROR,
      title: t('external_services.google_calendar.error'),
    });
  }
  finally {
    logger.error('Setting isAuthorizing to false');
    set(isAuthorizing, false);
  }
}

async function syncCalendar() {
  set(isSyncing, true);
  try {
    const result = await googleCalendarApi.syncCalendar();

    // Show appropriate message based on results
    let message: string;
    const severity = Severity.INFO;

    if (result.eventsProcessed === 0) {
      message = t('external_services.google_calendar.no_events_to_sync');
    }
    else {
      message = t('external_services.google_calendar.sync_complete', {
        created: result.eventsCreated || 0,
        total: result.eventsProcessed || 0,
        updated: result.eventsUpdated || 0,
      });
    }

    notify({
      display: true,
      message,
      severity,
      title: t('external_services.google_calendar.success'),
    });
  }
  catch (error: any) {
    notify({
      display: true,
      message: error.message || t('external_services.google_calendar.sync_failed'),
      severity: Severity.ERROR,
      title: t('external_services.google_calendar.error'),
    });
  }
  finally {
    set(isSyncing, false);
  }
}

async function submitManualToken() {
  if (!get(manualToken).trim()) {
    notify({
      display: true,
      message: t('external_services.google_calendar.token_required'),
      severity: Severity.ERROR,
      title: t('external_services.google_calendar.error'),
    });
    return;
  }

  set(isAuthorizing, true);
  try {
    await handleOAuthCallback(get(manualToken).trim());
    set(manualToken, '');
    set(showTokenInput, false);
  }
  catch {
    // Error handling is done in handleOAuthCallback
  }
  finally {
    set(isAuthorizing, false);
  }
}

function cancelTokenInput() {
  set(manualToken, '');
  set(showTokenInput, false);
}

async function disconnect() {
  try {
    await googleCalendarApi.disconnect();
    set(isConnected, false);
    set(connectedUserEmail, '');
  }
  catch (error: any) {
    notify({
      display: true,
      message: error.message || t('external_services.google_calendar.disconnect_failed'),
      severity: Severity.ERROR,
      title: t('external_services.google_calendar.error'),
    });
  }
}

onMounted(() => {
  setAutoDelete();
  setAutoCreate();
  checkGoogleCalendarStatus();

  registerOAuthCallbackHandler(handleOAuthCallback);
});

onUnmounted(() => {
  unregisterOAuthCallbackHandler(handleOAuthCallback);
});
</script>

<template>
  <RuiMenu
    v-model="showMenu"
    menu-class="w-full max-w-96 !bg-transparent"
    :popper="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            v-bind="attrs"
          >
            <RuiIcon name="lu-settings" />
          </RuiButton>
        </template>
        <span>{{ t('calendar.dialog.settings.tooltip') }}</span>
      </RuiTooltip>
    </template>
    <RuiCard variant="flat">
      <template #header>
        {{ t('calendar.dialog.settings.title') }}
      </template>
      <div class="flex flex-col gap-1">
        <SettingsOption
          #default="{ updateImmediate, loading, error, success }"
          setting="autoCreateCalendarReminders"
          @finished="setAutoCreate()"
        >
          <RuiSwitch
            v-model="autoCreateReminders"
            :disabled="loading"
            :label="t('calendar.dialog.settings.auto_create_reminders')"
            color="primary"
            :error-messages="error"
            :success-messages="success"
            @update:model-value="updateImmediate($event)"
          />
        </SettingsOption>
        <SettingsOption
          #default="{ updateImmediate, loading, error, success }"
          setting="autoDeleteCalendarEntries"
          @finished="setAutoDelete()"
        >
          <RuiSwitch
            v-model="autoDelete"
            :disabled="loading"
            :label="t('calendar.dialog.settings.auto_delete')"
            color="primary"
            :error-messages="error"
            :success-messages="success"
            @update:model-value="updateImmediate($event)"
          />
        </SettingsOption>

        <!-- Google Calendar Integration -->
        <div class="border-t pt-4 mt-4">
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
            <RuiButton
              color="primary"
              size="sm"
              :disabled="isAuthorizing"
              :loading="isAuthorizing"
              @click="connectToGoogle()"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-link"
                  size="16"
                />
              </template>
              {{ t('external_services.google_calendar.connect_to_google') }}
            </RuiButton>

            <!-- Manual Token Input for Docker Mode -->
            <div
              v-if="showTokenInput && !isPackaged"
              class="space-y-3 border-t pt-3 mt-3"
            >
              <div class="text-body-2 text-rui-text-secondary">
                {{ t('external_services.google_calendar.paste_token_instruction') }}
              </div>
              <RuiTextArea
                v-model="manualToken"
                :label="t('external_services.google_calendar.access_token')"
                placeholder="ya29.a0AfH6..."
                variant="outlined"
                color="primary"
                rows="4"
                dense
              />
              <div class="flex gap-2">
                <RuiButton
                  color="primary"
                  size="sm"
                  :disabled="isAuthorizing || !manualToken.trim()"
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
              <span class="text-body-2">
                {{ connectedUserEmail ? `Connected as ${connectedUserEmail}` : t('external_services.google_calendar.connected_status') }}
              </span>
            </div>

            <div class="flex gap-2">
              <RuiButton
                color="primary"
                variant="outlined"
                size="sm"
                :loading="isSyncing"
                :disabled="isSyncing"
                @click="syncCalendar()"
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
                @click="disconnect()"
              >
                {{ t('external_services.google_calendar.disconnect') }}
              </RuiButton>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <RuiButton
          class="ml-auto"
          variant="text"
          color="primary"
          @click="showMenu = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiMenu>
</template>
