import type { ComputedRef, Ref } from 'vue';
import type { MoneriumOAuthResult, MoneriumStatus } from './types';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { logger } from '@/modules/core/common/logging/logging';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';
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

export const useMoneriumOAuth = createSharedComposable((): UseMoneriumOAuthReturn => {
  const loading = ref<boolean>(false);
  const api = useMoneriumOAuthApi();

  const { logged } = storeToRefs(useSessionAuthStore());
  const { allowed } = useFeatureAccess(PremiumFeature.MONERIUM);

  const status: Ref<MoneriumStatus | undefined> = asyncComputed<MoneriumStatus | undefined>(
    async () => {
      if (get(logged) && get(allowed)) {
        try {
          return await api.getStatus();
        }
        catch (error) {
          logger.error('Failed to fetch Monerium status', error);
          return { authenticated: false };
        }
      }

      return undefined;
    },
    undefined,
    { evaluating: loading },
  );

  const authenticated = computed<boolean>(() => !!get(status)?.authenticated);

  async function refreshStatus(): Promise<void> {
    set(loading, true);
    try {
      set(status, await api.getStatus());
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

  /**
   * Takes down the expired-session row once the user has authenticated again.
   *
   * @remarks
   * Without this the condition outlives the session it was about, and a later deliberate disconnect
   * would bring back a row asking to re-authenticate. The store is resolved here rather than when the
   * shared composable is created, so the call reaches the pinia that is active now.
   */
  function clearSessionExpiredCondition(): void {
    useRaisedConditionsStore().clear(({ kind }) => kind === RaisedConditionKind.MONERIUM_SESSION);
  }

  async function completeOAuth(
    accessToken: string,
    refreshToken: string,
    expiresIn: number = 3600,
  ): Promise<MoneriumOAuthResult> {
    try {
      const result = await api.completeOAuth(accessToken, refreshToken, expiresIn);
      clearSessionExpiredCondition();

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
});
