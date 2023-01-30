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
    canRequestData,
    username,
    premiumPrompt,
    syncConflict,
    upgradeVisible,
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
