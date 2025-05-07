<script setup lang="ts">
import type { DatabaseInfo, UserDbBackup, UserDbBackupWithId } from '@/types/backup';
import DatabaseBackups from '@/components/settings/data-security/backups/DatabaseBackups.vue';
import SettingCategoryHeader from '@/components/settings/SettingCategoryHeader.vue';
import { useBackupApi } from '@/composables/api/backup';
import { useRefMap } from '@/composables/utils/useRefMap';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';
import { getFilepath } from '@/utils/file';
import { logger } from '@/utils/logging';
import { Severity } from '@rotki/common';

const { t } = useI18n({ useScope: 'global' });

const backupInfo = ref<DatabaseInfo>();
const selected = ref<UserDbBackupWithId[]>([]);
const loading = ref(false);
const saving = ref(false);

const backups = useRefMap(
  backupInfo,
  info => info?.userdb?.backups.map((x, index) => ({ ...x, id: index + 1 })) ?? [],
);

const { notify } = useNotificationsStore();

const directory = computed(() => {
  const info = get(backupInfo);
  if (!info)
    return '';

  const { filepath } = info.userdb.info;

  let index = filepath.lastIndexOf('/');
  if (index === -1)
    index = filepath.lastIndexOf('\\');

  return filepath.slice(0, index + 1);
});

const { createBackup, deleteBackup, info } = useBackupApi();

async function loadInfo() {
  try {
    set(loading, true);
    set(backupInfo, await info());
  }
  catch (error: any) {
    logger.error(error);
    notify({
      display: true,
      message: t('database_backups.load_error.message', {
        message: error.message,
      }),
      title: t('database_backups.load_error.title'),
    });
  }
  finally {
    set(loading, false);
  }
}

function isSameEntry(firstDb: UserDbBackup, secondDb: UserDbBackup) {
  return firstDb.version === secondDb.version && firstDb.time === secondDb.time && firstDb.size === secondDb.size;
}

async function massRemove() {
  const currentSelection = get(selected);
  const filepaths = currentSelection.map(db => getFilepath(db, directory));
  try {
    await deleteBackup(filepaths);
    const backups = get(backupInfo);
    if (backups) {
      const info: DatabaseInfo = { ...backups };
      currentSelection.forEach((db: UserDbBackup) => {
        const index = info.userdb.backups.findIndex(backup => isSameEntry(backup, db));
        info.userdb.backups.splice(index, 1);
      });
      set(backupInfo, info);
    }
    set(selected, []);
  }
  catch (error: any) {
    logger.error(error);
    notify({
      display: true,
      message: t('database_backups.delete_error.mass_message', {
        message: error.message,
      }),
      title: t('database_backups.delete_error.title'),
    });
  }
}

async function remove(db: UserDbBackup) {
  const filepath = getFilepath(db, directory);
  try {
    await deleteBackup([filepath]);
    const backups = get(backupInfo);
    if (backups) {
      const info: DatabaseInfo = { ...backups };
      const index = info.userdb.backups.findIndex(backup => isSameEntry(backup, db));
      info.userdb.backups.splice(index, 1);
      set(backupInfo, info);

      const currentSelection = get(selected);
      if (currentSelection.length > 0) {
        set(
          selected,
          currentSelection.filter(item => !isSameEntry(item, db)),
        );
      }
    }
  }
  catch (error: any) {
    logger.error(error);
    notify({
      display: true,
      message: t('database_backups.delete_error.message', {
        file: filepath,
        message: error.message,
      }),
      title: t('database_backups.delete_error.title'),
    });
  }
}

async function backup() {
  try {
    set(saving, true);
    const filepath = await createBackup();
    notify({
      display: true,
      message: t('database_backups.backup.message', {
        filepath,
      }),
      severity: Severity.INFO,
      title: t('database_backups.backup.title'),
    });

    await loadInfo();
  }
  catch (error: any) {
    logger.error(error);
    notify({
      display: true,
      message: t('database_backups.backup_error.message', {
        message: error.message,
      }),
      title: t('database_backups.backup_error.title'),
    });
  }
  finally {
    set(saving, false);
  }
}

const { show } = useConfirmStore();

function showMassDeleteConfirmation() {
  show(
    {
      message: t('database_backups.confirm.mass_message', {
        length: get(selected).length,
      }),
      title: t('database_backups.confirm.title'),
    },
    massRemove,
  );
}

onMounted(loadInfo);
</script>

<template>
  <div>
    <div class="pb-5 flex flex-wrap gap-4 items-center justify-between">
      <SettingCategoryHeader>
        <template #title>
          {{ t('database_settings.user_backups.title') }}
        </template>
        <template #subtitle>
          {{ t('database_settings.user_backups.subtitle') }}
        </template>
      </SettingCategoryHeader>
      <div class="flex flex-wrap gap-2">
        <RuiButton
          v-if="selected.length > 0"
          color="error"
          @click="showMassDeleteConfirmation()"
        >
          {{ t('database_settings.user_backups.delete_selected') }}
        </RuiButton>
        <RuiButton
          variant="outlined"
          color="primary"
          :loading="loading"
          @click="loadInfo()"
        >
          <template #prepend>
            <RuiIcon
              name="lu-refresh-ccw"
              size="16"
            />
          </template>
          {{ t('common.refresh') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :disabled="saving"
          :loading="saving"
          @click="backup()"
        >
          {{ t('database_settings.user_backups.backup_button') }}
        </RuiButton>
      </div>
    </div>
    <DatabaseBackups
      v-model:selected="selected"
      :loading="loading"
      :items="backups"
      :directory="directory"
      @remove="remove($event)"
    />
  </div>
</template>
