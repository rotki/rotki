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
        :selected="selected"
        @change="onSelectedChange"
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
        <v-btn
          v-if="selected.length > 0"
          depressed
          color="error"
          @click="showConfirmMassDelete = true"
        >
          {{ $t('backup_manager.delete_selected') }}
        </v-btn>
      </template>
    </card>
    <confirm-dialog
      :display="!!showConfirmMassDelete"
      :title="$t('database_backups.confirm.title')"
      :message="
        $t('database_backups.confirm.mass_message', {
          length: selected.length
        })
      "
      @cancel="showConfirmMassDelete = false"
      @confirm="massRemove"
    />
  </fragment>
</template>

<script lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import {
  computed,
  defineComponent,
  onMounted,
  Ref,
  ref
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import Fragment from '@/components/helper/Fragment';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import DatabaseBackups from '@/components/settings/data-security/backups/DatabaseBackups.vue';
import DatabaseInfoDisplay from '@/components/settings/data-security/backups/DatabaseInfoDisplay.vue';
import { getFilepath } from '@/components/settings/data-security/backups/utils';
import i18n from '@/i18n';
import { DatabaseInfo, UserDbBackup } from '@/services/backup/types';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
import { size } from '@/utils/data';
import { logger } from '@/utils/logging';

const isSameEntry = (firstDb: UserDbBackup, secondDb: UserDbBackup) => {
  return (
    firstDb.version === secondDb.version &&
    firstDb.time === secondDb.time &&
    firstDb.size === secondDb.size
  );
};

const setupBackupInfo = () => {
  const backupInfo = ref<DatabaseInfo | null>();
  const loading = ref(false);

  const backups = computed(() => {
    return get(backupInfo)?.userdb?.backups ?? [];
  });

  const directory = computed(() => {
    const info = get(backupInfo);
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
    const info = get(backupInfo);
    return {
      size: info ? size(info.userdb.info.size) : '0',
      version: info ? info.userdb.info.version : '0'
    };
  });

  const globalDb = computed(() => {
    const info = get(backupInfo);
    return {
      schema: info ? info.globaldb.globaldbSchemaVersion : '0',
      assets: info ? info.globaldb.globaldbAssetsVersion : '0'
    };
  });

  const loadInfo = async () => {
    try {
      set(loading, true);
      set(backupInfo, await api.backups.info());
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
      set(loading, false);
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

const setupBackupActions = (
  directory: Ref<string>,
  backupInfo: Ref<DatabaseInfo | null | undefined>,
  refresh: () => Promise<void>,
  selected: Ref<UserDbBackup[]>,
  showConfirmMassDelete: Ref<boolean>
) => {
  const massRemove = async () => {
    const filepaths = get(selected).map(db => getFilepath(db, directory));
    try {
      await api.backups.deleteBackup(filepaths);
      if (get(backupInfo)) {
        const info: DatabaseInfo = { ...get(backupInfo)! };
        get(selected).forEach((db: UserDbBackup) => {
          const index = info.userdb.backups.findIndex(backup =>
            isSameEntry(backup, db)
          );
          info.userdb.backups.splice(index, 1);
        });
        set(backupInfo, info);
      }
      set(selected, []);
    } catch (e: any) {
      logger.error(e);
      const { notify } = useNotifications();
      notify({
        display: true,
        title: i18n.t('database_backups.delete_error.title').toString(),
        message: i18n
          .t('database_backups.delete_error.mass_message', {
            message: e.message
          })
          .toString()
      });
    }

    set(showConfirmMassDelete, false);
  };

  const remove = async (db: UserDbBackup) => {
    const filepath = getFilepath(db, directory);
    try {
      await api.backups.deleteBackup([filepath]);
      if (get(backupInfo)) {
        const info: DatabaseInfo = { ...get(backupInfo)! };
        const index = info.userdb.backups.findIndex(backup =>
          isSameEntry(backup, db)
        );
        info.userdb.backups.splice(index, 1);
        set(backupInfo, info);

        if (get(selected).length > 0) {
          set(
            selected,
            get(selected).filter(item => !isSameEntry(item, db))
          );
        }
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
      set(saving, true);
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
      set(saving, false);
    }
  };
  return { remove, massRemove, backup, saving };
};

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

    const showConfirmMassDelete = ref<boolean>(false);

    const selected = ref<UserDbBackup[]>([]);
    const onSelectedChange = (newSelected: UserDbBackup[]) => {
      set(selected, newSelected);
    };

    return {
      ...getBackupInfo,
      ...setupBackupActions(
        directory,
        backupInfo,
        getBackupInfo.loadInfo,
        selected,
        showConfirmMassDelete
      ),
      selected,
      showConfirmMassDelete,
      onSelectedChange
    };
  }
});
export default BackupManager;
</script>
