import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed } from 'vue';
import { PrivacyMode } from '@/store/session/types';
import { useSessionSettingsStore } from '@/store/settings/session';

export const usePrivacyMode = () => {
  const { privacyMode } = storeToRefs(useSessionSettingsStore());

  const privacyModeIcon = computed<string>(() => {
    return ['mdi-eye', 'mdi-eye-minus', 'mdi-eye-off'][get(privacyMode)];
  });

  const changePrivacyMode = (mode: PrivacyMode) => {
    set(privacyMode, mode);
  };

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
