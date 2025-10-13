import type { ComputedRef, Ref } from 'vue';
import type { PremiumFeature } from '@/types/session';
import { useInterop } from '@/composables/electron-interop';
import { usePremiumStore } from '@/store/session/premium';

export function usePremium(): Ref<boolean> {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
}

interface UsePremiumHelperReturn {
  showGetPremiumButton: () => void;
  isFeatureAllowed: (feature: PremiumFeature) => ComputedRef<boolean>;
}

export function usePremiumHelper(): UsePremiumHelperReturn {
  const premium: Ref<boolean> = usePremium();
  const { capabilities } = storeToRefs(usePremiumStore());

  const { premiumUserLoggedIn } = useInterop();

  const showGetPremiumButton = (): void => {
    premiumUserLoggedIn(get(premium));
  };

  const isFeatureAllowed = (feature: PremiumFeature): ComputedRef<boolean> => computed<boolean>(() => {
    if (!get(premium))
      return false;

    const caps = get(capabilities);
    return caps?.[feature] ?? false;
  });

  return {
    isFeatureAllowed,
    showGetPremiumButton,
  };
}
