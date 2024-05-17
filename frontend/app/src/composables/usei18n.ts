import Vue from 'vue';
import type { I18n, VueI18n } from 'vue-i18n-bridge';

declare module 'vue/types/vue' {
  export interface Vue {
    _i18nBridgeRoot: I18n & { locale: string; global: VueI18n };
  }
}

type NamedValues = Record<string, unknown>;

interface MigrationTranslator {
  <Key extends string>(key: Key): string;
  <Key extends string>(key: Key, plural: number): string;
  <Key extends string>(key: Key, values: NamedValues): string;
  <Key extends string>(key: Key, values: NamedValues, plural: number): string;
}

interface ModifiedI18n extends Omit<VueI18n, 't'> {
  t: MigrationTranslator;
}

export function useI18n(): ModifiedI18n {
  const instance = getCurrentInstance();
  const vm = instance?.proxy || new Vue();

  return vm._i18nBridgeRoot.global;
}

export function useI18nLocale() {
  const instance = getCurrentInstance();
  const vm = instance?.proxy || new Vue();

  const i18nBridgeRoot = vm._i18nBridgeRoot;

  const locale = computed({
    get() {
      return get(i18nBridgeRoot.global.locale);
    },
    set(locale: string) {
      set(i18nBridgeRoot.global.locale, locale);
      i18nBridgeRoot.locale = locale;
    },
  });

  return { locale };
}
