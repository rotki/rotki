import messages from '@intlify/unplugin-vue-i18n/messages';
import { createI18n } from 'vue-i18n';

export const i18n = createI18n({
  fallbackLocale: (import.meta.env.VITE_I18N_FALLBACK_LOCALE as string | undefined) || 'en',
  legacy: false,
  locale: (import.meta.env.VITE_I18N_LOCALE as string | undefined) || 'en',
  messages,
  modifiers: {
    quote: (val, type) => type === 'text' && typeof val === 'string'
      ? `"${val}"`
      : type === 'vnode' && typeof val === 'object' && '__v_isVNode' in val
        ? `"${(val as any).children}"`
        : `"${val.toString()}"`,
  },
  silentTranslationWarn: import.meta.env.VITE_SILENT_TRANSLATION_WARN === 'true',
});
