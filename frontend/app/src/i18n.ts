import Vue from 'vue';
import VueI18n, { LocaleMessages } from 'vue-i18n';

Vue.use(VueI18n);

function loadLocaleMessages(): LocaleMessages {
  const messages: LocaleMessages = {};
  try {
    const locales = import.meta.globEager('./locales/*.json');

    for (const key in locales) {
      const matched = key.match(/([A-Za-z0-9-_]+)\./i);
      if (matched && matched.length > 1) {
        const locale = matched[1];
        messages[locale] = locales[key].default;
      }
    }
    // eslint-disable-next-line no-empty
  } catch (e) {}
  return messages;
}

export default new VueI18n({
  locale: (import.meta.env.VITE_I18N_LOCALE as string | undefined) || 'en',
  fallbackLocale:
    (import.meta.env.VITE_I18N_FALLBACK_LOCALE as string | undefined) || 'en',
  messages: loadLocaleMessages(),
  silentTranslationWarn: process.env.ROTKEHLCHEN_ENVIRONMENT === 'test'
});
