import type { DatabaseInfo, UserDbBackup } from '@/modules/session/backup';
import { neverSettles } from '@test/utils/never-settles';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import { useDatabaseBackups } from './use-database-backups';

const { createBackup, deleteBackup, info, notify, show } = await vi.hoisted(async () => ({
  createBackup: vi.fn(),
  deleteBackup: vi.fn(),
  info: vi.fn(),
  notify: vi.fn(),
  show: vi.fn(),
}));

vi.mock('@/modules/session/api/use-backup-api', () => ({
  useBackupApi: (): Record<string, unknown> => ({ createBackup, deleteBackup, info }),
}));

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: (): Record<string, unknown> => ({ notify }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): Record<string, unknown> => ({ show }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  getDefaultLogLevel: vi.fn(() => 'debug'),
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
  setLevel: vi.fn(),
}));

const wrappers: VueWrapper[] = [];

function entry(time: number, version = 40, size = 100): UserDbBackup {
  return { size, time, version };
}

function databaseInfo(backups: UserDbBackup[], filepath = '/home/user/.rotki/data/rotkehlchen.db'): DatabaseInfo {
  return {
    globaldb: { globaldbAssetsVersion: 1, globaldbSchemaVersion: 1 },
    userdb: { backups, info: { filepath, size: 1000, version: 40 } },
  };
}

async function mountBackups(): Promise<ReturnType<typeof useDatabaseBackups>> {
  let captured: ReturnType<typeof useDatabaseBackups> | undefined;
  let setupError: Error | undefined;
  const Host = defineComponent({
    setup(): () => ReturnType<typeof h> {
      try {
        captured = useDatabaseBackups();
      }
      catch (error) {
        setupError = error instanceof Error ? error : new Error(String(error));
      }
      return (): ReturnType<typeof h> => h('div');
    },
  });

  wrappers.push(mount(Host));
  await flushPromises();
  if (setupError)
    throw setupError;
  return captured!;
}

