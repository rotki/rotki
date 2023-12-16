import type { RuiIcons } from '@rotki/ui-library';
import type { PrivacyMode } from '@/types/session';

export function usePrivacyMode() {
  const store = useSessionSettingsStore();
  const { privacyMode } = storeToRefs(store);

  const privacyModeIcon = computed<RuiIcons>(() => {
    const icons = ['eye-line', 'eye-2-line', 'eye-off-line'] as const;
    return icons[get(privacyMode)];
  });

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
    changePrivacyMode,
  };
}
