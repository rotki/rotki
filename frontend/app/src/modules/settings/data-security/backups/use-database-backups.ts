import type { ComputedRef, Ref } from 'vue';
import type { DatabaseInfo, UserDbBackup, UserDbBackupWithId } from '@/modules/session/backup';
import { Severity } from '@rotki/common';
import { getFilepath } from '@/modules/core/common/file/file';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useBackupApi } from '@/modules/session/api/use-backup-api';

interface UseDatabaseBackupsReturn {
  /** Every backup the last load reported, numbered for the table. */
  backups: ComputedRef<UserDbBackupWithId[]>;
  /** Writes a new backup, then reloads so the list shows it. */
  backup: () => Promise<void>;
  /**
   * Directory the backups live in, trailing separator included, or empty until the info loads.
   *
   * @remarks
   * Derived from the database's own path rather than configured, so it follows a user who moved
   * their data directory. Handles both separators, the backend reporting whichever its platform
   * uses.
   */
  directory: ComputedRef<string>;
  /** Reads the backup list from the backend, reporting a failure as a notification. */
  loadInfo: () => Promise<void>;
  /** True while the list is being read. */
  loading: Readonly<Ref<boolean>>;
  /** The rows the user ticked; bound with `v-model:selected`. */
  modelSelected: Ref<UserDbBackupWithId[]>;
  /** Deletes one backup and drops it from the list and the selection. */
  remove: (db: UserDbBackup) => Promise<void>;
  /** True while a new backup is being written. */
  saving: Readonly<Ref<boolean>>;
  /** Opens the confirmation for deleting every selected backup; deletes only once accepted. */
  showMassDeleteConfirmation: () => void;
}

function isSameEntry(firstDb: UserDbBackup, secondDb: UserDbBackup): boolean {
  return firstDb.version === secondDb.version && firstDb.time === secondDb.time && firstDb.size === secondDb.size;
}

/**
 * Drives the user-database backup list: reading it, writing a new one, and deleting the ones the
 * user picked.
 *
 * @remarks
 * Deleting a backup removes a file that nothing else recreates, so a mass delete goes through a
 * confirmation. A delete that the backend rejects leaves the list untouched, so the row the user
 * still has on disk is still on screen.
 *
 * @returns the list's bindings; `remove` and the accepted mass delete are the only destructive ones
 */
export function useDatabaseBackups(): UseDatabaseBackupsReturn {
  const backupInfo = ref<DatabaseInfo>();
  const modelSelected = ref<UserDbBackupWithId[]>([]);
  const loading = shallowRef<boolean>(false);
  const saving = shallowRef<boolean>(false);

  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationDispatcher();
  const { createBackup, deleteBackup, info } = useBackupApi();
  const { show } = useConfirmStore();

  const backups = computed<UserDbBackupWithId[]>(
    () => get(backupInfo)?.userdb?.backups.map((x, index) => ({ ...x, id: index + 1 })) ?? [],
  );

  const directory = computed<string>(() => {
    const currentInfo = get(backupInfo);
    if (!currentInfo)
      return '';

    const { filepath } = currentInfo.userdb.info;

    let index = filepath.lastIndexOf('/');
    if (index === -1)
      index = filepath.lastIndexOf('\\');

    return filepath.slice(0, index + 1);
  });

  function forget(removed: UserDbBackup[]): void {
    const current = get(backupInfo);
    if (!current)
      return;

    const next: DatabaseInfo = { ...current };
    removed.forEach((db) => {
      const index = next.userdb.backups.findIndex(backup => isSameEntry(backup, db));
      if (index !== -1)
        next.userdb.backups.splice(index, 1);
    });
    set(backupInfo, next);
  }

  async function loadInfo(): Promise<void> {
    try {
      set(loading, true);
      set(backupInfo, await info());
    }
    catch (error: unknown) {
      logger.error(error);
      notify({
        display: true,
        message: t('database_backups.load_error.message', { message: getErrorMessage(error) }),
        title: t('database_backups.load_error.title'),
      });
    }
    finally {
      set(loading, false);
    }
  }

  async function massRemove(): Promise<void> {
    const currentSelection = get(modelSelected);
    const filepaths = currentSelection.map(db => getFilepath(db, get(directory)));
    try {
      await deleteBackup(filepaths);
      forget(currentSelection);
      set(modelSelected, []);
    }
    catch (error: unknown) {
      logger.error(error);
      notify({
        display: true,
        message: t('database_backups.delete_error.mass_message', { message: getErrorMessage(error) }),
        title: t('database_backups.delete_error.title'),
      });
    }
  }

  async function remove(db: UserDbBackup): Promise<void> {
    const filepath = getFilepath(db, get(directory));
    try {
      await deleteBackup([filepath]);
      forget([db]);
      set(modelSelected, get(modelSelected).filter(item => !isSameEntry(item, db)));
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

  async function backup(): Promise<void> {
    try {
      set(saving, true);
      const filepath = await createBackup();
      notify({
        display: true,
        message: t('database_backups.backup.message', { filepath }),
        severity: Severity.INFO,
        title: t('database_backups.backup.title'),
      });

      await loadInfo();
    }
    catch (error: unknown) {
      logger.error(error);
      notify({
        display: true,
        message: t('database_backups.backup_error.message', { message: getErrorMessage(error) }),
        title: t('database_backups.backup_error.title'),
      });
    }
    finally {
      set(saving, false);
    }
  }

  function showMassDeleteConfirmation(): void {
    show(
      {
        message: t('database_backups.confirm.mass_message', { length: get(modelSelected).length }),
        title: t('database_backups.confirm.title'),
      },
      massRemove,
    );
  }

  onMounted(loadInfo);

  return {
    backup,
    backups,
    directory,
    loadInfo,
    loading: readonly(loading),
    modelSelected,
    remove,
    saving: readonly(saving),
    showMassDeleteConfirmation,
  };
}
