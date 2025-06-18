<script setup lang="ts">
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import { useGoogleCalendarApi } from '@/composables/api/settings/google-calendar';
import { useInterop } from '@/composables/electron-interop';
import { useNotificationsStore } from '@/store/notifications';
import { Severity } from '@rotki/common';
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n({ useScope: 'global' });

const googleCalendarApi = useGoogleCalendarApi();
const { notify } = useNotificationsStore();
const { openUrl } = useInterop();

const showApiErrorDialog = ref(false);
const apiErrorDetails = ref({ projectId: '', setupUrl: '' });
const isConnected = ref(false);
const isSyncing = ref(false);
const isLoading = ref(false);
const isAuthorizing = ref(false);

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

async function connectToGoogle() {
  isAuthorizing.value = true;
  try {
    // Step 1: Initialize the OAuth flow
    await googleCalendarApi.startAuth();

    // Step 2: Run the authorization (opens browser and waits for completion)
    notify({
      display: true,
      message: t('external_services.google_calendar.opening_browser'),
      severity: Severity.INFO,
      title: t('external_services.google_calendar.authorizing'),
    });

    const authResult = await googleCalendarApi.runAuth();

    if (authResult.success) {
      isConnected.value = true;
      notify({
        display: true,
        message: t('external_services.google_calendar.connected'),
        severity: Severity.INFO,
        title: t('external_services.google_calendar.success'),
      });
    }
  }
  catch (error: any) {
    notify({
      display: true,
      message: error.message || t('external_services.google_calendar.auth_failed'),
      severity: Severity.ERROR,
      title: t('external_services.google_calendar.error'),
    });
  }
  finally {
    isAuthorizing.value = false;
  }
}

async function syncCalendar() {
  isSyncing.value = true;
  try {
    const result = await googleCalendarApi.syncCalendar();

    notify({
      display: true,
      message: t('external_services.google_calendar.sync_complete', {
        created: result.eventsCreated || 0,
        total: result.eventsProcessed || 0,
        updated: result.eventsUpdated || 0,
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

async function openApiSetupUrl() {
  try {
    if (apiErrorDetails.value.setupUrl) {
      await openUrl(apiErrorDetails.value.setupUrl);
    }
  }
  catch (error) {
    console.error('Failed to open API setup URL:', error);
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
        {{ t('external_services.google_calendar.connect_description') }}
      </div>

      <div class="flex gap-2">
        <RuiButton
          data-test="connect-button"
          color="primary"
          :disabled="isAuthorizing"
          :loading="isAuthorizing"
          @click="connectToGoogle()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-link"
              size="20"
            />
          </template>
          {{ t('external_services.google_calendar.connect_to_google') }}
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
