import { type ComputedRef, type Ref } from 'vue';

export const usePremium = () => {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
};

export const usePremiumReminder = () => {
  const premium: Ref<boolean> = usePremium();

  const { premiumUserLoggedIn } = useInterop();
  const { premiumPrompt } = storeToRefs(useSessionAuthStore());
  const { message } = storeToRefs(useMessageStore());

  const isPremiumDialogVisible: ComputedRef<boolean> = computed(
    () => !get(premium) && !get(message).title && get(premiumPrompt)
  );

  const showPremiumDialog = async (): Promise<boolean> => {
    if (get(premium)) {
      set(premiumPrompt, false);
      return true;
    }
    set(premiumPrompt, true);
    return false;
  };

  const showGetPremiumButton = () => {
    premiumUserLoggedIn(get(premium));
  };

  return {
    isPremiumDialogVisible,
    showGetPremiumButton,
    showPremiumDialog
  };
};
