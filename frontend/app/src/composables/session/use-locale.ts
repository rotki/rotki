import type { MaybeRef } from 'vue';
import { loadLocaleMessages } from '@/i18n';
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

  async function setLanguage(language: string): Promise<void> {
    if (language !== get(locale)) {
      await loadLocaleMessages(language);
      set(locale, language);
      document.querySelector('html')?.setAttribute('lang', language);
    }
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
