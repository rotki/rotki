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
          <v-list-item two-line link @click="showRestoreConfirmation('soft')">
            <v-list-item-content>
              <v-list-item-title>
                {{ t('asset_update.restore.soft_reset') }}
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ t('asset_update.restore.soft_reset_hint') }}
              </v-list-item-subtitle>
            </v-list-item-content>
          </v-list-item>
          <v-list-item two-line link @click="showRestoreConfirmation('hard')">
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
            @click="showRestoreConfirmation('soft')"
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
            @click="showRestoreConfirmation('hard')"
          >
            {{ t('asset_update.restore.hard_reset') }}
          </v-btn>
        </template>
        <span>{{ t('asset_update.restore.hard_reset_hint') }}</span>
      </v-tooltip>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import { api } from '@/services/rotkehlchen-api';
import { useMainStore } from '@/store/main';
import { useNotificationsStore } from '@/store/notifications';
import { useSessionStore } from '@/store/session';
import { useConfirmStore } from '@/store/confirm';

defineProps({
  dropdown: {
    required: false,
    type: Boolean,
    default: false
  }
});

type ResetType = 'soft' | 'hard';

const { notify } = useNotificationsStore();
const { connect, setConnected } = useMainStore();
const { logout } = useSessionStore();

const { restartBackend } = useBackendManagement();

const { t, tc } = useI18n();

async function restoreAssets(resetType: ResetType) {
  try {
    const updated = await api.assets.restoreAssetsDatabase(
      resetType,
      resetType === 'hard'
    );
    if (updated) {
      showDoneConfirmation();
    }
  } catch (e: any) {
    const title = t('asset_update.restore.title').toString();
    const message = e.toString();
    if (message.includes('There are assets that can not')) {
      showDoubleConfirmation(resetType);
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

const { show } = useConfirmStore();

const showRestoreConfirmation = (type: ResetType) => {
  show(
    {
      title: tc('asset_update.restore.delete_confirmation.title'),
      message:
        type === 'soft'
          ? tc('asset_update.restore.delete_confirmation.soft_reset_message')
          : tc('asset_update.restore.delete_confirmation.hard_reset_message')
    },
    () => restoreAssets(type)
  );
};

const showDoubleConfirmation = (type: ResetType) => {
  show(
    {
      title: tc('asset_update.restore.hard_restore_confirmation.title'),
      message: tc('asset_update.restore.hard_restore_confirmation.message')
    },
    () => restoreAssets(type)
  );
};

const showDoneConfirmation = () => {
  show(
    {
      title: tc('asset_update.restore.success.title'),
      message: tc('asset_update.restore.success.description'),
      primaryAction: tc('asset_update.success.ok'),
      singleAction: true
    },
    updateComplete
  );
};
</script>
