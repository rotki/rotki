import { get, set } from '@vueuse/core';
import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { type MoneriumStatus, useMoneriumOAuthApi } from '@/composables/api/settings/monerium-oauth';
import { logger } from '@/utils/logging';

export const useMoneriumOAuthStore = defineStore('moneriumOAuth', () => {
  const status = ref<MoneriumStatus>();
  const loading = ref(false);
  const api = useMoneriumOAuthApi();

  const authenticated = computed(() => !!get(status)?.authenticated);

  async function refreshStatus(): Promise<void> {
    set(loading, true);
    try {
      const result = await api.getStatus();
      set(status, result);
    }
    catch (error) {
      logger.error('Failed to fetch Monerium status', error);
      set(status, { authenticated: false });
    }
    finally {
      set(loading, false);
    }
  }

  function setStatus(newStatus: MoneriumStatus): void {
    set(status, newStatus);
  }

  return {
    authenticated,
    loading,
    refreshStatus,
    setStatus,
    status,
  };
});
