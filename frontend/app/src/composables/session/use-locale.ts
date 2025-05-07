import type { MaybeRef } from '@vueuse/core';
import { useSessionAuthStore } from '@/store/session/auth';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { SupportedLanguage } from '@/types/settings/frontend-settings';

export const useLocale = createSharedComposable(() => {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { language } = storeToRefs(useFrontendSettingsStore());

  const lastLanguage = useLocalStorage('rotki.last_language', SupportedLanguage.EN);
  const forceUpdateMachineLanguage = useLocalStorage('rotki.force_update_machine_language', 'true');

  const { locale } = useI18n({ useScope: 'global' });

  const adaptiveLanguage = computed<SupportedLanguage>(() => {
    const selectedLanguageVal = get(lastLanguage);
    return !get(logged) && selectedLanguageVal !== 'undefined'
      ? (selectedLanguageVal as SupportedLanguage)
      : get(language);
  });

  const checkMachineLanguage = (language: MaybeRef<SupportedLanguage>): void => {
    if (get(forceUpdateMachineLanguage) === 'true')
      set(lastLanguage, get(language));
    else
      set(lastLanguage, SupportedLanguage.EN);
  };

  function setLanguage(language: string): void {
    if (language !== get(locale))
      set(locale, language);
  }

  watch([language, forceUpdateMachineLanguage], () => {
    checkMachineLanguage(get(language));
  });

  return {
    adaptiveLanguage,
    checkMachineLanguage,
    forceUpdateMachineLanguage,
    lastLanguage,
    setLanguage,
  };
});
