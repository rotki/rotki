import { computed } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { setupSession } from '@/composables/session';

export const usePrivacyMode = () => {
  const { privacyMode, changePrivacyMode } = setupSession();

  const privacyModeIcon = computed<string>(() => {
    return ['mdi-eye', 'mdi-eye-minus', 'mdi-eye-off'][get(privacyMode)];
  });

  const togglePrivacyMode = () => {
    const newPrivacyMode = (get(privacyMode) + 1) % 3;
    changePrivacyMode(newPrivacyMode);
  };

  return {
    privacyMode,
    privacyModeIcon,
    togglePrivacyMode,
    changePrivacyMode
  };
};
