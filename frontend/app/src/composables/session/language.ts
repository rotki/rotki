import { SupportedLanguage } from '@/types/settings/frontend-settings';
import type { MaybeRef } from '@vueuse/core';

const useLastLanguageShared = createSharedComposable(useLocalStorage);
const useForceUpdateMachineLanguageShared = createSharedComposable(useLocalStorage);
const lastLanguage = useLastLanguageShared('rotki.last_language', SupportedLanguage.EN);

const forceUpdateMachineLanguage = useForceUpdateMachineLanguageShared('rotki.force_update_machine_language', 'true');

export const useLastLanguage = createSharedComposable(() => {
  const checkMachineLanguage = (language: MaybeRef<SupportedLanguage>): void => {
    if (get(forceUpdateMachineLanguage) === 'true')
      set(lastLanguage, get(language));
    else
      set(lastLanguage, SupportedLanguage.EN);
  };

  return {
    checkMachineLanguage,
    forceUpdateMachineLanguage,
    lastLanguage,
  };
});
