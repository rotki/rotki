import type { RemoteBackup } from '@/modules/session/sync';
import { createPinia, setActivePinia, storeToRefs } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FailureCause } from '@/modules/core/api/failure-cause';
import { ApiRequestError } from '@/modules/core/api/types/errors';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { RemoteBackupDeletionPhase, useRemoteBackupDeletion } from '@/modules/shell/cloud-sync/use-remote-backup-deletion';

const { deleteRemoteBackup, fetchRemoteBackup } = vi.hoisted(() => ({
  deleteRemoteBackup: vi.fn(),
  fetchRemoteBackup: vi.fn(),
}));

vi.mock('@/modules/session/api/use-sync-api', () => ({
  useSyncApi: (): Record<string, unknown> => ({ deleteRemoteBackup, fetchRemoteBackup }),
}));

const BACKUP: RemoteBackup = { dataHash: 'abc', dataSize: 4242, lastModifyTs: 1760882400, uploadTs: 1760882460 };

const NEWER_BACKUP: RemoteBackup = { ...BACKUP, dataHash: 'def', uploadTs: 1760882999 };

describe('modules/shell/cloud-sync/use-remote-backup-deletion', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    fetchRemoteBackup.mockResolvedValue(BACKUP);
    deleteRemoteBackup.mockResolvedValue({ premiumShouldSync: false });
  });

  it('should show the server backup for review', async () => {
    const { backup, load, phase } = useRemoteBackupDeletion();
    await load();

    expect(get(phase)).toBe(RemoteBackupDeletionPhase.REVIEW);
    expect(get(backup)).toEqual(BACKUP);
  });

  it('should say there is nothing to delete when the server stores no backup', async () => {
    fetchRemoteBackup.mockResolvedValue(null);
    const { load, phase } = useRemoteBackupDeletion();
    await load();

    expect(get(phase)).toBe(RemoteBackupDeletionPhase.EMPTY);
  });

  it('should keep the reason when the server can not be asked', async () => {
    const error = new ApiRequestError('unreachable', { failureCause: FailureCause.NETWORK, status: 502 });
    fetchRemoteBackup.mockRejectedValue(error);
    const { failure, load, phase } = useRemoteBackupDeletion();
    await load();

    expect(get(phase)).toBe(RemoteBackupDeletionPhase.LOAD_FAILED);
    expect(get(failure)).toBe(error);
  });

  it('should delete the reviewed backup and turn automatic backup off', async () => {
    const { premiumSync } = storeToRefs(usePremiumStore());
    const { lastDataUpload } = storeToRefs(useSessionMetadataStore());
    set(premiumSync, true);
    set(lastDataUpload, 1760882460);

    const { load, phase, remove } = useRemoteBackupDeletion();
    await load();
    await remove(true);

    expect(deleteRemoteBackup).toHaveBeenCalledWith({ dataHash: 'abc', disableSync: true });
    expect(get(phase)).toBe(RemoteBackupDeletionPhase.DELETED);
    expect(get(premiumSync)).toBe(false);
    expect(get(lastDataUpload)).toBe(0);
  });

  it('should leave the choice about automatic backup to the backend', async () => {
    deleteRemoteBackup.mockResolvedValue({ premiumShouldSync: false });
    const { load, remove } = useRemoteBackupDeletion();
    await load();
    await remove(true);

    expect(deleteRemoteBackup).toHaveBeenCalledWith({ dataHash: 'abc', disableSync: true });
  });

  it('should keep automatic backup on when the user leaves it on', async () => {
    const { premiumSync } = storeToRefs(usePremiumStore());
    set(premiumSync, true);
    deleteRemoteBackup.mockResolvedValue({ premiumShouldSync: true });

    const { load, remove } = useRemoteBackupDeletion();
    await load();
    await remove(false);

    expect(deleteRemoteBackup).toHaveBeenCalledWith({ dataHash: 'abc', disableSync: false });
    expect(get(premiumSync)).toBe(true);
  });

  it('should show the newer backup for review when the server kept it', async () => {
    deleteRemoteBackup.mockRejectedValue(new ApiRequestError('changed', { failureCause: FailureCause.CONFLICT, status: 409 }));
    const { backup, backupChanged, load, phase, remove } = useRemoteBackupDeletion();
    await load();
    fetchRemoteBackup.mockResolvedValue(NEWER_BACKUP);
    await remove(true);

    expect(get(phase)).toBe(RemoteBackupDeletionPhase.REVIEW);
    expect(get(backup)).toEqual(NEWER_BACKUP);
    expect(get(backupChanged)).toBe(true);
  });

  it('should keep saying the backup changed when showing it again fails and is retried', async () => {
    deleteRemoteBackup.mockRejectedValue(new ApiRequestError('changed', { failureCause: FailureCause.CONFLICT, status: 409 }));
    const { backup, backupChanged, load, phase, remove } = useRemoteBackupDeletion();
    await load();
    fetchRemoteBackup.mockRejectedValue(new ApiRequestError('unreachable', { failureCause: FailureCause.NETWORK, status: 502 }));
    await remove(true);

    expect(get(phase)).toBe(RemoteBackupDeletionPhase.LOAD_FAILED);
    expect(get(backupChanged)).toBe(true);

    fetchRemoteBackup.mockResolvedValue(NEWER_BACKUP);
    await load();

    expect(get(phase)).toBe(RemoteBackupDeletionPhase.REVIEW);
    expect(get(backup)).toEqual(NEWER_BACKUP);
    expect(get(backupChanged)).toBe(true);
  });

  it('should keep the backup up for another try when the deletion fails', async () => {
    const error = new ApiRequestError('busy', { failureCause: FailureCause.RATE_LIMITED, status: 409 });
    deleteRemoteBackup.mockRejectedValue(error);
    const { backup, failure, load, phase, remove } = useRemoteBackupDeletion();
    await load();
    await remove(true);

    expect(get(phase)).toBe(RemoteBackupDeletionPhase.REVIEW);
    expect(get(backup)).toEqual(BACKUP);
    expect(get(failure)).toBe(error);
  });

  it('should not delete anything before a backup was reviewed', async () => {
    const { remove } = useRemoteBackupDeletion();
    await remove(true);

    expect(deleteRemoteBackup).not.toHaveBeenCalled();
  });
});
