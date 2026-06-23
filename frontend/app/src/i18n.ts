import { nextTick } from 'vue';
import { createI18n } from 'vue-i18n';
import en from './locales/en.json';

const loadedLocales = new Set<string>(['en']);

export const i18n = createI18n({
  fallbackLocale: import.meta.env.VITE_I18N_FALLBACK_LOCALE || 'en',
  locale: import.meta.env.VITE_I18N_LOCALE || 'en',
  messages: { en },
  modifiers: {
    quote(val, type) {
      if (type === 'text' && typeof val === 'string')
        return `"${val}"`;
      if (type === 'vnode' && typeof val === 'object' && '__v_isVNode' in val)
        return `"${(val as any).children}"`;
      return `"${val.toString()}"`;
    },
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

// Hot-reload the base (en) locale: the JSON is registered once at startup, so
// without this an edit to en.json only takes effect after a full dev restart.
if (import.meta.hot) {
  import.meta.hot.accept('./locales/en.json', (updated) => {
    if (updated?.default)
      i18n.global.setLocaleMessage('en', updated.default);
  });
}
