import { isVNode, nextTick } from 'vue';
import { createI18n } from 'vue-i18n';
import en from './locales/en.json';

const loadedLocales = new Set<string>(['en']);

export const i18n = createI18n({
  fallbackLocale: import.meta.env.VITE_I18N_FALLBACK_LOCALE ?? 'en',
  locale: import.meta.env.VITE_I18N_LOCALE ?? 'en',
  messages: { en },
  modifiers: {
    quote(val, type) {
      if (type === 'text' && typeof val === 'string')
        return `"${val}"`;
      if (type === 'vnode' && isVNode(val))
        return `"${String(val.children)}"`;
      return `"${val.toString()}"`;
    },
  },
  silentTranslationWarn: import.meta.env.VITE_SILENT_TRANSLATION_WARN === 'true',
});

/**
 * `@intlify/unplugin-vue-i18n` precompiles the locale JSON into a module whose default
 * export is an object of compiled message functions, but it neither self-accepts nor
 * handles hot updates for directly imported resources. Without an accept handler the
 * update propagates up to the root and Vite falls back to a full page reload, which
 * throws away the app state. Accepting here swaps the messages in place instead.
 */
if (import.meta.hot) {
  import.meta.hot.accept('./locales/en.json', (mod) => {
    if (mod)
      i18n.global.setLocaleMessage('en', mod.default);
  });
}

export async function loadLocaleMessages(locale: string): Promise<void> {
  if (loadedLocales.has(locale))
    return;

  const messages = await import(`./locales/${locale}.json`);
  i18n.global.setLocaleMessage(locale, messages.default);
  loadedLocales.add(locale);
  return nextTick();
}
