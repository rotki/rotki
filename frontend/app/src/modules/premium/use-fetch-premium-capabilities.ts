import { logger } from '@/modules/core/common/logging/logging';
import { usePremiumCredentialsApi } from '@/modules/premium/use-premium-credentials-api';
import { usePremiumStore } from '@/modules/premium/use-premium-store';

interface UseFetchPremiumCapabilitiesReturn {
  fetchCapabilities: () => Promise<void>;
}

export function useFetchPremiumCapabilities(): UseFetchPremiumCapabilitiesReturn {
  const api = usePremiumCredentialsApi();
  const { capabilities } = storeToRefs(usePremiumStore());

  async function fetchCapabilities(): Promise<void> {
    try {
      const result = await api.getPremiumCapabilities();
      set(capabilities, result);
    }
    catch (error: unknown) {
      logger.error('Failed to fetch premium capabilities:', error);
    }
  }

  return { fetchCapabilities };
}