describe('modules/settings/data-security/backups/useDatabaseBackups', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    info.mockResolvedValue(databaseInfo([]));
    deleteBackup.mockResolvedValue(true);
    createBackup.mockResolvedValue('/home/user/.rotki/data/1700000000_rotkehlchen_db_v40.backup');
  });

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
  });

  describe('loading the list', () => {
    it('should read the backups as soon as it mounts', async () => {
      info.mockResolvedValue(databaseInfo([entry(1700000000)]));

      const { backups } = await mountBackups();

      expect(info).toHaveBeenCalledOnce();
      expect(get(backups)).toHaveLength(1);
    });

    it('should number the rows from one so the table can key them', async () => {
      info.mockResolvedValue(databaseInfo([entry(1700000000), entry(1700000001)]));

      const { backups } = await mountBackups();

      expect(get(backups).map(item => item.id)).toEqual([1, 2]);
    });

    it('should report an empty list rather than failing when nothing has been backed up', async () => {
      const { backups } = await mountBackups();

      expect(get(backups)).toEqual([]);
    });

    it('should notify and leave the list empty when the read fails', async () => {
      info.mockRejectedValue(new Error('offline'));

      const { backups, loading } = await mountBackups();

      expect(notify).toHaveBeenCalledOnce();
      expect(get(backups)).toEqual([]);
      expect(get(loading)).toBe(false);
    });
  });

  describe('where the backups live', () => {
    it('should take the directory from the database path', async () => {
      const { directory } = await mountBackups();

      expect(get(directory)).toBe('/home/user/.rotki/data/');
    });

    it('should handle a windows path, which the backend reports with backslashes', async () => {
      info.mockResolvedValue(databaseInfo([], 'C:\\Users\\user\\rotki\\data\\rotkehlchen.db'));

      const { directory } = await mountBackups();

      expect(get(directory)).toBe('C:\\Users\\user\\rotki\\data\\');
    });

    it('should be empty until the info has loaded', async () => {
      info.mockReturnValue(neverSettles());

      let captured: ReturnType<typeof useDatabaseBackups> | undefined;
      const Host = defineComponent({
        setup(): () => ReturnType<typeof h> {
          captured = useDatabaseBackups();
          return (): ReturnType<typeof h> => h('div');
        },
      });
      wrappers.push(mount(Host));

      expect(get(captured!.directory)).toBe('');
    });
  });

  describe('deleting one backup', () => {
    it('should delete the file that row names, and only that one', async () => {
      info.mockResolvedValue(databaseInfo([entry(1700000000), entry(1700000001)]));
      const { remove } = await mountBackups();

      await remove(entry(1700000000));

      expect(deleteBackup).toHaveBeenCalledExactlyOnceWith([
        '/home/user/.rotki/data/1700000000_rotkehlchen_db_v40.backup',
      ]);
    });

    it('should drop the row from the list once the backend accepted', async () => {
      info.mockResolvedValue(databaseInfo([entry(1700000000), entry(1700000001)]));
      const { backups, remove } = await mountBackups();

      await remove(entry(1700000000));

      expect(get(backups).map(item => item.time)).toEqual([1700000001]);
    });

    it('should drop it from the selection too, so a later mass delete cannot resend it', async () => {
      info.mockResolvedValue(databaseInfo([entry(1700000000), entry(1700000001)]));
      const { modelSelected, remove } = await mountBackups();
      set(modelSelected, [{ ...entry(1700000000), id: 1 }, { ...entry(1700000001), id: 2 }]);

      await remove(entry(1700000000));

      expect(get(modelSelected).map(item => item.time)).toEqual([1700000001]);
    });

    it('should still delete the file when nothing has loaded yet', async () => {
      info.mockReturnValue(neverSettles());
      let captured: ReturnType<typeof useDatabaseBackups> | undefined;
      const Host = defineComponent({
        setup(): () => ReturnType<typeof h> {
          captured = useDatabaseBackups();
          return (): ReturnType<typeof h> => h('div');
        },
      });
      wrappers.push(mount(Host));

      await captured!.remove(entry(1700000000));

      expect(deleteBackup).toHaveBeenCalledOnce();
      expect(get(captured!.backups)).toEqual([]);
    });

    it('should leave the other rows alone when the deleted one is not in the list', async () => {
      info.mockResolvedValue(databaseInfo([entry(1700000000), entry(1700000001)]));
      const { backups, remove } = await mountBackups();

      await remove(entry(1799999999));

      expect(get(backups).map(item => item.time)).toEqual([1700000000, 1700000001]);
    });

    it('should keep the row when the backend refused, since the file is still there', async () => {
      info.mockResolvedValue(databaseInfo([entry(1700000000)]));
      deleteBackup.mockRejectedValue(new Error('permission denied'));
      const { backups, remove } = await mountBackups();

      await remove(entry(1700000000));

      expect(notify).toHaveBeenCalledOnce();
      expect(get(backups)).toHaveLength(1);
    });
  });

  describe('deleting the selected backups', () => {
    it('should delete nothing until the user accepts the confirmation', async () => {
      info.mockResolvedValue(databaseInfo([entry(1700000000)]));
      const { modelSelected, showMassDeleteConfirmation } = await mountBackups();
      set(modelSelected, [{ ...entry(1700000000), id: 1 }]);

      showMassDeleteConfirmation();

      expect(show).toHaveBeenCalledOnce();
      expect(deleteBackup).not.toHaveBeenCalled();
    });

    it('should delete every selected file in one call once accepted', async () => {
      info.mockResolvedValue(databaseInfo([entry(1700000000), entry(1700000001)]));
      const { modelSelected, showMassDeleteConfirmation } = await mountBackups();
      set(modelSelected, [{ ...entry(1700000000), id: 1 }, { ...entry(1700000001), id: 2 }]);

      showMassDeleteConfirmation();
      await show.mock.calls[0][1]();

      expect(deleteBackup).toHaveBeenCalledExactlyOnceWith([
        '/home/user/.rotki/data/1700000000_rotkehlchen_db_v40.backup',
        '/home/user/.rotki/data/1700000001_rotkehlchen_db_v40.backup',
      ]);
    });

    it('should drop the deleted rows and clear the selection', async () => {
      info.mockResolvedValue(databaseInfo([entry(1700000000), entry(1700000001), entry(1700000002)]));
      const { backups, modelSelected, showMassDeleteConfirmation } = await mountBackups();
      set(modelSelected, [{ ...entry(1700000000), id: 1 }, { ...entry(1700000002), id: 3 }]);

      showMassDeleteConfirmation();
      await show.mock.calls[0][1]();

      expect(get(backups).map(item => item.time)).toEqual([1700000001]);
      expect(get(modelSelected)).toEqual([]);
    });

    it('should keep the selection when the backend refused, so the user can retry', async () => {
      info.mockResolvedValue(databaseInfo([entry(1700000000)]));
      deleteBackup.mockRejectedValue(new Error('permission denied'));
      const { backups, modelSelected, showMassDeleteConfirmation } = await mountBackups();
      set(modelSelected, [{ ...entry(1700000000), id: 1 }]);

      showMassDeleteConfirmation();
      await show.mock.calls[0][1]();

      expect(notify).toHaveBeenCalledOnce();
      expect(get(modelSelected)).toHaveLength(1);
      expect(get(backups)).toHaveLength(1);
    });

    it('should tell the user how many are about to go', async () => {
      const { modelSelected, showMassDeleteConfirmation } = await mountBackups();
      set(modelSelected, [{ ...entry(1700000000), id: 1 }, { ...entry(1700000001), id: 2 }]);

      showMassDeleteConfirmation();

      expect(show.mock.calls[0][0].message).toContain('2');
    });
  });

  describe('writing a new backup', () => {
    it('should reload the list so the new backup appears', async () => {
      await mountBackups();
      info.mockClear();
      const { backup } = await mountBackups();

      await backup();

      expect(createBackup).toHaveBeenCalledOnce();
      expect(info).toHaveBeenCalled();
    });

    it('should name the file it wrote', async () => {
      const { backup } = await mountBackups();

      await backup();

      expect(notify).toHaveBeenCalledOnce();
      expect(notify.mock.calls[0][0].message).toContain('1700000000_rotkehlchen_db_v40.backup');
    });

    it('should notify and not reload when the write failed', async () => {
      createBackup.mockRejectedValue(new Error('disk full'));
      const { backup, saving } = await mountBackups();
      info.mockClear();

      await backup();

      expect(notify).toHaveBeenCalledOnce();
      expect(info).not.toHaveBeenCalled();
      expect(get(saving)).toBe(false);
    });
  });
});
