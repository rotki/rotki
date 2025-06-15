<script setup lang="ts">
import ServiceKeyCard from '@/components/settings/api-keys/ServiceKeyCard.vue';
import { useGoogleCalendarApi } from '@/composables/api/settings/google-calendar';
import { useInterop } from '@/composables/electron-interop';
import { useNotificationsStore } from '@/store/notifications';
import { Severity } from '@rotki/common';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n({ useScope: 'global' });

const googleCalendarApi = useGoogleCalendarApi();
const { notify } = useNotificationsStore();
const { openUrl } = useInterop();

const clientId = ref('');
const clientSecret = ref('');
const authCode = ref('');
const showAuthDialog = ref(false);
const showSetupDialog = ref(false);
const authUrl = ref('');
const isConnected = ref(false);
const isSyncing = ref(false);
const isLoading = ref(false);

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
    const response = await googleCalendarApi.startAuth(clientId.value, clientSecret.value);

    // Handle the nested response structure: {result: {authUrl: "..."}}
    const authUrlFromResponse = response?.result?.authUrl || response?.auth_url;

    if (authUrlFromResponse && typeof authUrlFromResponse === 'string') {
      authUrl.value = authUrlFromResponse;
      showAuthDialog.value = true;

      // Open auth URL in external browser
      // Use setTimeout to ensure the dialog is shown first and URL is properly set
      setTimeout(async () => {
        if (authUrl.value) {
          await openUrl(authUrl.value);
        }
      }, 200);
    }
    else {
      throw new Error(`Invalid response from server: missing authorization URL`);
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
}

async function completeAuth() {
  if (!authCode.value) {
    notify({
      display: true,
      message: t('external_services.google_calendar.auth_code_required'),
      severity: Severity.ERROR,
      title: t('external_services.google_calendar.error'),
    });
    return;
  }

  try {
    // Build the full redirect URL with the auth code
    const redirectUrl = `http://localhost:8080?code=${authCode.value}`;
    await googleCalendarApi.completeAuth(redirectUrl);

    isConnected.value = true;
    showAuthDialog.value = false;
    authCode.value = '';

    notify({
      display: true,
      message: t('external_services.google_calendar.connected'),
      severity: Severity.INFO,
      title: t('external_services.google_calendar.success'),
    });
  }
  catch (error: any) {
    notify({
      display: true,
      message: error.message || t('external_services.google_calendar.auth_complete_failed'),
      severity: Severity.ERROR,
      title: t('external_services.google_calendar.error'),
    });
  }
}

async function syncCalendar() {
  isSyncing.value = true;
  try {
    const result = await googleCalendarApi.syncCalendar();
    notify({
      display: true,
      message: t('external_services.google_calendar.sync_complete', {
        created: result.events_created,
        total: result.events_processed,
        updated: result.events_updated,
      }),
      severity: Severity.INFO,
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
          name="checkbox-circle-line"
          size="20"
        />
        <span class="text-body-1">{{ t('external_services.google_calendar.connected_status') }}</span>
      </div>

      <div class="text-body-2 text-rui-text-secondary">
        {{ t('external_services.google_calendar.sync_info') }}
      </div>

      <div class="flex gap-2">
        <RuiButton
          color="error"
          variant="outlined"
          @click="disconnect()"
        >
          {{ t('external_services.google_calendar.disconnect') }}
        </RuiButton>
      </div>
    </div>

    <!-- Auth Code Dialog -->
    <RuiDialog
      v-model="showAuthDialog"
      max-width="600"
      persistent
      :z-index="9999"
    >
      <RuiCard>
        <template #header>
          {{ t('external_services.google_calendar.auth_dialog_title') }}
        </template>

        <div class="space-y-4">
          <p class="text-body-2">
            {{ t('external_services.google_calendar.auth_dialog_instructions') }}
          </p>

          <RuiTextField
            v-model="authCode"
            variant="outlined"
            color="primary"
            :label="t('external_services.google_calendar.auth_code_label')"
            :hint="t('external_services.google_calendar.auth_code_hint')"
          />
        </div>

        <template #footer>
          <div class="flex justify-end gap-2">
            <RuiButton
              variant="text"
              @click="showAuthDialog = false; authCode = ''"
            >
              {{ t('common.actions.cancel') }}
            </RuiButton>
            <RuiButton
              color="primary"
              :disabled="!authCode"
              @click="completeAuth()"
            >
              {{ t('external_services.google_calendar.complete_auth') }}
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

          <div class="bg-rui-warning-lighter p-4 rounded">
            <p class="text-body-2">
              <strong>{{ t('external_services.google_calendar.important') }}:</strong>
              {{ t('external_services.google_calendar.redirect_uri_note') }}
            </p>
            <code class="block mt-2 p-2 bg-rui-grey-100 rounded text-black">{{ t('external_services.google_calendar.redirect_uri') }}</code>
          </div>
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
  </ServiceKeyCard>
</template>
