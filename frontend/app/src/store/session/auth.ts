import { type ComputedRef, type Ref } from 'vue';
import { type SyncConflict } from '@/store/session/types';
import {
  type DataMigrationStatusData,
  type DbUpgradeStatusData
} from '@/types/websocket-messages';

const defaultSyncConflict = (): SyncConflict => ({
  message: '',
  payload: null
});

export const useSessionAuthStore = defineStore('session/auth', () => {
  const logged: Ref<boolean> = ref(false);
  const canRequestData: Ref<boolean> = ref(false);
  const shouldFetchData: Ref<boolean> = ref(false);
  const premiumPrompt: Ref<boolean> = ref(false);
  const username: Ref<string> = ref('');
  const syncConflict: Ref<SyncConflict> = ref(defaultSyncConflict());
  const dbUpgradeStatus: Ref<DbUpgradeStatusData | null> = ref(null);
  const dataMigrationStatus: Ref<DataMigrationStatusData | null> = ref(null);

  const upgradeVisible: ComputedRef<boolean> = logicOr(
    dbUpgradeStatus,
    dataMigrationStatus
  );

  const resetSyncConflict = (): void => {
    set(syncConflict, defaultSyncConflict());
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

  return {
    logged,
    dbUpgradeStatus,
    dataMigrationStatus,
    shouldFetchData,
    canRequestData,
    username,
    premiumPrompt,
    syncConflict,
    upgradeVisible,
    resetSyncConflict,
    updateDbUpgradeStatus,
    updateDataMigrationStatus,
    clearUpgradeMessages
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSessionAuthStore, import.meta.hot));
}
