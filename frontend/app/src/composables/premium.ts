export function usePremium(): Ref<boolean> {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
}

interface UsePremiumReminderReturn { showGetPremiumButton: () => void }

export function usePremiumReminder(): UsePremiumReminderReturn {
  const premium: Ref<boolean> = usePremium();

  const { premiumUserLoggedIn } = useInterop();

  const showGetPremiumButton = (): void => {
    premiumUserLoggedIn(get(premium));
  };

  return {
    showGetPremiumButton,
  };
}
