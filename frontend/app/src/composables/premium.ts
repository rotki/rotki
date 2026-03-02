import type { Ref } from 'vue';
import { useInterop } from '@/composables/electron-interop';
import { usePremiumStore } from '@/store/session/premium';

export function usePremium(): Ref<boolean> {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
}

interface UsePremiumHelperReturn {
  currentTier: Readonly<Ref<string>>;
  premium: Readonly<Ref<boolean>>;
  showGetPremiumButton: () => void;
}

export function usePremiumHelper(): UsePremiumHelperReturn {
  const { capabilities, premium } = storeToRefs(usePremiumStore());

  const { premiumUserLoggedIn } = useInterop();

  const showGetPremiumButton = (): void => {
    premiumUserLoggedIn(get(premium));
  };

  const currentTier = computed<string>(() => get(capabilities)?.currentTier ?? '');

  return {
    currentTier: readonly(currentTier),
    premium: readonly(premium),
    showGetPremiumButton,
  };
}
