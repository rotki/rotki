<script setup lang="ts">
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import { useGoogleCalendarApi } from '@/composables/api/settings/google-calendar';
import { useInterop } from '@/composables/electron-interop';
import { useNotificationsStore } from '@/store/notifications';
import { Severity } from '@rotki/common';
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n({ useScope: 'global' });

const googleCalendarApi = useGoogleCalendarApi();
const { notify } = useNotificationsStore();
const { openUrl } = useInterop();

const clientId = ref('');
const clientSecret = ref('');
const showAuthDialog = ref(false);
const showSetupDialog = ref(false);
const showApiErrorDialog = ref(false);
const apiErrorDetails = ref({ projectId: '', setupUrl: '' });
const verificationUrl = ref('');
const userCode = ref('');
const isConnected = ref(false);
const isSyncing = ref(false);
const isLoading = ref(false);
const isPolling = ref(false);
let pollInterval: NodeJS.Timeout | null = null;

const hasCredentials = computed(() => clientId.value && clientSecret.value);


// Check connection status on mount
onMounted(async () => {
  isLoading.value = true;
  try {
    const response = await googleCalendarApi.getStatus();
    isConnected.value = response.authenticated;
  }
  catch (error: any) {
    console.error('Failed to check Google Calendar status:', error);
  }
  finally {
    isLoading.value = false;
  }
});

// Cleanup polling on unmount
onUnmounted(() => {
  stopPolling();
});

async function startAuth() {
  if (!hasCredentials.value) {
    notify({
      display: true,
      message: t('external_services.google_calendar.credentials_required'),
      severity: Severity.ERROR,
      title: t('external_services.google_calendar.error'),
    });
    return;
  }

  try {
    const deviceInfo = await googleCalendarApi.startAuth(clientId.value, clientSecret.value);

    verificationUrl.value = deviceInfo.verificationUrl;
    userCode.value = deviceInfo.userCode;
    showAuthDialog.value = true;

    // Open verification URL in external browser immediately (before any timeout)
    // This prevents popup blockers from blocking the window.open call
    try {
      if (verificationUrl.value && typeof verificationUrl.value === 'string' && verificationUrl.value.startsWith('https://')) {
        await openUrl(verificationUrl.value);
        console.log('Browser opened successfully');
      } else {
        console.error('Invalid URL - not opening:', verificationUrl.value);
      }
    }
    catch (error) {
      console.error('Failed to open browser:', error);
      // If opening URL fails, user can still manually copy the URL
    }

    // Start polling for completion
    startPolling();
  }
  catch (error: any) {
    notify({
      display: true,
      message: error.message || t('external_services.google_calendar.auth_failed'),
      severity: Severity.ERROR,
      title: t('external_services.google_calendar.error'),
    });
  }
}

function startPolling() {
  if (isPolling.value) {
    console.log('startPolling: Already polling, ignoring request');
    return;
  }

  console.log('startPolling: Starting authentication polling...');
  isPolling.value = true;
  
  pollInterval = setInterval(async () => {
    try {
      console.log('startPolling: Polling for authorization status...');
      const result = await googleCalendarApi.pollAuth();
      console.log('startPolling: Poll result:', result);

      if (result.success) {
        console.log('startPolling: Authentication successful!');
        // Authentication completed successfully
        stopPolling();
        isConnected.value = true;
        showAuthDialog.value = false;

        notify({
          display: true,
          message: t('external_services.google_calendar.connected'),
          severity: Severity.INFO,
          title: t('external_services.google_calendar.success'),
        });
      }
      else if (result.pending) {
        console.log('startPolling: Authentication still pending, continuing to poll...');
      }
      else {
        console.log('startPolling: Unexpected result state:', result);
      }
      // If result.pending is true, continue polling
    }
    catch (error: any) {
      console.error('startPolling: Error during polling:', error);
      stopPolling();
      showAuthDialog.value = false;

      notify({
        display: true,
        message: error.message || t('external_services.google_calendar.auth_failed'),
        severity: Severity.ERROR,
        title: t('external_services.google_calendar.error'),
      });
    }
  }, 5000); // Poll every 5 seconds
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
  isPolling.value = false;
}

async function syncCalendar() {
  isSyncing.value = true;
  try {
    const result = await googleCalendarApi.syncCalendar();
    console.log('Sync result:', result);
    
    notify({
      display: true,
      message: t('external_services.google_calendar.sync_complete', {
        created: result.events_created || 0,
        total: result.events_processed || 0,
        updated: result.events_updated || 0,
      }),
      severity: Severity.INFO,
      title: t('external_services.google_calendar.success'),
    });
  }
  catch (error: any) {
    // Check if this is the "API not enabled" error
    if (error.message && (error.message.includes('Google Calendar API has not been used') || error.message.includes('accessNotConfigured'))) {
      // Extract project ID from the error message
      const projectMatch = error.message.match(/project (\d+)/);
      const projectId = projectMatch ? projectMatch[1] : 'YOUR_PROJECT_ID';
      
      // Set up the API error dialog
      apiErrorDetails.value = {
        projectId,
        setupUrl: `https://console.developers.google.com/apis/api/calendar-json.googleapis.com/overview?project=${projectId}`,
      };
      showApiErrorDialog.value = true;
    }
    else {
      // Show generic error notification for other errors
      notify({
        display: true,
        message: error.message || t('external_services.google_calendar.sync_failed'),
        severity: Severity.ERROR,
        title: t('external_services.google_calendar.error'),
      });
    }
  }
  finally {
    isSyncing.value = false;
  }
}

