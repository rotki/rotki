<template>
  <fragment>
    <card class="mt-8">
      <template #title>{{ t('asset_update.restore.title') }}</template>
      <template #subtitle>{{ t('asset_update.restore.subtitle') }}</template>
      <template #buttons>
        <v-btn
          depressed
          color="primary"
          class="mt-2"
          @click="confirmRestore = true"
        >
          {{ t('asset_update.restore.action') }}
        </v-btn>
      </template>
    </card>
    <confirm-dialog
      :display="confirmRestore"
      :title="tc('asset_update.restore.hard_restore_message.title')"
      :message="tc('asset_update.restore.hard_restore_message.message')"
      @confirm="restoreAssets"
      @cancel="confirmRestore = false"
    />
    <confirm-dialog
      :display="doubleConfirmation"
      :title="tc('asset_update.restore.hard_restore_confirmation.title')"
      :message="tc('asset_update.restore.hard_restore_confirmation.message')"
      @confirm="confirmHardReset"
      @cancel="doubleConfirmation = false"
    />
    <confirm-dialog
      v-if="done"
      single-action
      display
      :title="tc('asset_update.restore.success.title')"
      :primary-action="tc('asset_update.success.ok')"
      :message="tc('asset_update.restore.success.description')"
      @confirm="updateComplete()"
    />
  </fragment>
</template>

<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import Fragment from '@/components/helper/Fragment';
import { useBackendManagement } from '@/composables/backend';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/main';
import { useNotifications } from '@/store/notifications';
import { useSessionStore } from '@/store/session';

const confirmRestore = ref(false);
const doubleConfirmation = ref(false);
const restoreHard = ref(false);
const done = ref(false);

const { notify } = useNotifications();
const { connect, setConnected } = useMainStore();
const { logout } = useSessionStore();

const { t, tc } = useI18n();

const { restartBackend } = useBackendManagement();

async function confirmHardReset() {
  set(restoreHard, true);
  await restoreAssets();
}

async function restoreAssets() {
  try {
    set(confirmRestore, false);
    const updated = await api.assets.restoreAssetsDatabase(
      'hard',
      get(restoreHard)
    );
    if (updated) {
      set(done, true);
      set(restoreHard, false);
    }
  } catch (e: any) {
    const title = t('asset_update.restore.title').toString();
    const message = e.toString();
    if (message.includes('There are assets that can not')) {
      set(doubleConfirmation, true);
    }
    notify({
      title,
      message,
      severity: Severity.ERROR,
      display: true
    });
  }
}

async function updateComplete() {
  await logout();
  setConnected(false);
  await restartBackend();
  await connect();
}
</script>
