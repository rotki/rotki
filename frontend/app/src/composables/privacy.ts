import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef } from 'vue';
import type { PrivacyMode } from '@/types/session';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

interface UsePrivacyModeReturn {
  privacyMode: ComputedRef<PrivacyMode>;
  privacyModeIcon: ComputedRef<string>;
  togglePrivacyMode: () => Promise<void>;
  changePrivacyMode: (mode: PrivacyMode) => Promise<void>;
}

export function usePrivacyMode(): UsePrivacyModeReturn {
  const store = useFrontendSettingsStore();
  const { privacyMode } = storeToRefs(store);

  const privacyModeIcon = computed<RuiIcons>(() => {
    const icons = ['lu-eye', 'lu-eye-off', 'lu-eye-closed'] as const;
    return icons[get(privacyMode)];
  });

  const changePrivacyMode = async (mode: PrivacyMode): Promise<void> => {
    await store.updateSetting({ privacyMode: mode });
  };

  const togglePrivacyMode = async (): Promise<void> => {
    const newPrivacyMode = (get(privacyMode) + 1) % 3;
    await store.updateSetting({ privacyMode: newPrivacyMode });
  };

  return {
    changePrivacyMode,
    privacyMode,
    privacyModeIcon,
    togglePrivacyMode,
  };
}
