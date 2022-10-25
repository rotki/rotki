import { SupportedLanguage } from '@/types/frontend-settings';

const useLastLanguageShared = createSharedComposable(useLocalStorage);
const useForceUpdateMachineLanguageShared =
  createSharedComposable(useLocalStorage);
const lastLanguage = useLastLanguageShared(
  'rotki.last_language',
  SupportedLanguage.EN
);

const forceUpdateMachineLanguage = useForceUpdateMachineLanguageShared(
  'rotki.force_update_machine_language',
  'true'
);

export const useLastLanguage = () => {
  return {
    lastLanguage,
    forceUpdateMachineLanguage
  };
};
