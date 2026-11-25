import { createSharedComposable, useLocalStorage } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type MaybeRef, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { loadLocaleMessages } from '@/i18n';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { isOfEnum } from '@/modules/core/common/helpers/is-of-enum';
import { hasLiveSession } from '@/modules/core/session/session-lifecycle';
import { SupportedLanguage } from '@/modules/settings/types/frontend-settings';
import { useSetting } from '@/modules/settings/use-setting';

const isSupportedLanguage = isOfEnum(SupportedLanguage);

export const useLocale = createSharedComposable(() => {
  const { logged } = storeToRefs(useSessionAuthStore());
  const language = useSetting('language');

  const lastLanguage = useLocalStorage('rotki.last_language', SupportedLanguage.EN);
  const forceUpdateMachineLanguage = useLocalStorage('rotki.force_update_machine_language', 'true');

  const { locale } = useI18n({ useScope: 'global' });

  const adaptiveLanguage = computed<SupportedLanguage>(() => {
    const selectedLanguageVal = get(lastLanguage);
    return !get(logged) && isSupportedLanguage(selectedLanguageVal)
      ? selectedLanguageVal
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

  /**
   * Remembers the user's language for the login screen when they change it.
   *
   * @remarks
   * Only while a session is live: the store reset at logout puts `language` back to its default,
   * and remembering that would switch the login screen to English after every logout.
   */
  function rememberSessionLanguage(): void {
    if (hasLiveSession())
      checkMachineLanguage(get(language));
  }

  watch(language, rememberSessionLanguage);

  watch(forceUpdateMachineLanguage, () => {
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
