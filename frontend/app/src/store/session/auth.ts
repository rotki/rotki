import { SyncConflict } from '@/store/session/types';

const defaultSyncConflict = (): SyncConflict => ({
  message: '',
  payload: null
});

export const useSessionAuthStore = defineStore('session/auth', () => {
  const logged = ref(false);
  const premiumPrompt = ref(false);
  const username = ref('');
  const syncConflict = ref<SyncConflict>(defaultSyncConflict());

  const resetSyncConflict = () => {
    set(syncConflict, defaultSyncConflict());
  };

  return {
    logged,
    username,
    premiumPrompt,
    syncConflict,
    resetSyncConflict
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSessionAuthStore, import.meta.hot));
}
