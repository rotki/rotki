import dayjs from 'dayjs';
import { logger } from '@/modules/core/common/logging/logging';
import { useSessionApi } from '@/modules/session/api/use-session-api';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useSetting } from '@/modules/settings/use-setting';

const SECONDS_PER_HOUR = 60 * 60;

interface UseSnapshotScheduleReturn {
  isSnapshotDue: () => Promise<boolean>;
}

/**
 * Whether the backend's balance snapshot schedule is due, mirroring
 * `DBHandler.should_save_balances`: `now - lastBalanceSave > balanceSaveFrequency`, strict.
 *
 * The backend stays the authority; this only avoids an aggregate query it would decline to save.
 *
 * `lastBalanceSave` is written by the `/periodic` poll alone, and that poll races the login load,
 * so an unknown value is settled here rather than read as 0 (which every period clears, making the
 * check always answer "due"). `GET /settings` cannot serve as the seed: its `last_balance_save`
 * is a different field that nothing updates and reads 0 with snapshots present. A failed read
 * still errs towards due, since an extra cached read costs less than a missed snapshot.
 */
export function useSnapshotSchedule(): UseSnapshotScheduleReturn {
  const { lastBalanceSave } = storeToRefs(useSessionMetadataStore());
  const balanceSaveFrequency = useSetting('balanceSaveFrequency');
  const { fetchPeriodicData } = useSessionApi();

  const settleLastBalanceSave = async (): Promise<void> => {
    try {
      set(lastBalanceSave, (await fetchPeriodicData()).lastBalanceSave);
    }
    catch (error: unknown) {
      logger.warn('[snapshot-schedule] could not read the last snapshot time', error);
    }
  };

  const isSnapshotDue = async (): Promise<boolean> => {
    if (get(lastBalanceSave) === 0)
      await settleLastBalanceSave();

    return dayjs().unix() - get(lastBalanceSave) > get(balanceSaveFrequency) * SECONDS_PER_HOUR;
  };

  return {
    isSnapshotDue,
  };
}
