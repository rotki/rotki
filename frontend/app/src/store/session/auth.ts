import { type SyncConflict } from '@/store/session/types';
import { type LoginStatusData } from '@/types/websocket-messages';

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
  const loginStatus = ref<LoginStatusData | null>(null);

  const resetSyncConflict = (): void => {
    set(syncConflict, defaultSyncConflict());
  };

  const handleLoginStatus = (data: LoginStatusData): void => {
    if (!get(logged)) {
      updateLoginStatus(data);
    }
  };

  const updateLoginStatus = (status: LoginStatusData | null = null): void => {
    set(loginStatus, status);
  };

  return {
    logged,
    loginStatus,
    shouldFetchData,
    username,
    premiumPrompt,
    syncConflict,
    resetSyncConflict,
    handleLoginStatus,
    updateLoginStatus
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSessionAuthStore, import.meta.hot));
}
