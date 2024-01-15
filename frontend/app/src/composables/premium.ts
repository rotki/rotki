export function usePremium() {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
}

export function usePremiumReminder() {
  const premium: Ref<boolean> = usePremium();

  const { premiumUserLoggedIn } = useInterop();

  const showGetPremiumButton = () => {
    premiumUserLoggedIn(get(premium));
  };

  return {
    showGetPremiumButton,
  };
}
