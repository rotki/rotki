import type { ComputedRef, Ref } from 'vue';
import type { MoneriumOAuthResult, MoneriumStatus } from './types';
import { logger } from '@/utils/logging';
import { useMoneriumOAuthApi } from './use-monerium-api';

interface UseMoneriumOAuthReturn {
  authenticated: ComputedRef<boolean>;
  completeOAuth: (
    accessToken: string,
    refreshToken: string,
    expiresIn?: number,
  ) => Promise<MoneriumOAuthResult>;
  disconnect: () => Promise<void>;
  loading: Ref<boolean>;
  refreshStatus: () => Promise<void>;
  setStatus: (newStatus: MoneriumStatus) => void;
  status: Ref<MoneriumStatus | undefined>;
}

export function useMoneriumOAuth(): UseMoneriumOAuthReturn {
  const status = ref<MoneriumStatus>();
  const loading = ref<boolean>(false);
  const api = useMoneriumOAuthApi();

  const authenticated = computed<boolean>(() => !!get(status)?.authenticated);

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

  async function completeOAuth(
    accessToken: string,
    refreshToken: string,
    expiresIn: number = 3600,
  ): Promise<MoneriumOAuthResult> {
    try {
      const result = await api.completeOAuth(accessToken, refreshToken, expiresIn);

      setStatus({
        authenticated: true,
        defaultProfileId: result.defaultProfileId,
        profiles: result.profiles,
        userEmail: result.userEmail,
      });

      await refreshStatus();

      return {
        defaultProfileId: result.defaultProfileId,
        message: result.message,
        profiles: result.profiles,
        userEmail: result.userEmail,
      };
    }
    catch (error) {
      logger.error('Failed to complete Monerium OAuth', error);
      throw error;
    }
  }

  async function disconnect(): Promise<void> {
    try {
      await api.disconnect();
      setStatus({ authenticated: false });
      await refreshStatus();
    }
    catch (error) {
      logger.error('Failed to disconnect Monerium', error);
      throw error;
    }
  }

  return {
    authenticated,
    completeOAuth,
    disconnect,
    loading,
    refreshStatus,
    setStatus,
    status,
  };
}
