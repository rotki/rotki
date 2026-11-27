import type { IncompleteUpgradeConflict, SyncConflict } from '@/modules/auth/login';
import type { DataMigrationStatusData, DbUpgradeStatusData } from '@/modules/core/messaging/types';
import { logicOr } from '@vueuse/math';
import { get, set } from '@vueuse/shared';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { computed, type ComputedRef, ref } from 'vue';

/** When each version of a DB upgrade or data migration run was first reported, keyed by version. */
type VersionTimes = Record<number, number>;

export const useSessionAuthStore = defineStore('session/auth', () => {
  const logged = ref<boolean>(false);
  const canRequestData = ref<boolean>(false);
  const shouldFetchData = ref<boolean>(false);
  const username = ref<string>('');
  const syncConflict = ref<SyncConflict | undefined>();
  const incompleteUpgradeConflict = ref<IncompleteUpgradeConflict | undefined>();
  const dbUpgradeStatus = ref<DbUpgradeStatusData | null>(null);
  const dataMigrationStatus = ref<DataMigrationStatusData | null>(null);
  const needsPasswordConfirmation = ref<boolean>(false);
  /**
   * The profile an unlock is opening, known before `username`, which is only set once the session
   * has loaded. The upgrade screen names it while that profile's database is migrated.
   */
  const unlockingProfile = ref<string>('');
  const dbUpgradeVersionTimes = ref<VersionTimes>({});
  const dataMigrationVersionTimes = ref<VersionTimes>({});
  /** When the first upgrade or migration message of this unlock arrived: the earliest version start. */
  const upgradeStartedAt = computed<number | null>(() => {
    const starts = [...Object.values(get(dbUpgradeVersionTimes)), ...Object.values(get(dataMigrationVersionTimes))];
    return starts.length > 0 ? Math.min(...starts) : null;
  });
  /** The error an unlock failed with while an upgrade or migration was running, kept for the failure screen. */
  const upgradeFailure = ref<string | null>(null);

  const upgradeVisible: ComputedRef<boolean> = logicOr(dbUpgradeStatus, dataMigrationStatus);

  const resetSyncConflict = (): void => {
    set(syncConflict, undefined);
  };

  const resetIncompleteUpgradeConflict = (): void => {
    set(incompleteUpgradeConflict, undefined);
  };

  function markStarted(times: VersionTimes, version: number): VersionTimes {
    if (times[version] !== undefined)
      return times;
    return { ...times, [version]: Date.now() };
  }

  const updateDbUpgradeStatus = (status: DbUpgradeStatusData): void => {
    set(dbUpgradeVersionTimes, markStarted(get(dbUpgradeVersionTimes), status.currentUpgrade.toVersion));
    set(dbUpgradeStatus, status);
  };

  const updateDataMigrationStatus = (status: DataMigrationStatusData): void => {
    set(dataMigrationVersionTimes, markStarted(get(dataMigrationVersionTimes), status.currentMigration.version));
    set(dataMigrationStatus, status);
  };

  const setUnlockingProfile = (profile: string): void => {
    set(unlockingProfile, profile);
  };

  /**
   * Records that the unlock failed while an upgrade was running, keeping the progress it reached on
   * screen for the failure state.
   *
   * @returns whether an upgrade was running, so the caller knows the failure belongs to it
   */
  const failUpgrade = (message: string): boolean => {
    if (!get(upgradeVisible))
      return false;
    set(upgradeFailure, message);
    return true;
  };

  const clearUpgradeMessages = (): void => {
    set(dataMigrationStatus, null);
    set(dbUpgradeStatus, null);
    set(dbUpgradeVersionTimes, {});
    set(dataMigrationVersionTimes, {});
    set(upgradeFailure, null);
  };

  const conflictExist = computed<boolean>(() => !!(get(syncConflict) ?? get(incompleteUpgradeConflict)));

  return {
    canRequestData,
    clearUpgradeMessages,
    conflictExist,
    dataMigrationStatus,
    dataMigrationVersionTimes,
    dbUpgradeStatus,
    dbUpgradeVersionTimes,
    failUpgrade,
    incompleteUpgradeConflict,
    logged,
    needsPasswordConfirmation,
    resetIncompleteUpgradeConflict,
    resetSyncConflict,
    setUnlockingProfile,
    shouldFetchData,
    syncConflict,
    unlockingProfile,
    updateDataMigrationStatus,
    updateDbUpgradeStatus,
    upgradeFailure,
    upgradeStartedAt,
    upgradeVisible,
    username,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSessionAuthStore, import.meta.hot));
