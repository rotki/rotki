import Vue from 'vue';
import VueI18n, { LocaleMessages } from 'vue-i18n';

Vue.use(VueI18n);

function loadLocaleMessages(): LocaleMessages {
  const messages: LocaleMessages = {};
  try {
    const locales = require.context(
      './locales',
      true,
      /[A-Za-z0-9-_,\s]+\.json$/i
    );

    locales.keys().forEach(key => {
      const matched = key.match(/([A-Za-z0-9-_]+)\./i);
      if (matched && matched.length > 1) {
        const locale = matched[1];
        messages[locale] = locales(key);
      }
    });
    // eslint-disable-next-line no-empty
  } catch (e) {}
  return messages;
}

export default new VueI18n({
  locale: process.env.VUE_APP_I18N_LOCALE || 'en',
  fallbackLocale: process.env.VUE_APP_I18N_FALLBACK_LOCALE || 'en',
  messages: loadLocaleMessages(),
  silentTranslationWarn: process.env.ROTKEHLCHEN_ENVIRONMENT === 'test'
});
