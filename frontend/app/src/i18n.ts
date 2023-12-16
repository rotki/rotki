import { createI18n } from 'vue-i18n';
import messages from '@intlify/unplugin-vue-i18n/messages';

export const i18n = createI18n({
  legacy: false,
  locale: (import.meta.env.VITE_I18N_LOCALE as string | undefined) || 'en',
  fallbackLocale: (import.meta.env.VITE_I18N_FALLBACK_LOCALE as string | undefined) || 'en',
  messages,
  silentTranslationWarn: import.meta.env.VITE_SILENT_TRANSLATION_WARN === 'true',
  modifiers: {
    quote: str => `"${str.toString()}"`,
  },
});
