import { useMessageStore } from '@/store/message';
import { useSessionAuthStore } from '@/store/session/auth';
import { usePremiumStore } from '@/store/session/premium';

export const usePremium = () => {
  const { premium } = storeToRefs(usePremiumStore());
  return premium;
};

export const usePremiumReminder = () => {
  const premium = usePremium();
  const { navigateToDashboard } = useAppNavigation();

  const { premiumUserLoggedIn } = useInterop();
  const { premiumPrompt } = storeToRefs(useSessionAuthStore());
  const { message } = storeToRefs(useMessageStore());

  const isPremiumDialogVisible = computed(
    () => !get(premium) && !get(message).title && get(premiumPrompt)
  );

  const showPremiumDialog = async () => {
    if (get(premium)) {
      set(premiumPrompt, false);
      await navigateToDashboard();
      return;
    }
    set(premiumPrompt, true);
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
