<template>
  <fragment>
    <database-info-display
      class="mt-8"
      :directory="directory"
      :global-db="globalDb"
      :user-db="userDb"
    />
    <card outlined-body class="mt-8">
      <template #title>{{ $t('backup_manager.title') }}</template>
      <template #details>
        <refresh-button
          :loading="loading"
          :tooltip="$t('database_manager.refresh_tooltip')"
          @refresh="loadInfo"
        />
      </template>
      <database-backups
        :loading="loading"
        :items="backups"
        :directory="directory"
        @remove="remove"
      />
      <template #buttons>
        <v-btn
          depressed
          color="primary"
          :disabled="saving"
          :loading="saving"
          @click="backup"
        >
          {{ $t('backup_manager.backup_button') }}
        </v-btn>
      </template>
    </card>
  </fragment>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  onMounted,
  Ref,
  ref
} from '@vue/composition-api';
import Fragment from '@/components/helper/Fragment';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import DatabaseBackups from '@/components/settings/data-security/backups/DatabaseBackups.vue';
import DatabaseInfoDisplay from '@/components/settings/data-security/backups/DatabaseInfoDisplay.vue';
import { getFilepath } from '@/components/settings/data-security/backups/utils';
import i18n from '@/i18n';
import { DatabaseInfo, UserDbBackup } from '@/services/backup/types';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
import { Severity } from '@/store/notifications/consts';
import { size } from '@/utils/data';
import { logger } from '@/utils/logging';

const setupBackupInfo = () => {
  const backupInfo = ref<DatabaseInfo | null>();
  const loading = ref(false);

  const backups = computed(() => {
    return backupInfo?.value?.userdb?.backups ?? [];
  });

  const directory = computed(() => {
    const info = backupInfo.value;
    if (!info) {
      return '';
    }
    const { filepath } = info.userdb.info;

    let index = filepath.lastIndexOf('/');
    let separatorLength = 1;
    if (index === -1) {
      index = filepath.lastIndexOf('\\');
      separatorLength = 2;
    }

    return filepath.substr(0, index + separatorLength);
  });

  const userDb = computed(() => {
    const info = backupInfo.value;
    return {
      size: info ? size(info.userdb.info.size) : '0',
      version: info ? info.userdb.info.version : '0'
    };
  });

  const globalDb = computed(() => {
    const info = backupInfo.value;
    return {
      schema: info ? info.globaldb.globaldbSchemaVersion : '0',
      assets: info ? info.globaldb.globaldbAssetsVersion : '0'
    };
  });

  const loadInfo = async () => {
    try {
      loading.value = true;
      backupInfo.value = await api.backups.info();
    } catch (e: any) {
      logger.error(e);
      const { notify } = useNotifications();
      notify({
        display: true,
        title: i18n.t('database_backups.load_error.title').toString(),
        message: i18n
          .t('database_backups.load_error.message', {
            message: e.message
          })
          .toString()
      });
    } finally {
      loading.value = false;
    }
  };
  onMounted(loadInfo);
  return {
    backups,
    backupInfo,
    userDb,
    globalDb,
    directory,
    loading,
    loadInfo
  };
};

function setupBackupActions(
  directory: Ref<string>,
  backupInfo: Ref<DatabaseInfo | null | undefined>,
  refresh: () => Promise<void>
) {
  const remove = async (db: UserDbBackup) => {
    const filepath = getFilepath(db, directory);
    try {
      await api.backups.deleteBackup(filepath);
      if (backupInfo.value) {
        const info: DatabaseInfo = { ...backupInfo.value };
        const index = info.userdb.backups.findIndex(
          ({ size, time, version }) =>
            version === db.version && time === db.time && size === db.size
        );
        info.userdb.backups.splice(index, 1);
        backupInfo.value = info;
      }
    } catch (e: any) {
      logger.error(e);
      const { notify } = useNotifications();
      notify({
        display: true,
        title: i18n.t('database_backups.delete_error.title').toString(),
        message: i18n
          .t('database_backups.delete_error.message', {
            file: filepath,
            message: e.message
          })
          .toString()
      });
    }
  };

  const saving = ref(false);

  const backup = async () => {
    try {
      saving.value = true;
      const filepath = await api.backups.createBackup();
      const { notify } = useNotifications();
      notify({
        display: true,
        severity: Severity.INFO,
        title: i18n.t('database_backups.backup.title').toString(),
        message: i18n
          .t('database_backups.backup.message', {
            filepath
          })
          .toString()
      });

      await refresh();
    } catch (e: any) {
      logger.error(e);
      const { notify } = useNotifications();
      notify({
        display: true,
        title: i18n.t('database_backups.backup_error.title').toString(),
        message: i18n
          .t('database_backups.backup_error.message', {
            message: e.message
          })
          .toString()
      });
    } finally {
      saving.value = false;
    }
  };
  return { remove, backup, saving };
}

const BackupManager = defineComponent({
  name: 'BackupManager',
  components: {
    Fragment,
    RefreshButton,
    DatabaseInfoDisplay,
    DatabaseBackups
  },
  setup() {
    const getBackupInfo = setupBackupInfo();
    const { backupInfo, directory } = getBackupInfo;

    return {
      ...getBackupInfo,
      ...setupBackupActions(directory, backupInfo, getBackupInfo.loadInfo)
    };
  }
});
export default BackupManager;
</script>
