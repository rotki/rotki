<template>
  <fragment>
    <card class="mt-8">
      <template #title>{{ $t('asset_update.restore.title') }}</template>
      <template #subtitle>{{ $t('asset_update.restore.subtitle') }}</template>
      <template #buttons>
        <v-btn
          depressed
          color="primary"
          class="mt-2"
          @click="confirmRestore = true"
        >
          {{ $t('asset_update.restore.action') }}
        </v-btn>
      </template>
    </card>
    <confirm-dialog
      :display="confirmRestore"
      :title="$t('asset_update.restore.hard_restore_message.title')"
      :message="$t('asset_update.restore.hard_restore_message.message')"
      @confirm="restoreAssets"
      @cancel="confirmRestore = false"
    />
    <confirm-dialog
      :display="doubleConfirmation"
      :title="$t('asset_update.restore.hard_restore_confirmation.title')"
      :message="$t('asset_update.restore.hard_restore_confirmation.message')"
      @confirm="confirmHardReset"
      @cancel="doubleConfirmation = false"
    />
    <confirm-dialog
      v-if="done"
      single-action
      display
      :title="$t('asset_update.restore.success.title')"
      :primary-action="$t('asset_update.success.ok')"
      :message="$t('asset_update.restore.success.description')"
      @confirm="updateComplete()"
    />
  </fragment>
</template>

<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import { get, set } from '@vueuse/core';
import { ref } from 'vue';
import Fragment from '@/components/helper/Fragment';
import { useBackendManagement } from '@/composables/backend';
import i18n from '@/i18n';
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
    const title = i18n.t('asset_update.restore.title').toString();
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
