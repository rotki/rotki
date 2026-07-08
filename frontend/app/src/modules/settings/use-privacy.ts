import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { PrivacyMode } from '@/modules/session/types';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

interface UsePrivacyModeReturn {
  privacyMode: Readonly<Ref<PrivacyMode>>;
  privacyModeIcon: ComputedRef<string>;
  togglePrivacyMode: () => Promise<void>;
  changePrivacyMode: (mode: PrivacyMode) => Promise<void>;
}

export function usePrivacyMode(): UsePrivacyModeReturn {
  const privacyMode = useSetting('privacyMode');
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
