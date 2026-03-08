import { usePremiumCredentialsApi } from '@/composables/api/session/premium-credentials';
import { useSessionAuthStore } from '@/store/session/auth';
import { usePremiumStore } from '@/store/session/premium';
import { logger } from '@/utils/logging';

export function usePremiumWatchers(): void {
  const api = usePremiumCredentialsApi();
  const { capabilities, premium } = storeToRefs(usePremiumStore());
  const { logged } = storeToRefs(useSessionAuthStore());

  watchImmediate([premium, logged], async ([, isLogged]) => {
    if (!isLogged) {
      set(capabilities, undefined);
      return;
    }

    try {
      const result = await api.getPremiumCapabilities();
      set(capabilities, result);
    }
    catch (error: unknown) {
      logger.error('Failed to fetch premium capabilities:', error);
    }
  });
}
