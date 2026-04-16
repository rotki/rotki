import type { Ref } from 'vue';
import { useInterop } from '@/composables/electron-interop';
import { usePremiumStore } from '@/modules/premium/use-premium-store';

export function usePremium(): Ref<boolean> {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
}

interface UsePremiumHelperReturn {
  currentTier: Readonly<Ref<string>>;
  ethStakedLimit: Readonly<Ref<number>>;
  premium: Readonly<Ref<boolean>>;
  showGetPremiumButton: () => void;
}

export function usePremiumHelper(): UsePremiumHelperReturn {
  const { capabilities, premium } = storeToRefs(usePremiumStore());

  const { premiumUserLoggedIn } = useInterop();

  const showGetPremiumButton = (): void => {
    premiumUserLoggedIn(get(premium));
  };

  const currentTier = computed<string>(() => get(capabilities)?.currentTier ?? 'Free');
  const ethStakedLimit = computed<number>(() => get(capabilities)?.ethStakedLimit ?? 0);

  return {
    currentTier: readonly(currentTier),
    ethStakedLimit: readonly(ethStakedLimit),
    premium: readonly(premium),
    showGetPremiumButton,
  };
}
