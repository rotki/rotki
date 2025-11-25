import type { DataMigrationStatusData, DbUpgradeStatusData } from '@/modules/messaging/types';
import type { IncompleteUpgradeConflict, SyncConflict } from '@/types/login';

export const useSessionAuthStore = defineStore('session/auth', () => {
  const logged = ref<boolean>(false);
  const canRequestData = ref<boolean>(false);
  const shouldFetchData = ref<boolean>(false);
  const username = ref<string>('');
  const syncConflict = ref<SyncConflict | undefined>();
  const incompleteUpgradeConflict = ref<IncompleteUpgradeConflict | undefined>();
  const dbUpgradeStatus = ref<DbUpgradeStatusData | null>(null);
  const dataMigrationStatus = ref<DataMigrationStatusData | null>(null);
  const checkForAssetUpdate = ref<boolean>(false);
  const needsPasswordConfirmation = ref<boolean>(false);

  const upgradeVisible: ComputedRef<boolean> = logicOr(dbUpgradeStatus, dataMigrationStatus);

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

  const conflictExist = computed<boolean>(() => !!(get(syncConflict) || get(incompleteUpgradeConflict)));

  return {
    canRequestData,
    checkForAssetUpdate,
    clearUpgradeMessages,
    conflictExist,
    dataMigrationStatus,
    dbUpgradeStatus,
    incompleteUpgradeConflict,
    logged,
    needsPasswordConfirmation,
    resetIncompleteUpgradeConflict,
    resetSyncConflict,
    shouldFetchData,
    syncConflict,
    updateDataMigrationStatus,
    updateDbUpgradeStatus,
    upgradeVisible,
    username,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSessionAuthStore, import.meta.hot));
