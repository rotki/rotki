import { usePremiumCredentialsApi } from '@/composables/api/session/premium-credentials';
import { logger } from '@/modules/common/logging/logging';
import { useSessionAuthStore } from '@/store/session/auth';
import { usePremiumStore } from '@/store/session/premium';

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
