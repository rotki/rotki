import { nextTick } from 'vue';
import { createI18n } from 'vue-i18n';
import en from './locales/en.json';

const loadedLocales = new Set<string>(['en']);

export const i18n = createI18n({
  fallbackLocale: (import.meta.env.VITE_I18N_FALLBACK_LOCALE as string | undefined) || 'en',
  locale: (import.meta.env.VITE_I18N_LOCALE as string | undefined) || 'en',
  messages: { en },
  modifiers: {
    quote: (val, type) => type === 'text' && typeof val === 'string'
      ? `"${val}"`
      : type === 'vnode' && typeof val === 'object' && '__v_isVNode' in val
        ? `"${(val as any).children}"`
        : `"${val.toString()}"`,
  },
  silentTranslationWarn: import.meta.env.VITE_SILENT_TRANSLATION_WARN === 'true',
});

export async function loadLocaleMessages(locale: string): Promise<void> {
  if (loadedLocales.has(locale))
    return;

  const messages = await import(`./locales/${locale}.json`);
  i18n.global.setLocaleMessage(locale, messages.default);
  loadedLocales.add(locale);
  return nextTick();
}
