import type { Ref } from 'vue';
import { useInterop } from '@/composables/electron-interop';
import { usePremiumStore } from '@/store/session/premium';

export function usePremium(): Ref<boolean> {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
}

interface UsePremiumHelperReturn {
  showGetPremiumButton: () => void;
}

export function usePremiumHelper(): UsePremiumHelperReturn {
  const premium: Ref<boolean> = usePremium();

  const { premiumUserLoggedIn } = useInterop();

  const showGetPremiumButton = (): void => {
    premiumUserLoggedIn(get(premium));
  };

  return {
    showGetPremiumButton,
  };
}
