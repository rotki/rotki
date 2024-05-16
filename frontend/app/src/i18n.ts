import VueI18n, { type LocaleMessages } from 'vue-i18n';
import { castToVueI18n, createI18n } from 'vue-i18n-bridge';
import Vue from 'vue';

Vue.use(VueI18n, { bridge: true });

function loadLocaleMessages(): LocaleMessages {
  const messages: LocaleMessages = {};
  try {
    const locales = import.meta.globEager('./locales/*.json') as any;

    for (const key in locales) {
      const matched = key.match(/([\w-]+)\./i);
      if (matched && matched.length > 1) {
        const locale = matched[1];
        messages[locale] = locales[key].default;
      }
    }
  }
  catch {}
  return messages;
}

export const i18n = castToVueI18n(
  createI18n(
    {
      legacy: false,
      locale: (import.meta.env.VITE_I18N_LOCALE as string | undefined) || 'en',
      fallbackLocale:
        (import.meta.env.VITE_I18N_FALLBACK_LOCALE as string | undefined)
        || 'en',
      messages: loadLocaleMessages(),
      silentTranslationWarn:
        import.meta.env.VITE_SILENT_TRANSLATION_WARN === 'true',
      modifiers: {
        quote: str => `"${str.toString()}"`,
      },
    },
    VueI18n,
  ),
);
