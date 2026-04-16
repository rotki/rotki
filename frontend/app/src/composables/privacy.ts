import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef } from 'vue';
import type { PrivacyMode } from '@/modules/session/types';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface UsePrivacyModeReturn {
  privacyMode: ComputedRef<PrivacyMode>;
  privacyModeIcon: ComputedRef<string>;
  togglePrivacyMode: () => Promise<void>;
  changePrivacyMode: (mode: PrivacyMode) => Promise<void>;
}

export function usePrivacyMode(): UsePrivacyModeReturn {
  const store = useFrontendSettingsStore();
  const { privacyMode } = storeToRefs(store);
  const { updateFrontendSetting } = useSettingsOperations();

  const privacyModeIcon = computed<RuiIcons>(() => {
    const icons = ['lu-eye', 'lu-eye-off', 'lu-eye-closed'] as const;
    return icons[get(privacyMode)];
  });

  const changePrivacyMode = async (mode: PrivacyMode): Promise<void> => {
    await updateFrontendSetting({ privacyMode: mode });
  };

  const togglePrivacyMode = async (): Promise<void> => {
    const newPrivacyMode = (get(privacyMode) + 1) % 3;
    await updateFrontendSetting({ privacyMode: newPrivacyMode });
  };

  return {
    changePrivacyMode,
    privacyMode,
    privacyModeIcon,
    togglePrivacyMode,
  };
}
