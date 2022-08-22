<template>
  <div>
    <v-btn depressed color="primary" @click="confirmRestore = true">
      {{ $t('asset_update.restore.action') }}
    </v-btn>
    <confirm-dialog
      :display="confirmRestore"
      :title="$t('asset_update.restore.delete_confirmation.title')"
      :message="$t('asset_update.restore.delete_confirmation.message')"
      @confirm="restoreAssets"
      @cancel="confirmRestore = false"
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
  </div>
</template>

<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import { set } from '@vueuse/core';
import { ref } from 'vue';
import { useBackendManagement } from '@/composables/backend';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/main';
import { useNotifications } from '@/store/notifications';
import { useSessionStore } from '@/store/session';

const confirmRestore = ref(false);
const done = ref(false);

const { notify } = useNotifications();
const { connect, setConnected } = useMainStore();
const { logout } = useSessionStore();

const { restartBackend } = useBackendManagement();

const restoreAssets = async () => {
  try {
    set(confirmRestore, false);
    set(done, await api.assets.restoreAssetsDatabase('hard', false));
  } catch (e: any) {
    const title = i18n.t('asset_update.restore.title').toString();
    const message = e.toString();
    notify({
      title,
      message,
      severity: Severity.ERROR,
      display: true
    });
  }
};

async function updateComplete() {
  await logout();
  setConnected(false);
  await restartBackend();
  await connect();
}
</script>
