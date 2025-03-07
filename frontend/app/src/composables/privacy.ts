import type { PrivacyMode } from '@/types/session';
import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef } from 'vue';
import { useSessionSettingsStore } from '@/store/settings/session';

interface UsePrivacyModeReturn {
  privacyMode: ComputedRef<PrivacyMode>;
  privacyModeIcon: ComputedRef<string>;
  togglePrivacyMode: () => void;
  changePrivacyMode: (mode: PrivacyMode) => void;
}

export function usePrivacyMode(): UsePrivacyModeReturn {
  const store = useSessionSettingsStore();
  const { privacyMode } = storeToRefs(store);

  const privacyModeIcon = computed<RuiIcons>(() => {
    const icons = ['lu-eye', 'lu-eye-off', 'lu-eye-closed'] as const;
    return icons[get(privacyMode)];
  });

  const changePrivacyMode = (mode: PrivacyMode): void => {
    store.update({ privacyMode: mode });
  };

  const togglePrivacyMode = (): void => {
    const newPrivacyMode = (get(privacyMode) + 1) % 3;
    store.update({ privacyMode: newPrivacyMode });
  };

  return {
    changePrivacyMode,
    privacyMode,
    privacyModeIcon,
    togglePrivacyMode,
  };
}
