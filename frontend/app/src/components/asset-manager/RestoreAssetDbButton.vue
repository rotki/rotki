<template>
  <div>
    <template v-if="dropdown">
      <v-menu offset-y>
        <template #activator="{ on }">
          <v-btn color="primary" depressed v-on="on">
            {{ t('asset_update.restore.title') }}
          </v-btn>
        </template>
        <v-list>
          <v-list-item two-line link @click="restoreClick('soft')">
            <v-list-item-content>
              <v-list-item-title>
                {{ t('asset_update.restore.soft_reset') }}
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ t('asset_update.restore.soft_reset_hint') }}
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>
          <v-list-item two-line link @click="restoreClick('hard')">
            <v-list-item-content>
              <v-list-item-title>
                {{ t('asset_update.restore.hard_reset') }}
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ t('asset_update.restore.hard_reset_hint') }}
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>
        </v-list>
      </v-menu>
    </template>
    <template v-else>
      <v-tooltip top max-width="200">
        <template #activator="{ on }">
          <v-btn
            outlined
            depressed
            color="primary"
            v-on="on"
            @click="restoreClick('soft')"
          >
            {{ t('asset_update.restore.soft_reset') }}
          </v-btn>
        </template>
        <span>{{ t('asset_update.restore.soft_reset_hint') }}</span>
      </v-tooltip>
      <v-tooltip top max-width="200">
        <template #activator="{ on }">
          <v-btn
            class="ml-4"
            depressed
            color="primary"
            v-on="on"
            @click="restoreClick('hard')"
          >
            {{ t('asset_update.restore.hard_reset') }}
          </v-btn>
        </template>
        <span>{{ t('asset_update.restore.hard_reset_hint') }}</span>
      </v-tooltip>
    </template>
    <confirm-dialog
      :display="confirmRestore"
      :title="tc('asset_update.restore.delete_confirmation.title')"
      :message="
        resetType === 'soft'
          ? tc('asset_update.restore.delete_confirmation.soft_reset_message')
          : tc('asset_update.restore.delete_confirmation.hard_reset_message')
      "
      @confirm="restoreAssets"
      @cancel="confirmRestore = false"
    />
    <confirm-dialog
      :display="doubleConfirmation"
      :title="tc('asset_update.restore.hard_restore_confirmation.title')"
      :message="tc('asset_update.restore.hard_restore_confirmation.message')"
      @confirm="confirmReset"
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
  </div>
</template>

<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import { type Ref } from 'vue';
import { useBackendManagement } from '@/composables/backend';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/main';
import { useNotifications } from '@/store/notifications';
import { useSessionStore } from '@/store/session';

defineProps({
  dropdown: {
    required: false,
    type: Boolean,
    default: false
  }
});

const confirmRestore = ref(false);
const doubleConfirmation = ref(false);
const done = ref(false);
type ResetType = 'soft' | 'hard';
const resetType: Ref<ResetType> = ref('soft');

const { notify } = useNotifications();
const { connect, setConnected } = useMainStore();
const { logout } = useSessionStore();

const { restartBackend } = useBackendManagement();

const { t, tc } = useI18n();

const restoreClick = (type: ResetType) => {
  set(resetType, type);
  set(confirmRestore, true);
};

async function confirmReset() {
  await restoreAssets();
}

async function restoreAssets() {
  try {
    set(confirmRestore, false);
    const updated = await api.assets.restoreAssetsDatabase(
      get(resetType),
      get(resetType) === 'hard'
    );
    if (updated) {
      set(done, true);
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
