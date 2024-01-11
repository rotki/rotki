<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import Fragment from '@/components/helper/Fragment';
import {
  type DatabaseInfo,
  type UserDbBackup,
  type UserDbBackupWithId
} from '@/types/backup';

const { t } = useI18n();

const backupInfo = ref<DatabaseInfo | null>();
const selected = ref<UserDbBackupWithId[]>([]);
const loading = ref(false);
const saving = ref(false);

const backups = useRefMap(
  backupInfo,
  info =>
    info?.userdb?.backups.map((x, index) => ({ ...x, id: index + 1 })) ?? []
);

const { notify } = useNotificationsStore();

const directory = computed(() => {
  const info = get(backupInfo);
  if (!info) {
    return '';
  }
  const { filepath } = info.userdb.info;

  let index = filepath.lastIndexOf('/');
  if (index === -1) {
    index = filepath.lastIndexOf('\\');
  }

  return filepath.slice(0, index + 1);
});

const userDb = computed(() => {
  const info = get(backupInfo);
  return {
    size: info ? size(info.userdb.info.size) : '0',
    version: info ? info.userdb.info.version.toString() : '0'
  };
});

const globalDb = computed(() => {
  const info = get(backupInfo);
  return {
    schema: info ? info.globaldb.globaldbSchemaVersion.toString() : '0',
    assets: info ? info.globaldb.globaldbAssetsVersion.toString() : '0'
  };
});

const { info, createBackup, deleteBackup } = useBackupApi();

const loadInfo = async () => {
  try {
    set(loading, true);
    set(backupInfo, await info());
  } catch (e: any) {
    logger.error(e);
    notify({
      display: true,
      title: t('database_backups.load_error.title'),
      message: t('database_backups.load_error.message', {
        message: e.message
      })
    });
  } finally {
    set(loading, false);
  }
};
const isSameEntry = (firstDb: UserDbBackup, secondDb: UserDbBackup) =>
  firstDb.version === secondDb.version &&
  firstDb.time === secondDb.time &&
  firstDb.size === secondDb.size;

const massRemove = async () => {
  const currentSelection = get(selected);
  const filepaths = currentSelection.map(db => getFilepath(db, directory));
  try {
    await deleteBackup(filepaths);
    const backups = get(backupInfo);
    if (backups) {
      const info: DatabaseInfo = { ...backups };
      currentSelection.forEach((db: UserDbBackup) => {
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
    notify({
      display: true,
      title: t('database_backups.delete_error.title'),
      message: t('database_backups.delete_error.mass_message', {
        message: e.message
      })
    });
  }
};

const remove = async (db: UserDbBackup) => {
  const filepath = getFilepath(db, directory);
  try {
    await deleteBackup([filepath]);
    const backups = get(backupInfo);
    if (backups) {
      const info: DatabaseInfo = { ...backups };
      const index = info.userdb.backups.findIndex(backup =>
        isSameEntry(backup, db)
      );
      info.userdb.backups.splice(index, 1);
      set(backupInfo, info);

      const currentSelection = get(selected);
      if (currentSelection.length > 0) {
        set(
          selected,
          currentSelection.filter(item => !isSameEntry(item, db))
        );
      }
    }
  } catch (e: any) {
    logger.error(e);
    notify({
      display: true,
      title: t('database_backups.delete_error.title'),
      message: t('database_backups.delete_error.message', {
        file: filepath,
        message: e.message
      })
    });
  }
};

const backup = async () => {
  try {
    set(saving, true);
    const filepath = await createBackup();
    notify({
      display: true,
      severity: Severity.INFO,
      title: t('database_backups.backup.title'),
      message: t('database_backups.backup.message', {
        filepath
      })
    });

    await loadInfo();
  } catch (e: any) {
    logger.error(e);
    notify({
      display: true,
      title: t('database_backups.backup_error.title'),
      message: t('database_backups.backup_error.message', {
        message: e.message
      })
    });
  } finally {
    set(saving, false);
  }
};

const { show } = useConfirmStore();

const showMassDeleteConfirmation = () => {
  show(
    {
      title: t('database_backups.confirm.title'),
      message: t('database_backups.confirm.mass_message', {
        length: get(selected).length
      })
    },
    massRemove
  );
};

onMounted(loadInfo);
</script>

<template>
  <Fragment>
    <DatabaseInfoDisplay
      class="mt-8"
      :directory="directory"
      :global-db="globalDb"
      :user-db="userDb"
    />
    <RuiCard class="mt-8">
      <template #header>
        <CardTitle>
          <RefreshButton
            :loading="loading"
            :tooltip="t('database_manager.refresh_tooltip')"
            @refresh="loadInfo()"
          />
          {{ t('backup_manager.title') }}
        </CardTitle>
      </template>
      <DatabaseBackups
        :loading="loading"
        :items="backups"
        :directory="directory"
        :selected.sync="selected"
        @remove="remove($event)"
      />
      <template #footer>
        <div class="flex gap-3">
          <RuiButton
            color="primary"
            :disabled="saving"
            :loading="saving"
            @click="backup()"
          >
            {{ t('backup_manager.backup_button') }}
          </RuiButton>
          <RuiButton
            v-if="selected.length > 0"
            color="error"
            @click="showMassDeleteConfirmation()"
          >
            {{ t('backup_manager.delete_selected') }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
  </Fragment>
</template>
