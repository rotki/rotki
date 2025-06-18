<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useGoogleCalendarApi } from '@/composables/api/settings/google-calendar';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Severity } from '@rotki/common';

const { t } = useI18n({ useScope: 'global' });

const showMenu = ref(false);
const autoDelete = ref(true);
const autoCreateReminders = ref(true);

// Google Calendar integration
const googleCalendarApi = useGoogleCalendarApi();
const { notify } = useNotificationsStore();
const isConnected = ref(false);
const isSyncing = ref(false);
const isAuthorizing = ref(false);

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
    isConnected.value = response.authenticated;
  }
  catch (error: any) {
    console.error('Failed to check Google Calendar status:', error);
  }
}

async function connectToGoogle() {
  isAuthorizing.value = true;
  try {
    await googleCalendarApi.startAuth();

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

onMounted(() => {
  setAutoDelete();
  setAutoCreate();
  checkGoogleCalendarStatus();
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
          <div class="text-subtitle-2 font-medium mb-3 text-rui-text-secondary">
            {{ t('external_services.google_calendar.title') }}
          </div>

          <div
            v-if="!isConnected"
            class="space-y-3"
          >
            <div class="text-body-2 text-rui-text-secondary">
              {{ t('external_services.google_calendar.connect_description') }}
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
              <span class="text-body-2">{{ t('external_services.google_calendar.connected_status') }}</span>
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
                    name="refresh-line"
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
