import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { logger } from '@/modules/core/common/logging/logging';
import { usePremiumCredentialsApi } from '@/modules/premium/use-premium-credentials-api';
import { usePremiumStore } from '@/modules/premium/use-premium-store';

interface UsePremiumWatchersReturn {
  fetchCapabilities: () => Promise<void>;
}

export function usePremiumWatchers(): UsePremiumWatchersReturn {
  const api = usePremiumCredentialsApi();
  const { capabilities } = storeToRefs(usePremiumStore());
  const { logged } = storeToRefs(useSessionAuthStore());

  async function fetchCapabilities(): Promise<void> {
    try {
      const result = await api.getPremiumCapabilities();
      set(capabilities, result);
    }
    catch (error: unknown) {
      logger.error('Failed to fetch premium capabilities:', error);
    }
  }

  watch(logged, (isLogged) => {
    if (!isLogged) {
      set(capabilities, undefined);
    }
  });

  return { fetchCapabilities };
}
