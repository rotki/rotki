import { createI18n } from 'vue-i18n';

function loadLocaleMessages() {
  const messages: Record<string, any> = {};
  try {
    const locales = import.meta.glob('./locales/*.json', { eager: true }) as any;

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

export default createI18n({
  legacy: false,
  locale: (import.meta.env.VITE_I18N_LOCALE as string | undefined) || 'en',
  fallbackLocale: (import.meta.env.VITE_I18N_FALLBACK_LOCALE as string | undefined) || 'en',
  messages: loadLocaleMessages(),
  silentTranslationWarn: import.meta.env.VITE_SILENT_TRANSLATION_WARN === 'true',
});
