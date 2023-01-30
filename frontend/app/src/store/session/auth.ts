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
  const logged = ref(false);
  const shouldFetchData = ref(false);
  const premiumPrompt = ref(false);
  const username = ref('');
  const syncConflict = ref<SyncConflict>(defaultSyncConflict());
  const dbUpgradeStatus = ref<DbUpgradeStatusData | null>(null);
  const dataMigrationStatus = ref<DataMigrationStatusData | null>(null);

  const resetSyncConflict = (): void => {
    set(syncConflict, defaultSyncConflict());
  };

  const handleDbUpgradeStatus = (data: DbUpgradeStatusData): void => {
    if (!get(logged)) {
      updateDbUpgradeStatus(data);
    }
  };

  const updateDbUpgradeStatus = (
    status: DbUpgradeStatusData | null = null
  ): void => {
    set(dbUpgradeStatus, status);
  };

  const handleDataMigrationStatus = (
    data: DataMigrationStatusData | null = null
  ): void => {
    if (!get(logged)) {
      updateDataMigrationStatus(data);
    }
  };

  const updateDataMigrationStatus = (
    status: DataMigrationStatusData | null = null
  ): void => {
    set(dataMigrationStatus, status);
  };

  return {
    logged,
    dbUpgradeStatus,
    dataMigrationStatus,
    shouldFetchData,
    username,
    premiumPrompt,
    syncConflict,
    resetSyncConflict,
    handleDbUpgradeStatus,
    updateDbUpgradeStatus,
    handleDataMigrationStatus,
    updateDataMigrationStatus
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSessionAuthStore, import.meta.hot));
}
