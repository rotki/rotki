import { type PrivacyMode } from '@/types/session';

export const usePrivacyMode = () => {
  const store = useSessionSettingsStore();
  const { privacyMode } = storeToRefs(store);

  const privacyModeIcon = computed<string>(
    () => ['eye-line', 'eye-2-line', 'eye-off-line'][get(privacyMode)]
  );

  const changePrivacyMode = (mode: PrivacyMode) => {
    store.update({ privacyMode: mode });
  };

  const togglePrivacyMode = () => {
    const newPrivacyMode = (get(privacyMode) + 1) % 3;
    store.update({ privacyMode: newPrivacyMode });
  };

  return {
    privacyMode,
    privacyModeIcon,
    togglePrivacyMode,
    changePrivacyMode
  };
};
