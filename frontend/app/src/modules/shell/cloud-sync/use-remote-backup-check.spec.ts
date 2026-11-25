import { createPinia, setActivePinia, storeToRefs } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useRemoteBackupCheck } from '@/modules/shell/cloud-sync/use-remote-backup-check';

const { fetchRemoteBackup } = vi.hoisted(() => ({
  fetchRemoteBackup: vi.fn(),
}));

vi.mock('@/modules/session/api/use-sync-api', () => ({
  useSyncApi: (): Record<string, unknown> => ({ fetchRemoteBackup }),
}));

const HOUR = 3_600_000;

describe('modules/shell/cloud-sync/use-remote-backup-check', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.useFakeTimers({ now: 10 * HOUR, toFake: ['Date'] });
    fetchRemoteBackup.mockResolvedValue({ dataHash: 'abc', dataSize: 1, lastModifyTs: 1760882400, uploadTs: 1760882460 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should ask the server when no backup is known and take its answer', async () => {
    const { lastDataUpload } = storeToRefs(useSessionMetadataStore());
    const { checkIfUnknown } = useRemoteBackupCheck();

    await checkIfUnknown();

    expect(fetchRemoteBackup).toHaveBeenCalledOnce();
    expect(get(lastDataUpload)).toBe(1760882460);
  });

  it('should not ask when a backup is known', async () => {
    const { lastDataUpload } = storeToRefs(useSessionMetadataStore());
    set(lastDataUpload, 1760882460);
    const { checkIfUnknown } = useRemoteBackupCheck();

    await checkIfUnknown();

    expect(fetchRemoteBackup).not.toHaveBeenCalled();
  });

  it('should ask at most once an hour while the server has no backup', async () => {
    fetchRemoteBackup.mockResolvedValue(null);
    const { lastDataUpload } = storeToRefs(useSessionMetadataStore());
    const { checkIfUnknown } = useRemoteBackupCheck();

    await checkIfUnknown();
    vi.setSystemTime(10 * HOUR + HOUR - 1);
    await checkIfUnknown();

    expect(fetchRemoteBackup).toHaveBeenCalledOnce();
    expect(get(lastDataUpload)).toBe(0);

    vi.setSystemTime(10 * HOUR + HOUR);
    await checkIfUnknown();

    expect(fetchRemoteBackup).toHaveBeenCalledTimes(2);
  });

  it('should ask again on the next opening after a failed check, which learned nothing', async () => {
    fetchRemoteBackup.mockRejectedValueOnce(new Error('unreachable'));
    const { lastDataUpload } = storeToRefs(useSessionMetadataStore());
    const { checkFailed, checking, checkIfUnknown } = useRemoteBackupCheck();

    await checkIfUnknown();

    expect(get(checkFailed)).toBe(true);
    expect(get(checking)).toBe(false);
    expect(get(lastDataUpload)).toBe(0);

    await checkIfUnknown();

    expect(fetchRemoteBackup).toHaveBeenCalledTimes(2);
    expect(get(checkFailed)).toBe(false);
    expect(get(lastDataUpload)).toBe(1760882460);
  });

  it('should report checking while the server is asked', async () => {
    let resolve: (value: null) => void = () => {};
    fetchRemoteBackup.mockReturnValue(new Promise((r) => {
      resolve = r;
    }));
    const { checking, checkIfUnknown } = useRemoteBackupCheck();

    const pending = checkIfUnknown();
    expect(get(checking)).toBe(true);

    resolve(null);
    await pending;
    expect(get(checking)).toBe(false);
  });
});