async function disconnect() {
  try {
    await googleCalendarApi.disconnect();
    isConnected.value = false;
    clientId.value = '';
    clientSecret.value = '';

    notify({
      display: true,
      message: t('external_services.google_calendar.disconnected'),
      severity: Severity.INFO,
      title: t('external_services.google_calendar.success'),
    });
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

function openSetupGuide() {
  showSetupDialog.value = true;
}

async function openApiSetupUrl() {
  try {
    if (apiErrorDetails.value.setupUrl) {
      await openUrl(apiErrorDetails.value.setupUrl);
    }
  } catch (error) {
    console.error('Failed to open API setup URL:', error);
  }
}

function cancelAuth() {
  stopPolling();
  showAuthDialog.value = false;
  verificationUrl.value = '';
  userCode.value = '';
}

async function openUrlSafely(url: string) {
  try {
    if (url && typeof url === 'string' && url.startsWith('https://')) {
      await openUrl(url);
      console.log('Browser opened via button');
    } else {
      console.error('Invalid URL passed to button:', url);
    }
  } catch (error) {
    console.error('Failed to open URL via button:', error);
  }
}
</script>

<template>
  <ServiceKeyCard
    :key-set="isConnected"
    :title="t('external_services.google_calendar.title')"
    :subtitle="t('external_services.google_calendar.description')"
    image-src="./assets/images/services/google-calendar.svg"
    :loading="isLoading"
  >
    <template #right>
      <RuiButton
        v-if="isConnected"
        data-test="sync-button"
        color="primary"
        variant="outlined"
        size="sm"
        :loading="isSyncing"
        :disabled="isSyncing"
        @click="syncCalendar()"
      >
        <template #prepend>
          <RuiIcon
            name="refresh-line"
            size="20"
          />
        </template>
        {{ t('external_services.google_calendar.sync_now') }}
      </RuiButton>
    </template>

    <div
      v-if="!isConnected"
      class="space-y-4"
    >
      <div class="text-body-2 text-rui-text-secondary">
        {{ t('external_services.google_calendar.setup_instructions') }}
        <RuiButton
          variant="text"
          size="sm"
          color="primary"
          @click="openSetupGuide()"
        >
          {{ t('external_services.google_calendar.view_setup_guide') }}
        </RuiButton>
      </div>

      <RuiTextField
        v-model="clientId"
        variant="outlined"
        color="primary"
        :label="t('external_services.google_calendar.client_id')"
        :hint="t('external_services.google_calendar.client_id_hint')"
      />

      <RuiTextField
        v-model="clientSecret"
        variant="outlined"
        color="primary"
        type="password"
        :label="t('external_services.google_calendar.client_secret')"
        :hint="t('external_services.google_calendar.client_secret_hint')"
      />

      <div class="flex gap-2">
        <RuiButton
          data-test="connect-button"
          color="primary"
          :disabled="!hasCredentials"
          @click="startAuth()"
        >
          {{ t('external_services.google_calendar.connect') }}
        </RuiButton>
      </div>
    </div>

    <div
      v-else
      class="space-y-4"
    >
      <div class="flex items-center gap-2 text-rui-success">
        <RuiIcon
          name="lu-circle-check"
          size="20"
        />
        <span class="text-body-1">{{ t('external_services.google_calendar.connected_status') }}</span>
      </div>

      <div class="text-body-2 text-rui-text-secondary">
        {{ t('external_services.google_calendar.sync_info') }}
      </div>

      <div class="flex gap-2">
        <RuiButton
          data-test="sync-button-main"
          color="primary"
          variant="outlined"
          :loading="isSyncing"
          :disabled="isSyncing"
          @click="syncCalendar()"
        >
          <template #prepend>
            <RuiIcon
              name="refresh-line"
              size="20"
            />
          </template>
          {{ t('external_services.google_calendar.sync_now') }}
        </RuiButton>
        
        <RuiButton
          color="error"
          variant="outlined"
          @click="disconnect()"
        >
          {{ t('external_services.google_calendar.disconnect') }}
        </RuiButton>
      </div>
    </div>

    <!-- Device Flow Auth Dialog -->
    <RuiDialog
      v-model="showAuthDialog"
      data-test="auth-dialog"
      max-width="600"
      persistent
      :z-index="9999"
    >
      <RuiCard>
        <template #header>
          {{ t('external_services.google_calendar.device_auth_title') }}
        </template>

        <div class="space-y-4">
          <p class="text-body-2">
            {{ t('external_services.google_calendar.device_auth_instructions') }}
          </p>

          <div class="p-4 bg-rui-grey-100 dark:bg-rui-grey-800 rounded">
            <div class="text-body-2 font-medium mb-2">
              {{ t('external_services.google_calendar.verification_url') }}:
            </div>
            <div class="text-body-1 break-all mb-2">
              <a 
                :href="verificationUrl" 
                target="_blank" 
                rel="noopener noreferrer"
                class="text-primary hover:underline"
              >
                {{ verificationUrl }}
              </a>
            </div>
            <RuiButton
              size="sm"
              variant="outlined"
              color="primary"
              @click="() => openUrlSafely(verificationUrl)"
            >
              Open in Browser
            </RuiButton>

            <div class="text-body-2 font-medium mb-2 mt-4">
              {{ t('external_services.google_calendar.user_code') }}:
            </div>
            <div class="text-h6 font-mono tracking-wider text-primary">
              {{ userCode }}
            </div>
          </div>

          <div
            v-if="isPolling"
            class="flex items-center gap-2 text-rui-text-secondary"
          >
            <RuiIcon
              name="lu-refresh-ccw"
              class="animate-spin"
              size="16"
            />
            <span class="text-body-2">{{ t('external_services.google_calendar.waiting_for_auth') }}</span>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <RuiButton
              variant="text"
              @click="cancelAuth()"
            >
              {{ t('common.actions.cancel') }}
            </RuiButton>
          </div>
        </template>
      </RuiCard>
    </RuiDialog>

    <!-- Setup Guide Dialog -->
    <RuiDialog
      v-model="showSetupDialog"
      max-width="800"
      persistent
      :z-index="9999"
    >
      <RuiCard>
        <template #header>
          {{ t('external_services.google_calendar.setup_guide_title') }}
        </template>

        <div class="space-y-4">
          <ol class="list-decimal list-inside space-y-2 text-body-2">
            <li>{{ t('external_services.google_calendar.setup_step_1') }}</li>
            <li>{{ t('external_services.google_calendar.setup_step_2') }}</li>
            <li>{{ t('external_services.google_calendar.setup_step_3') }}</li>
            <li>{{ t('external_services.google_calendar.setup_step_4') }}</li>
            <li>{{ t('external_services.google_calendar.setup_step_5') }}</li>
            <li>{{ t('external_services.google_calendar.setup_step_6') }}</li>
          </ol>
        </div>

        <template #footer>
          <div class="flex justify-end">
            <RuiButton
              color="primary"
              @click="showSetupDialog = false"
            >
              {{ t('common.actions.close') }}
            </RuiButton>
          </div>
        </template>
      </RuiCard>
    </RuiDialog>

    <!-- API Setup Error Dialog -->
    <RuiDialog
      v-model="showApiErrorDialog"
      max-width="600"
      data-test="api-error-dialog"
    >
      <RuiCard>
        <template #header>
          <div class="flex items-center gap-2">
            <RuiIcon
              name="lu-alert-circle"
              size="24"
              class="text-rui-error"
            />
            {{ t('external_services.google_calendar.setup_required') }}
          </div>
        </template>

        <div class="space-y-4">
          <div class="text-body-1">
            {{ t('external_services.google_calendar.api_error_explanation') }}
          </div>

          <div class="bg-rui-grey-100 dark:bg-rui-grey-800 p-4 rounded border-l-4 border-rui-warning">
            <div class="text-body-2 font-medium mb-2">
              {{ t('external_services.google_calendar.steps_to_fix') }}
            </div>
            <ol class="list-decimal list-inside space-y-1 text-body-2">
              <li>{{ t('external_services.google_calendar.step_1_click_link') }}</li>
              <li>{{ t('external_services.google_calendar.step_2_enable_api') }}</li>
              <li>{{ t('external_services.google_calendar.step_3_wait') }}</li>
              <li>{{ t('external_services.google_calendar.step_4_try_again') }}</li>
            </ol>
          </div>

          <div class="text-body-2 text-rui-text-secondary">
            <strong>{{ t('external_services.google_calendar.project_id') }}:</strong> {{ apiErrorDetails.projectId }}
          </div>
        </div>

        <template #footer>
          <div class="flex justify-between items-center w-full">
            <RuiButton
              color="primary"
              @click="openApiSetupUrl()"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-external-link"
                  size="16"
                />
              </template>
              {{ t('external_services.google_calendar.open_google_console') }}
            </RuiButton>
            
            <RuiButton
              variant="text"
              @click="showApiErrorDialog = false"
            >
              {{ t('common.actions.close') }}
            </RuiButton>
          </div>
        </template>
      </RuiCard>
    </RuiDialog>
  </ServiceKeyCard>
</template>
