import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, type Ref } from 'vue';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useSnapshotSchedule } from './use-snapshot-schedule';

const { frequency, useSetting, fetchPeriodicData } = vi.hoisted(() => {
  const frequency = { value: 24 };
  return { fetchPeriodicData: vi.fn(), frequency, useSetting: vi.fn() };
});

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: useSetting.mockImplementation((): Ref<number> => computed<number>(() => frequency.value)),
}));

vi.mock('@/modules/session/api/use-session-api', () => ({
  useSessionApi: (): { fetchPeriodicData: typeof fetchPeriodicData } => ({ fetchPeriodicData }),
}));

const NOW = new Date('2026-08-25T12:00:00Z');
const NOW_SECONDS = Math.floor(NOW.getTime() / 1000);
const HOUR = 60 * 60;

/** Pins the arithmetic to `DBHandler.should_save_balances`, so a drift between them fails here. */
describe('useSnapshotSchedule', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
    frequency.value = 24;
    useSetting.mockClear();
    fetchPeriodicData.mockReset();
    fetchPeriodicData.mockResolvedValue({ lastBalanceSave: NOW_SECONDS - 25 * HOUR });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const withLastSave = (secondsAgo: number): ReturnType<typeof useSnapshotSchedule> => {
    const { lastBalanceSave } = storeToRefs(useSessionMetadataStore());
    set(lastBalanceSave, NOW_SECONDS - secondsAgo);
    return useSnapshotSchedule();
  };

  it('should be due when the last snapshot is older than the frequency', async () => {
    const { isSnapshotDue } = withLastSave(25 * HOUR);

    await expect(isSnapshotDue()).resolves.toBe(true);
  });

  it('should not be due when the last snapshot is within the frequency', async () => {
    const { isSnapshotDue } = withLastSave(20 * HOUR);

    await expect(isSnapshotDue()).resolves.toBe(false);
  });

  /** The backend compares strictly, so `>=` here would query on every login and save nothing. */
  it('should not be due exactly on the boundary', async () => {
    const { isSnapshotDue } = withLastSave(24 * HOUR);

    await expect(isSnapshotDue()).resolves.toBe(false);
  });

  it('should follow the configured frequency, not a fixed day', async () => {
    frequency.value = 12;
    const { isSnapshotDue } = withLastSave(13 * HOUR);

    await expect(isSnapshotDue()).resolves.toBe(true);
  });

  it('should not re-read the snapshot time when it is already known', async () => {
    const { isSnapshotDue } = withLastSave(20 * HOUR);

    await isSnapshotDue();

    expect(fetchPeriodicData).not.toHaveBeenCalled();
  });

  describe('when the snapshot time is not known yet', () => {
    /**
     * 🔴 Only the `/periodic` poll writes `lastBalanceSave`, and it races the login load: measured
     * in the app, the poll landed *after* the aggregate query, so reading the unset 0 answered
     * "due" on a login minutes after a snapshot.
     */
    it('should read it rather than treat the unset value as due', async () => {
      fetchPeriodicData.mockResolvedValue({ lastBalanceSave: NOW_SECONDS - 20 * HOUR });
      const { isSnapshotDue } = useSnapshotSchedule();

      await expect(isSnapshotDue()).resolves.toBe(false);

      expect(fetchPeriodicData).toHaveBeenCalledOnce();
    });

    it('should be due when the read says the snapshot is old', async () => {
      const { isSnapshotDue } = useSnapshotSchedule();

      await expect(isSnapshotDue()).resolves.toBe(true);
    });

    it('should be due when the read fails', async () => {
      fetchPeriodicData.mockRejectedValue(new Error('backend is down'));
      const { isSnapshotDue } = useSnapshotSchedule();

      await expect(isSnapshotDue()).resolves.toBe(true);
    });

    it('should keep what it read for the next question', async () => {
      fetchPeriodicData.mockResolvedValue({ lastBalanceSave: NOW_SECONDS - 20 * HOUR });
      const { isSnapshotDue } = useSnapshotSchedule();

      await isSnapshotDue();
      await isSnapshotDue();

      expect(fetchPeriodicData).toHaveBeenCalledOnce();
    });
  });

  it('should read the balance save frequency setting', () => {
    useSnapshotSchedule();

    expect(useSetting).toHaveBeenCalledWith('balanceSaveFrequency');
  });
});
