<script setup lang="ts">
import type { DatabaseInfo, UserDbBackup, UserDbBackupWithId } from '@/modules/session/backup';
import { Severity } from '@rotki/common';
import { getFilepath } from '@/modules/core/common/file/file';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useBackupApi } from '@/modules/session/api/use-backup-api';
import DatabaseBackups from '@/modules/settings/data-security/backups/DatabaseBackups.vue';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';

const { t } = useI18n({ useScope: 'global' });

const backupInfo = ref<DatabaseInfo>();
const selected = ref<UserDbBackupWithId[]>([]);
const loading = ref<boolean>(false);
const saving = ref<boolean>(false);

const { notify } = useNotificationDispatcher();
const { createBackup, deleteBackup, info } = useBackupApi();
const { show } = useConfirmStore();

const backups = computed<UserDbBackupWithId[]>(
  () => get(backupInfo)?.userdb?.backups.map((x, index) => ({ ...x, id: index + 1 })) ?? [],
);

const directory = computed<string>(() => {
  const info = get(backupInfo);
  if (!info)
    return '';

  const { filepath } = info.userdb.info;

  let index = filepath.lastIndexOf('/');
  if (index === -1)
    index = filepath.lastIndexOf('\\');

  return filepath.slice(0, index + 1);
});

async function loadInfo() {
  try {
    set(loading, true);
    set(backupInfo, await info());
  }
  catch (error: unknown) {
    logger.error(error);
    notify({
      display: true,
      message: t('database_backups.load_error.message', {
        message: getErrorMessage(error),
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
  const filepaths = currentSelection.map(db => getFilepath(db, get(directory)));
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
  catch (error: unknown) {
    logger.error(error);
    notify({
      display: true,
      message: t('database_backups.delete_error.mass_message', {
        message: getErrorMessage(error),
      }),
      title: t('database_backups.delete_error.title'),
    });
  }
}

async function remove(db: UserDbBackup) {
  const filepath = getFilepath(db, get(directory));
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
  catch (error: unknown) {
    logger.error(error);
    notify({
      display: true,
      message: t('database_backups.delete_error.message', {
        file: filepath,
        message: getErrorMessage(error),
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
  catch (error: unknown) {
    logger.error(error);
    notify({
      display: true,
      message: t('database_backups.backup_error.message', {
        message: getErrorMessage(error),
      }),
      title: t('database_backups.backup_error.title'),
    });
  }
  finally {
    set(saving, false);
  }
}

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
