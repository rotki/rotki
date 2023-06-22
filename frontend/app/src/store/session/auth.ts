import {
  type DataMigrationStatusData,
  type DbUpgradeStatusData
} from '@/types/websocket-messages';
import {
  type IncompleteUpgradeConflict,
  type SyncConflict
} from '@/types/login';

export const useSessionAuthStore = defineStore('session/auth', () => {
  const logged: Ref<boolean> = ref(false);
  const canRequestData: Ref<boolean> = ref(false);
  const shouldFetchData: Ref<boolean> = ref(false);
  const username: Ref<string> = ref('');
  const syncConflict: Ref<SyncConflict | undefined> = ref();
  const incompleteUpgradeConflict: Ref<IncompleteUpgradeConflict | undefined> =
    ref();
  const dbUpgradeStatus: Ref<DbUpgradeStatusData | null> = ref(null);
  const dataMigrationStatus: Ref<DataMigrationStatusData | null> = ref(null);

  const upgradeVisible: ComputedRef<boolean> = logicOr(
    dbUpgradeStatus,
    dataMigrationStatus
  );

  const resetSyncConflict = (): void => {
    set(syncConflict, undefined);
  };

  const resetIncompleteUpgradeConflict = (): void => {
    set(incompleteUpgradeConflict, undefined);
  };

  const updateDbUpgradeStatus = (status: DbUpgradeStatusData): void => {
    set(dbUpgradeStatus, status);
  };

  const updateDataMigrationStatus = (status: DataMigrationStatusData): void => {
    set(dataMigrationStatus, status);
  };

  const clearUpgradeMessages = (): void => {
    set(dataMigrationStatus, null);
    set(dbUpgradeStatus, null);
  };

  const conflictExist: ComputedRef<boolean> = computed(
    () => !!(get(syncConflict) || get(incompleteUpgradeConflict))
  );

  return {
    logged,
    dbUpgradeStatus,
    dataMigrationStatus,
    shouldFetchData,
    canRequestData,
    username,
    syncConflict,
    incompleteUpgradeConflict,
    conflictExist,
    upgradeVisible,
    resetSyncConflict,
    resetIncompleteUpgradeConflict,
    updateDbUpgradeStatus,
    updateDataMigrationStatus,
    clearUpgradeMessages
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSessionAuthStore, import.meta.hot));
}
