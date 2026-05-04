import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useFetchPremiumCapabilities } from '@/modules/premium/use-fetch-premium-capabilities';
import { usePremiumStore } from '@/modules/premium/use-premium-store';

interface UsePremiumWatchersReturn {
  fetchCapabilities: () => Promise<void>;
}

export function usePremiumWatchers(): UsePremiumWatchersReturn {
  const { capabilities } = storeToRefs(usePremiumStore());
  const { logged } = storeToRefs(useSessionAuthStore());
  const { fetchCapabilities } = useFetchPremiumCapabilities();

  watch(logged, (isLogged) => {
    if (!isLogged) {
      set(capabilities, undefined);
    }
  });

  return { fetchCapabilities };
}
